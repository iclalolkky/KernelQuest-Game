"""Game engine: pygame init, main loop, top-level state machine."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from kernelquest.core import settings as settings_module
from kernelquest.core.config import (
    BAD_SECTOR_DAMAGE,
    DATABASE_FILENAME,
    FPS,
    PLAYER_BASE_DAMAGE,
    PLAYER_CACHE_CAPACITY,
    PLAYER_NAME_MAX_LENGTH,
    PLAYER_START_CPU_CYCLES,
    PLAYER_START_RAM,
    SCORE_PER_DESCENT,
    SCORE_PER_MOVE,
    SCREEN_SHAKE_DAMAGE_INTENSITY,
    SCREEN_SHAKE_KILL_INTENSITY,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from kernelquest.core.settings import Settings
from kernelquest.core.state import GameState
from kernelquest.data.database import Database
from kernelquest.data.repositories import (
    DaemonRepository,
    DailyRunRepository,
    MetaRepository,
    RunRepository,
    ScoreRepository,
    UpgradeRepository,
)
from kernelquest.data.upgrades_catalog import CATALOG, PlayerBonus
from kernelquest.entities.daemon import (
    CATALOG as DAEMON_CATALOG,
)
from kernelquest.entities.daemon import (
    Daemon,
    get_daemon,
    starter_daemon,
)
from kernelquest.entities.malware import Malware, SegFault, ZombieProcess
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.patch import Patch, PatchEffects, PatchState
from kernelquest.entities.player import Player
from kernelquest.entities.program import starter_loadout
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import player_attack
from kernelquest.systems.daemons import (
    damage_multiplier_on_attack,
)
from kernelquest.systems.daemons import (
    on_pickup as daemon_on_pickup,
)
from kernelquest.systems.daemons import (
    on_turn_end as daemon_on_turn_end,
)
from kernelquest.systems.inventory import pickup_item_at, use_cache_slot
from kernelquest.systems.programs import execute_program
from kernelquest.ui import theme
from kernelquest.ui import themes as themes_mod
from kernelquest.ui.console_log import ConsoleLog
from kernelquest.ui.fx import FloatingTextSystem, ParticleSystem, ScreenShake
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.sfx import SoundManager
from kernelquest.ui.viewport import Viewport
from kernelquest.world.daily import today_iso, today_seed
from kernelquest.world.generator import generate_world
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

log = logging.getLogger(__name__)

_KEY_BITS = "meta.bits"

_MENU_OPTIONS: tuple[str, ...] = (
    "New Run",
    "Daily Run",
    "Tutorial",
    "How to Play",
    "High Scores",
    "Daily Board",
    "Stats",
    "Shop",
    "Settings",
    "Quit",
)


@dataclass
class _RunMeta:
    """Per-run bookkeeping (seed, start time)."""

    seed: int
    is_daily: bool = False
    daily_date: str = ""
    started_at: float = field(default_factory=time.monotonic)

    def elapsed_ms(self) -> int:
        return max(0, int((time.monotonic() - self.started_at) * 1000))


class GameEngine:
    """Owns the pygame window and orchestrates state transitions."""

    def __init__(self, database_path: Path | None = None, seed: int | None = None) -> None:
        self._db_path = database_path or Path(DATABASE_FILENAME)
        self._database: Database | None = None
        self._scores: ScoreRepository | None = None
        self._runs: RunRepository | None = None
        self._meta: MetaRepository | None = None
        self._upgrades: UpgradeRepository | None = None
        self._daemons_repo: DaemonRepository | None = None
        self._daily_repo: DailyRunRepository | None = None

        self._state: GameState = GameState.MENU
        self._seed_override = seed
        self._rng: random.Random = random.Random(seed)
        self._world: World | None = None
        self._viewport: Viewport = Viewport.centered(WINDOW_WIDTH, WINDOW_HEIGHT, 20, 20)
        self._name_buffer: str = ""

        self._console = ConsoleLog()
        self._shake = ScreenShake()
        self._particles = ParticleSystem()
        self._floats = FloatingTextSystem()
        self._sfx: SoundManager | None = None
        self._screen: pygame.Surface | None = None
        self._ui: UIManager | None = None

        self._settings: Settings = Settings()
        self._menu_index: int = 0
        self._shop_index: int = 0
        self._settings_index: int = 0
        self._shop_message: str | None = None
        self._run_meta: _RunMeta | None = None
        self._patches: PatchState = PatchState()
        self._patch_choices: list[Patch] = []
        self._patch_pick_index: int = 0
        # Boss / accessibility / overlay state.
        self._boss_active: bool = False
        self._boss_banner_ttl: float = 0.0
        self._glitch_intensity: float = 0.0
        self._show_help_overlay: bool = False
        self._howtoplay_lines: list[str] = []
        self._howtoplay_scroll: int = 0
        self._tutorial_step: int = 0
        self._is_tutorial_run: bool = False

    # ----- public entry point -----

    def run(self) -> None:
        log.info("Booting GameEngine (db=%s)", self._db_path)
        self._database = Database.open(self._db_path)
        self._scores = ScoreRepository(self._database)
        self._runs = RunRepository(self._database)
        self._meta = MetaRepository(self._database)
        self._upgrades = UpgradeRepository(self._database)
        self._daemons_repo = DaemonRepository(self._database)
        self._daily_repo = DailyRunRepository(self._database)
        self._settings = settings_module.load(self._meta)
        # Grant the starter daemon on the very first launch.
        if not self._daemons_repo.owned():
            self._daemons_repo.grant(starter_daemon().key)
            self._daemons_repo.set_equipped([starter_daemon().key])

        pygame.init()
        try:
            themes_mod.apply_theme(self._settings.theme)
            if self._settings.large_text:
                # Bump font sizes by 25% before UIManager initialises its fonts.
                theme.FONT_SIZE_SMALL = int(theme.FONT_SIZE_SMALL * 1.25)
                theme.FONT_SIZE_BODY = int(theme.FONT_SIZE_BODY * 1.25)
                theme.FONT_SIZE_TITLE = int(theme.FONT_SIZE_TITLE * 1.25)
            flags = pygame.FULLSCREEN if self._settings.fullscreen else 0
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
            pygame.display.set_caption(WINDOW_TITLE)
            self._screen = screen
            ui = UIManager(screen)
            self._ui = ui
            self._sfx = SoundManager()
            self._sfx.set_volume(self._settings.volume)
            self._sfx.set_music_volume(self._settings.music_volume)
            self._sfx.set_sfx_volume(self._settings.sfx_volume)
            self._sfx.set_muted(self._settings.muted)
            self._sfx.start_music("main")
            clock = pygame.time.Clock()

            # First-launch onboarding nudge.
            if not settings_module.is_tutorial_done(self._meta):
                self._console.info("Hint: try the Tutorial from the main menu!")

            while self._state is not GameState.QUIT:
                dt = clock.tick(FPS) / 1000.0
                self._handle_events()
                self._step_fx(dt)
                self._render(ui)
        finally:
            if self._sfx is not None:
                self._sfx.stop_music()
            pygame.quit()
            if self._database is not None:
                self._database.close()
            log.info("GameEngine shutdown complete.")

    # ----- per-frame -----

    def _step_fx(self, dt: float = 0.0) -> None:
        if self._settings.reduce_motion:
            self._shake.intensity = 0.0
            self._particles.clear()
        self._shake.step()
        self._particles.step()
        self._floats.step()
        if self._boss_banner_ttl > 0.0:
            self._boss_banner_ttl = max(0.0, self._boss_banner_ttl - dt)
        if self._glitch_intensity > 0.0:
            self._glitch_intensity = max(0.0, self._glitch_intensity - dt * 0.4)

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._state = GameState.QUIT
                return
            if event.type != pygame.KEYDOWN:
                continue

            # Global hotkeys (work in every state).
            if event.key == pygame.K_F11:
                self._settings.toggle_fullscreen()
                self._apply_display_mode()
                continue
            if (
                event.key == pygame.K_m
                and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META) == 0
                and self._state is not GameState.GAME_OVER
            ):
                self._settings.toggle_mute()
                if self._sfx is not None:
                    self._sfx.set_muted(self._settings.muted)
                continue

            if self._state is GameState.MENU:
                self._handle_menu_key(event)
            elif self._state is GameState.PLAYING:
                self._handle_playing_key(event)
            elif self._state is GameState.TUTORIAL:
                self._handle_tutorial_key(event)
            elif self._state is GameState.HOWTOPLAY:
                self._handle_howtoplay_key(event)
            elif self._state is GameState.GAME_OVER:
                self._handle_game_over_key(event)
            elif self._state in (GameState.HIGH_SCORES, GameState.STATS, GameState.DAILY_BOARD):
                self._handle_back_key(event)
            elif self._state is GameState.SHOP:
                self._handle_shop_key(event)
            elif self._state is GameState.SETTINGS:
                self._handle_settings_key(event)
            elif self._state is GameState.PATCH_PICK:
                self._handle_patch_pick_key(event)

    def _apply_display_mode(self) -> None:
        flags = pygame.FULLSCREEN if self._settings.fullscreen else 0
        try:
            self._screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
            if self._ui is not None:
                self._ui.screen = self._screen
        except pygame.error as exc:  # pragma: no cover
            log.warning("Failed to toggle display mode: %s", exc)

    def _handle_menu_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._state = GameState.QUIT
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._menu_index = (self._menu_index - 1) % len(_MENU_OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._menu_index = (self._menu_index + 1) % len(_MENU_OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate_menu_option()

    def _activate_menu_option(self) -> None:
        choice = _MENU_OPTIONS[self._menu_index]
        if choice == "New Run":
            self._start_new_run(daily=False)
        elif choice == "Daily Run":
            self._start_new_run(daily=True)
        elif choice == "Tutorial":
            self._start_tutorial()
        elif choice == "How to Play":
            self._open_howtoplay()
        elif choice == "High Scores":
            self._state = GameState.HIGH_SCORES
        elif choice == "Daily Board":
            self._state = GameState.DAILY_BOARD
        elif choice == "Stats":
            self._state = GameState.STATS
        elif choice == "Shop":
            self._shop_index = 0
            self._shop_message = None
            self._state = GameState.SHOP
        elif choice == "Settings":
            self._settings_index = 0
            self._state = GameState.SETTINGS
        elif choice == "Quit":
            self._state = GameState.QUIT

    def _handle_back_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._state = GameState.MENU

    def _handle_shop_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._state = GameState.MENU
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._shop_index = (self._shop_index - 1) % len(CATALOG)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._shop_index = (self._shop_index + 1) % len(CATALOG)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._buy_selected_upgrade()

    def _handle_settings_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            assert self._meta is not None
            settings_module.save(self._meta, self._settings)
            self._state = GameState.MENU
            return
        rows = self._settings_rows()
        if event.key in (pygame.K_UP, pygame.K_w):
            self._settings_index = (self._settings_index - 1) % len(rows)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._settings_index = (self._settings_index + 1) % len(rows)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._adjust_setting(-1)
        elif event.key in (
            pygame.K_RIGHT,
            pygame.K_d,
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_SPACE,
        ):
            self._adjust_setting(+1)

    _SETTINGS_KEYS: tuple[str, ...] = (
        "music",
        "sfx",
        "mute",
        "difficulty",
        "theme",
        "fullscreen",
        "ui_scale",
        "reduce_motion",
        "crt",
        "large_text",
    )

    def _adjust_setting(self, direction: int) -> None:
        key = self._SETTINGS_KEYS[self._settings_index % len(self._SETTINGS_KEYS)]
        if key == "music":
            self._settings.adjust_music_volume(0.1 * direction)
            if self._sfx is not None:
                self._sfx.set_music_volume(self._settings.music_volume)
        elif key == "sfx":
            self._settings.adjust_sfx_volume(0.1 * direction)
            if self._sfx is not None:
                self._sfx.set_sfx_volume(self._settings.sfx_volume)
        elif key == "mute":
            self._settings.toggle_mute()
            if self._sfx is not None:
                self._sfx.set_muted(self._settings.muted)
        elif key == "difficulty":
            self._settings.cycle_difficulty()
        elif key == "theme":
            self._cycle_theme(direction)
        elif key == "fullscreen":
            self._settings.toggle_fullscreen()
            self._apply_display_mode()
        elif key == "ui_scale":
            self._settings.adjust_ui_scale(0.05 * direction)
        elif key == "reduce_motion":
            self._settings.toggle_reduce_motion()
        elif key == "crt":
            self._settings.toggle_crt()
        elif key == "large_text":
            self._settings.toggle_large_text()

    def _cycle_theme(self, direction: int) -> None:
        from kernelquest.ui import themes as themes_mod

        keys = [t.key for t in themes_mod.CATALOG]
        current = self._settings.theme
        idx = keys.index(current) if current in keys else 0
        idx = (idx + direction) % len(keys)
        self._settings.theme = keys[idx]
        themes_mod.apply_theme(self._settings.theme)

    def _handle_playing_key(self, event: pygame.event.Event) -> None:
        assert self._world is not None
        world = self._world
        player = world.player

        if event.key == pygame.K_ESCAPE:
            if player.crash_cause is None:
                player.crash_cause = "Manual shutdown"
            self._enter_game_over()
            return

        if event.key in (pygame.K_QUESTION, pygame.K_SLASH, pygame.K_F1):
            self._show_help_overlay = not self._show_help_overlay
            return

        if event.key == pygame.K_SPACE:
            self._end_player_turn()
            return

        program_slot = _key_to_program_slot(event.key)
        if program_slot is not None:
            result = execute_program(world, program_slot, self._rng)
            self._console.info(result.message)
            if result.success:
                if result.killed_enemy is not None:
                    self._on_enemy_killed(result.killed_enemy)
                world.recompute_fov()
                self._after_player_action()
            return

        slot_index = _key_to_slot(event.key)
        if slot_index is not None:
            message = use_cache_slot(world, slot_index)
            if message is not None:
                self._console.info(message)
                self._play_sfx("pickup")
                world.recompute_fov()
                self._after_player_action()
            return

        delta = _key_to_delta(event.key)
        if delta is None:
            return

        target = (player.position[0] + delta[0], player.position[1] + delta[1])
        enemy = world.enemy_at(target)
        if enemy is not None:
            self._player_attacks(enemy)
            return

        moved = player.try_move(*delta, world.grid)
        if moved:
            self._on_player_moved()

    def _handle_patch_pick_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._patch_pick_index = (self._patch_pick_index - 1) % len(self._patch_choices)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._patch_pick_index = (self._patch_pick_index + 1) % len(self._patch_choices)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            picked = self._patch_choices[self._patch_pick_index]
            self._patches.add(picked)
            # Apply one-shot effects on pickup.
            single = PatchEffects()
            picked.apply(single)
            if self._world is not None:
                player = self._world.player
                if single.starting_ram_bonus > 0:
                    player.max_ram += single.starting_ram_bonus
                    player.ram = min(player.max_ram, player.ram + single.starting_ram_bonus)
                if single.fov_radius_bonus > 0:
                    player.bonus_scan_radius += single.fov_radius_bonus
                    self._world.recompute_fov()
            self._console.info(f"Applied patch: {picked.label}")
            self._patch_choices = []
            self._state = GameState.PLAYING

    def _handle_game_over_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._save_run()
            self._reset_to_menu()
            return
        if event.key == pygame.K_BACKSPACE:
            self._name_buffer = self._name_buffer[:-1]
            return
        if event.key == pygame.K_ESCAPE:
            self._reset_to_menu()
            return
        char = event.unicode
        if char and char.isprintable() and len(self._name_buffer) < PLAYER_NAME_MAX_LENGTH:
            self._name_buffer += char

    def _render(self, ui: UIManager) -> None:
        if self._state is GameState.MENU:
            ui.render_menu(list(_MENU_OPTIONS), self._menu_index)
        elif self._state is GameState.PLAYING and self._world is not None:
            ui.clear()
            ui.render_world(
                self._world,
                self._viewport,
                shake=self._shake,
                particles=self._particles,
            )
            ui.render_floating_text(self._floats, self._viewport)
            ui.render_hud(
                self._world.player,
                sector=self._world.player.depth_reached,
                world=self._world,
                patches=[p.label for p in self._patches.selected],
            )
            if self._boss_active:
                boss = self._world.living_boss()
                if boss is not None:
                    ui.render_boss_hp_bar(boss)
                if self._boss_banner_ttl > 0.0:
                    ui.render_boss_banner(
                        boss.crash_label if boss is not None else "BOSS",
                        self._boss_banner_ttl / 2.5,
                    )
                ui.render_glitch_overlay(max(0.25, self._glitch_intensity))
            elif self._glitch_intensity > 0.0:
                ui.render_glitch_overlay(self._glitch_intensity)
            ui.render_console(self._console)
            if self._show_help_overlay:
                ui.render_help_overlay()
            if self._settings.crt_effect:
                ui.render_scanlines()
        elif self._state is GameState.TUTORIAL:
            ui.render_tutorial(
                self._TUTORIAL_STEPS[min(self._tutorial_step, len(self._TUTORIAL_STEPS) - 1)],
                self._tutorial_step + 1,
                len(self._TUTORIAL_STEPS),
            )
            if self._settings.crt_effect:
                ui.render_scanlines()
        elif self._state is GameState.HOWTOPLAY:
            ui.render_howtoplay(self._howtoplay_lines, self._howtoplay_scroll)
        elif self._state is GameState.GAME_OVER and self._world is not None:
            ui.render_game_over(self._world.player, self._name_buffer)
        elif self._state is GameState.HIGH_SCORES:
            ui.render_high_scores(self._fetch_high_scores())
        elif self._state is GameState.DAILY_BOARD:
            ui.render_daily_board(today_iso(), self._fetch_daily_board())
        elif self._state is GameState.STATS:
            avg, deaths, best, count = self._fetch_stats()
            ui.render_stats(avg, deaths, best, count)
        elif self._state is GameState.SHOP:
            ui.render_shop(
                self._fetch_bits(),
                self._shop_rows(),
                self._shop_index,
                self._shop_message,
            )
        elif self._state is GameState.SETTINGS:
            ui.render_settings(self._settings_rows(), self._settings_index)
        elif self._state is GameState.PATCH_PICK:
            ui.render_patch_pick(
                [(p.label, p.description) for p in self._patch_choices],
                self._patch_pick_index,
            )
        ui.present()

    # ----- transitions -----

    def _start_new_run(self, *, daily: bool = False) -> None:
        if daily:
            seed = today_seed()
        elif self._seed_override is not None:
            seed = self._seed_override
        else:
            seed = random.randrange(2**31)
        self._rng = random.Random(seed)
        self._run_meta = _RunMeta(
            seed=seed, is_daily=daily, daily_date=today_iso() if daily else ""
        )
        self._patches = PatchState()
        self._patch_choices = []
        self._patch_pick_index = 0
        self._is_tutorial_run = False
        self._boss_active = False
        self._boss_banner_ttl = 0.0
        self._glitch_intensity = 0.0
        self._floats.clear()

        bonus = self._compute_bonus()
        max_ram = PLAYER_START_RAM + bonus.bonus_ram
        max_cycles = PLAYER_START_CPU_CYCLES + bonus.bonus_cycles
        player = Player(
            max_ram=max_ram,
            ram=max_ram,
            max_cpu_cycles=max_cycles,
            cpu_cycles=max_cycles,
            cache_capacity=PLAYER_CACHE_CAPACITY + bonus.bonus_cache,
            base_damage=PLAYER_BASE_DAMAGE + bonus.bonus_damage,
            bonus_scan_radius=bonus.bonus_scan_radius,
        )
        # Phase 5 — equip programs and persisted daemons.
        player.programs = starter_loadout()
        player.daemons = self._equipped_daemons()

        self._world = generate_world(player=player, depth=1, rng=self._rng)
        self._world.recompute_fov()
        self._viewport = Viewport.centered(
            WINDOW_WIDTH, WINDOW_HEIGHT, self._world.grid.width, self._world.grid.height
        )
        self._name_buffer = ""
        self._console.clear()
        prefix = "DAILY " if daily else ""
        self._console.info(
            f"{prefix}Process spawned in sector 0x{player.depth_reached:02X} (seed={seed})"
        )
        self._particles.clear()
        if self._sfx is not None:
            self._sfx.start_music("main")
        self._refresh_boss_state()
        self._state = GameState.PLAYING

    def _equipped_daemons(self) -> list[Daemon]:
        if self._daemons_repo is None:
            return []
        out: list[Daemon] = []
        for key in self._daemons_repo.equipped():
            try:
                out.append(get_daemon(key))
            except KeyError:
                continue
        return out

    def _compute_bonus(self) -> PlayerBonus:
        bonus = PlayerBonus()
        if self._upgrades is None:
            return bonus
        levels = self._upgrades.all_levels()
        for upgrade in CATALOG:
            level = levels.get(upgrade.key, 0)
            if level > 0:
                upgrade.apply(level, bonus)
        return bonus

    def _player_attacks(self, enemy: Malware) -> None:
        assert self._world is not None
        player = self._world.player
        if not player.spend_cycle():
            return
        patch_effects = self._patches.effects()
        boss_mult = patch_effects.boss_damage_mult if getattr(enemy, "is_boss", False) else 1.0
        damage = max(
            1,
            int(
                round(
                    player.base_damage
                    * self._settings.player_damage_multiplier
                    * patch_effects.player_damage_mult
                    * boss_mult
                    * player.next_attack_multiplier
                    * damage_multiplier_on_attack(player)
                )
            ),
        )
        player.next_attack_multiplier = 1.0
        result = player_attack(self._world, enemy, self._rng, damage=damage)
        self._console.info(result.log_message)
        self._play_sfx("attack")
        ex, ey = enemy.position
        self._particles.burst(
            (ex + 0.5, ey + 0.5),
            theme.NEON_MAGENTA if result.killed else theme.NEON_AMBER,
            self._rng,
            count=14 if result.killed else 6,
        )
        if result.killed:
            self._on_enemy_killed(enemy)
        self._world.recompute_fov()
        self._after_player_action()

    def _on_enemy_killed(self, enemy: Malware) -> None:
        assert self._world is not None
        player = self._world.player
        self._shake.punch(SCREEN_SHAKE_KILL_INTENSITY)
        self._world.remove_dead_enemies()
        self._play_sfx("explode")
        # Score with combo + patch multipliers.
        patch_effects = self._patches.effects()
        base = enemy.score_value
        gained = int(round(base * player.combo_multiplier * patch_effects.score_mult))
        player.score = max(0, player.score - base + gained)  # base was already added by combat
        # Floating "+score" pop above the kill.
        if not self._settings.reduce_motion and gained > 0:
            ex, ey = enemy.position
            self._floats.spawn(f"+{gained}", (ex + 0.5, ey + 0.5), theme.NEON_AMBER)
        player.register_combo_event()
        # Bosses drop a guaranteed daemon (if not all already owned).
        if isinstance(enemy, ZombieProcess) and self._rng.random() < 0.25:
            self._maybe_award_daemon()
        if isinstance(enemy, SegFault):
            self._maybe_award_daemon(force=True)
        # Boss defeated — release lock and restore main music.
        if getattr(enemy, "is_boss", False) and not self._world.has_living_boss:
            self._boss_active = False
            self._glitch_intensity = 0.0
            self._console.info("BOSS terminated. Exit unlocked.")
            if self._sfx is not None:
                self._sfx.start_music("main")

    def _maybe_award_daemon(self, *, force: bool = False) -> None:
        if self._daemons_repo is None:
            return
        owned = self._daemons_repo.owned()
        unowned = [d for d in DAEMON_CATALOG if d.key not in owned]
        if not unowned:
            return
        if not force and self._rng.random() > 0.5:
            return
        new_daemon = self._rng.choice(unowned)
        self._daemons_repo.grant(new_daemon.key)
        self._console.info(f"Acquired daemon: {new_daemon.label}")

    def _on_player_moved(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.score += SCORE_PER_MOVE
        self._play_sfx("move")
        self._world.recompute_fov()

        message = pickup_item_at(self._world, player.position)
        if message is not None:
            patch_effects = self._patches.effects()
            self._console.info(message)
            self._play_sfx("pickup")
            bonus_score = daemon_on_pickup(self._world)
            if bonus_score > 0:
                player.score += bonus_score
                self._console.info(f"daemon bonus: +{bonus_score}")
            # Apply pickup_score_mult on top (rough heuristic: bonus delta scaled).
            if patch_effects.pickup_score_mult != 1.0 and bonus_score > 0:
                extra = int(round(bonus_score * (patch_effects.pickup_score_mult - 1.0)))
                if extra:
                    player.score = max(0, player.score + extra)
            # Cycle refund on pickup (Zero-Copy patch).
            refund = patch_effects.cycle_refund_on_pickup
            if refund > 0:
                player.cpu_cycles = min(player.max_cpu_cycles, player.cpu_cycles + refund)
            player.register_combo_event()
            self._particles.burst(
                (player.position[0] + 0.5, player.position[1] + 0.5),
                theme.NEON_GREEN,
                self._rng,
                count=8,
                speed=1.6,
            )

        tile = self._world.grid.get(*player.position)
        if tile is TileType.BAD_SECTOR:
            player.take_damage(BAD_SECTOR_DAMAGE, source="Bad Sector")
            self._console.warn(f"Bad Sector burned {BAD_SECTOR_DAMAGE} RAM")
            self._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
            if not self._settings.reduce_motion:
                px, py = player.position
                self._floats.spawn(
                    f"-{BAD_SECTOR_DAMAGE} RAM", (px + 0.5, py + 0.5), (255, 110, 110)
                )
        elif tile is TileType.EXIT:
            if self._world.has_living_boss:
                boss = self._world.living_boss()
                label = boss.crash_label if boss is not None else "BOSS"
                self._console.crit(f"EXIT LOCKED — terminate {label} first.")
                self._glitch_intensity = max(self._glitch_intensity, 0.6)
            else:
                self._descend()
                return

        if not player.is_alive:
            self._enter_game_over()
            return

        self._after_player_action()

    def _after_player_action(self) -> None:
        assert self._world is not None
        player = self._world.player
        if not player.is_alive:
            self._enter_game_over()
            return
        if player.cpu_cycles == 0:
            self._end_player_turn()

    def _end_player_turn(self) -> None:
        assert self._world is not None
        starting_ram = self._world.player.ram
        patch_effects = self._patches.effects()
        # Page-fault patch: ram_per_action drains RAM each turn.
        if patch_effects.ram_per_action > 0 and self._world.player.is_alive:
            self._world.player.take_damage(patch_effects.ram_per_action, source="page-fault")
            self._console.warn(f"page-fault: -{patch_effects.ram_per_action} RAM")
        enemy_mult = self._settings.enemy_damage_multiplier * patch_effects.enemy_damage_mult
        for message in run_enemy_turn(self._world, self._rng, damage_multiplier=enemy_mult):
            self._console.warn(message)

        # Patch: speed_demon → enemies move an extra time per turn.
        for _ in range(patch_effects.enemy_speed_bonus):
            for message in run_enemy_turn(self._world, self._rng, damage_multiplier=enemy_mult):
                self._console.warn(message)

        if self._world.player.ram < starting_ram:
            self._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
            self._play_sfx("attack")
        if not self._world.player.is_alive:
            self._enter_game_over()
            return
        self._world.player.tick_status_effects()
        self._world.player.tick_combo_idle()
        self._world.turn_counter += 1
        for msg in daemon_on_turn_end(self._world, self._world.turn_counter):
            self._console.info(msg)
        self._world.player.end_turn()
        self._world.recompute_fov()

    def _descend(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.depth_reached += 1
        player.score += SCORE_PER_DESCENT
        self._console.info(f"Descending to sector 0x{player.depth_reached:02X}")
        self._play_sfx("descend")
        patch_effects = self._patches.effects()
        self._world = generate_world(
            player=player,
            depth=player.depth_reached,
            rng=self._rng,
            extra_enemies=patch_effects.extra_enemies_per_sector,
        )
        self._world.recompute_fov()
        self._particles.clear()
        self._floats.clear()
        player.end_turn()
        self._refresh_boss_state()
        # Offer 3 random patches every odd-depth descent (skip depth 1).
        if player.depth_reached >= 2:
            self._open_patch_picker()

    def _refresh_boss_state(self) -> None:
        if self._world is None:
            self._boss_active = False
            return
        boss = self._world.living_boss()
        was_active = self._boss_active
        self._boss_active = boss is not None
        if self._boss_active and not was_active:
            self._boss_banner_ttl = 2.5
            self._glitch_intensity = 1.0
            self._play_sfx("boss_warn")
            if self._sfx is not None:
                self._sfx.start_music("boss")
            label = boss.crash_label if boss is not None else "BOSS"
            self._console.crit(f"!! BOSS PROCESS LOADED: {label} !!")
        elif not self._boss_active and was_active:
            if self._sfx is not None:
                self._sfx.start_music("main")

    def _open_patch_picker(self) -> None:
        if len(PATCH_CATALOG) < 3:  # pragma: no cover
            return
        self._patch_choices = self._rng.sample(list(PATCH_CATALOG), k=3)
        self._patch_pick_index = 0
        self._state = GameState.PATCH_PICK

    def _enter_game_over(self) -> None:
        assert self._world is not None
        if self._world.player.crash_cause is None:
            self._world.player.crash_cause = "Out of RAM"
        self._console.crit(f"SYSTEM CRASH — {self._world.player.crash_cause}")
        self._play_sfx("crash")
        self._state = GameState.GAME_OVER

    def _save_run(self) -> None:
        if (
            self._scores is None or self._runs is None or self._meta is None or self._world is None
        ):  # pragma: no cover
            return
        player = self._world.player
        name = self._name_buffer.strip() or "anon_process"
        self._scores.insert(
            player_name=name,
            depth_reached=player.depth_reached,
            total_score=player.score,
            crash_cause=player.crash_cause or "unknown",
        )
        if self._run_meta is not None:
            self._runs.insert(
                player_name=name,
                seed=self._run_meta.seed,
                depth_reached=player.depth_reached,
                total_score=player.score,
                crash_cause=player.crash_cause or "unknown",
                duration_ms=self._run_meta.elapsed_ms(),
            )
            if self._run_meta.is_daily and self._daily_repo is not None:
                self._daily_repo.insert(
                    run_date=self._run_meta.daily_date,
                    player_name=name,
                    seed=self._run_meta.seed,
                    depth_reached=player.depth_reached,
                    total_score=player.score,
                    crash_cause=player.crash_cause or "unknown",
                    duration_ms=self._run_meta.elapsed_ms(),
                )
        # Award bits = score / 10 + depth * 2.
        bits_earned = player.score // 10 + player.depth_reached * 2
        current = self._meta.get_int(_KEY_BITS, 0)
        self._meta.set_int(_KEY_BITS, current + bits_earned)
        log.info(
            "Saved run: name=%s depth=%d score=%d cause=%s bits=+%d",
            name,
            player.depth_reached,
            player.score,
            player.crash_cause,
            bits_earned,
        )

    def _reset_to_menu(self) -> None:
        self._name_buffer = ""
        self._state = GameState.MENU

    def _play_sfx(self, name: str) -> None:
        if self._sfx is not None:
            self._sfx.play(name)

    # ----- shop / stats / high scores plumbing -----

    def _fetch_bits(self) -> int:
        return self._meta.get_int(_KEY_BITS, 0) if self._meta is not None else 0

    def _shop_rows(self) -> list[tuple[str, str, str, int, int, int | None]]:
        if self._upgrades is None:
            return []
        levels = self._upgrades.all_levels()
        rows: list[tuple[str, str, str, int, int, int | None]] = []
        for upgrade in CATALOG:
            level = levels.get(upgrade.key, 0)
            rows.append(
                (
                    upgrade.key,
                    upgrade.label,
                    upgrade.description,
                    level,
                    upgrade.max_level,
                    upgrade.cost_for_next_level(level),
                )
            )
        return rows

    def _buy_selected_upgrade(self) -> None:
        if self._upgrades is None or self._meta is None:
            return
        upgrade = CATALOG[self._shop_index]
        current = self._upgrades.get_level(upgrade.key)
        cost = upgrade.cost_for_next_level(current)
        if cost is None:
            self._shop_message = f"{upgrade.label} is already maxed."
            return
        bits = self._meta.get_int(_KEY_BITS, 0)
        if bits < cost:
            self._shop_message = f"Not enough bits ({bits}/{cost})."
            return
        self._meta.set_int(_KEY_BITS, bits - cost)
        self._upgrades.set_level(upgrade.key, current + 1)
        self._shop_message = f"Purchased {upgrade.label} L{current + 1} for {cost} bits."

    def _settings_rows(self) -> list[tuple[str, str]]:
        s = self._settings
        return [
            ("Music Vol", f"{int(round(s.music_volume * 100))}%"),
            ("SFX Vol", f"{int(round(s.sfx_volume * 100))}%"),
            ("Mute", "ON" if s.muted else "OFF"),
            ("Difficulty", s.difficulty.value),
            ("Theme", s.theme),
            ("Fullscreen", "ON" if s.fullscreen else "OFF"),
            ("UI Scale", f"{s.ui_scale:.2f}x"),
            ("Reduce Motion", "ON" if s.reduce_motion else "OFF"),
            ("CRT Effect", "ON" if s.crt_effect else "OFF"),
            ("Large Text", "ON" if s.large_text else "OFF"),
        ]

    def _fetch_high_scores(self) -> list[tuple[str, int, int, str, str]]:
        if self._scores is None:
            return []
        rows = self._scores.top_n(10)
        return [
            (r.player_name, r.total_score, r.depth_reached, r.crash_cause, r.timestamp)
            for r in rows
        ]

    def _fetch_stats(
        self,
    ) -> tuple[float, dict[str, int], tuple[str, int, int] | None, int]:
        if self._runs is None:
            return (0.0, {}, None, 0)
        runs = self._runs.all()
        avg = self._runs.average_depth()
        deaths = self._runs.deaths_by_cause()
        best = (
            self._runs.best_with_score_fallback(self._scores)
            if self._scores is not None
            else self._runs.best()
        )
        best_tuple: tuple[str, int, int] | None = None
        if best is not None:
            best_tuple = (best.player_name, best.total_score, best.depth_reached)
        return (avg, deaths, best_tuple, len(runs))

    def _fetch_daily_board(self) -> list[tuple[str, int, int, str, str]]:
        if self._daily_repo is None:
            return []
        rows = self._daily_repo.top_for_date(today_iso(), 10)
        return [
            (r.player_name, r.total_score, r.depth_reached, r.crash_cause, r.timestamp)
            for r in rows
        ]

    # ----- tutorial / how-to-play -----

    _TUTORIAL_STEPS: tuple[str, ...] = (
        "Welcome to Kernel Quest. Use ARROW KEYS or WASD to move.",
        "Walk into a Malware tile to ATTACK it. Each move costs 1 CPU cycle.",
        "Pick up GC items to recover RAM. SCAN+ items reveal more of the map.",
        "Press [Q/E/R] to fire programs from your loadout.",
        "Reach the magenta EXIT to descend deeper. Some sectors lock the EXIT until the BOSS dies.",
        "Press [SPACE] to wait, [ESC] anytime to leave the run, [F11] toggles fullscreen.",
        "That's it! Press ENTER to finish the tutorial.",
    )

    def _start_tutorial(self) -> None:
        self._is_tutorial_run = True
        self._tutorial_step = 0
        self._console.clear()
        self._console.info("TUTORIAL — read the on-screen prompts and press ENTER to advance.")
        self._state = GameState.TUTORIAL
        if self._sfx is not None:
            self._sfx.start_music("tutorial")

    def _handle_tutorial_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE,):
            self._end_tutorial()
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._tutorial_step += 1
            if self._tutorial_step >= len(self._TUTORIAL_STEPS):
                self._end_tutorial()

    def _end_tutorial(self) -> None:
        if self._meta is not None:
            settings_module.mark_tutorial_done(self._meta)
        self._is_tutorial_run = False
        if self._sfx is not None:
            self._sfx.start_music("main")
        self._state = GameState.MENU

    def _open_howtoplay(self) -> None:
        if not self._howtoplay_lines:
            self._howtoplay_lines = self._load_howtoplay_lines()
        self._howtoplay_scroll = 0
        self._state = GameState.HOWTOPLAY

    def _load_howtoplay_lines(self) -> list[str]:
        path = Path("HOWTOPLAY.md")
        if not path.exists():
            return [
                "HOWTOPLAY.md not found.",
                "See the in-game tutorial for instructions.",
            ]
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except OSError:  # pragma: no cover
            return ["Failed to read HOWTOPLAY.md."]

    def _handle_howtoplay_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._state = GameState.MENU
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._howtoplay_scroll = max(0, self._howtoplay_scroll - 1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._howtoplay_scroll = min(
                max(0, len(self._howtoplay_lines) - 8), self._howtoplay_scroll + 1
            )
        elif event.key == pygame.K_PAGEUP:
            self._howtoplay_scroll = max(0, self._howtoplay_scroll - 10)
        elif event.key == pygame.K_PAGEDOWN:
            self._howtoplay_scroll = min(
                max(0, len(self._howtoplay_lines) - 8), self._howtoplay_scroll + 10
            )


def _key_to_delta(key: int) -> tuple[int, int] | None:
    if key in (pygame.K_LEFT, pygame.K_a):
        return (-1, 0)
    if key in (pygame.K_RIGHT, pygame.K_d):
        return (1, 0)
    if key in (pygame.K_UP, pygame.K_w):
        return (0, -1)
    if key in (pygame.K_DOWN, pygame.K_s):
        return (0, 1)
    return None


def _key_to_slot(key: int) -> int | None:
    mapping = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
        pygame.K_5: 4,
        pygame.K_6: 5,
        pygame.K_7: 6,
        pygame.K_8: 7,
        pygame.K_9: 8,
    }
    return mapping.get(key)


def _key_to_program_slot(key: int) -> int | None:
    mapping = {
        pygame.K_q: 0,
        pygame.K_e: 1,
        pygame.K_r: 2,
    }
    return mapping.get(key)
