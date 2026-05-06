"""Game engine: pygame init, main loop, top-level state machine."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

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
from kernelquest.core.run_progress import (
    MilestoneKind,
    RunProgress,
)
from kernelquest.core.settings import Settings
from kernelquest.core.state import GameState
from kernelquest.core.states import GameStateHandler, build_state_registry
from kernelquest.data.database import Database
from kernelquest.data.distros_catalog import (
    DISTROS,
    Distro,
    first_distro_key,
    get_distro,
    next_in_chain,
)
from kernelquest.data.lore_catalog import (
    CATALOG as LORE_CATALOG,
)
from kernelquest.data.lore_catalog import (
    ENDING_FRAMES,
    INTRO_FRAMES,
    STACK_TRACE_LINES,
)
from kernelquest.data.lore_catalog import (
    for_condition as lore_for_condition,
)
from kernelquest.data.repositories import (
    CombatLogRepository,
    DaemonRepository,
    DailyRunRepository,
    DistroRepository,
    IntelRepository,
    LoreRepository,
    MetaRepository,
    MilestoneRepository,
    RunRepository,
    ScoreRepository,
    SkipTagRepository,
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
from kernelquest.entities.damage import DamageType
from kernelquest.entities.items import ALL_ITEM_IDS, get_item
from kernelquest.entities.malware import (
    BufferOverflowBoss,
    DeadlockTwin,
    KernelPanic,
    Malware,
    RootkitHydra,
    SegFault,
    TheLeak,
    ZeroDayBoss,
    ZombieProcess,
)
from kernelquest.entities.malware_registry import maybe_get as maybe_get_species
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.patch import Patch, PatchEffects, PatchState
from kernelquest.entities.player import Player
from kernelquest.entities.program import CATALOG as PROGRAM_CATALOG
from kernelquest.entities.program import ProgramSlot, get_program, starter_loadout
from kernelquest.entities.skip_tag import CATALOG as SKIP_TAG_CATALOG
from kernelquest.entities.skip_tag import SkipTag
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import fire_death_effects, player_attack
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
from kernelquest.ui.cinematics import CinematicPlayer
from kernelquest.ui.console_log import ConsoleLog, LogLevel
from kernelquest.ui.fx import FloatingTextSystem, ParticleSystem, ScreenShake
from kernelquest.ui.music import StemMixer
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.sfx import SoundManager
from kernelquest.ui.sprites import get_player_palette
from kernelquest.ui.viewport import Viewport
from kernelquest.world.daily import today_iso, today_seed
from kernelquest.world.generator import generate_world
from kernelquest.world.tile import TileType
from kernelquest.world.tutorial_range import (
    CURRICULUM,
    Lesson,
    LessonProgress,
    RangeArena,
    build_range_world,
    load_range_arena,
)
from kernelquest.world.world import World

log = logging.getLogger(__name__)

_KEY_BITS = "meta.bits"

_POLYGON_KINDS: tuple[str, ...] = ("enemy", "item", "program", "daemon", "patch")

_MENU_OPTIONS: tuple[str, ...] = (
    "new_run",
    "daily_run",
    "training",
    "howtoplay",
    "codex",
    "high_scores",
    "daily_board",
    "stats",
    "shop",
    "settings",
    "quit",
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
        self._lore_repo: LoreRepository | None = None
        self._intel_repo: IntelRepository | None = None
        self._combat_log_repo: CombatLogRepository | None = None
        self._distros_repo: DistroRepository | None = None
        self._milestones_repo: MilestoneRepository | None = None
        self._skip_tags_repo: SkipTagRepository | None = None
        # Phase 8 — per-run summary buckets keyed by (program_key, species_key).
        self._run_combat_log: dict[tuple[str, str], dict[str, int]] = {}
        # Inspect mode + bestiary navigation.
        self._inspect_index: int = 0
        self._bestiary_scroll: int = 0
        self._post_run_summary: list[tuple[str, str, int, int]] = []
        # Phase 8 — adaptive music director.
        self._music: StemMixer = StemMixer()
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
        # Phase 10 — Interactive Tutorial Range.
        self._range_arena: RangeArena | None = None
        self._lesson_progress: LessonProgress = LessonProgress()
        self._lesson_index: int = 0
        self._range_completed: bool = False
        self._polygon_open: bool = False
        self._polygon_kind_index: int = 0
        self._polygon_item_index: int = 0
        self._range_god_mode: bool = False
        self._range_infinite_cycles: bool = False
        self._range_full_fov: bool = False
        # Phase 11 — distros & structured runs.
        self._run_progress: RunProgress | None = None
        self._distro_index: int = 0
        self._distro: Distro | None = None
        self._milestone_result_panel: dict[str, object] = {}
        self._vendor_stock: list[dict[str, object]] = []
        self._vendor_index: int = 0
        self._vendor_message: str | None = None
        self._vendor_free: bool = False  # set by the "free_vendor" skip tag
        self._double_bits_pending: bool = False
        self._extra_daemon_slot_pending: bool = False
        self._bonus_score_pending: int = 0
        self._run_summary_payload: dict[str, object] = {}
        self._run_was_successful: bool = False
        self._meta_bits_snapshot: int = 0
        # Phase 7 — narrative state.
        self._cinematic: CinematicPlayer | None = None
        self._cinematic_kind: str = ""  # "intro" | "ending"
        self._codex_index: int = 0
        self._stack_trace_lines: list[tuple[str, str]] = []
        self._first_kill_pending: bool = True
        self._first_pickup_pending: bool = True
        self._first_descent_pending: bool = True
        self._first_boss_pending: bool = True
        self._first_crash_pending: bool = True
        # State Pattern — concrete handlers keyed by ``GameState``.
        self._state_handlers: dict[GameState, GameStateHandler] = build_state_registry()

    @property
    def _active_state(self) -> GameStateHandler | None:
        """Return the handler for the current :class:`GameState`, if any.

        :attr:`GameState.QUIT` has no handler; in that case the main loop
        terminates so callers never need to dispatch through it.
        """
        return self._state_handlers.get(self._state)

    # ----- public helpers used by state handlers -----

    def start_new_run(self, *, daily: bool = False, distro_key: str | None = None) -> None:
        """Public entry point for state handlers to launch a fresh run."""
        self._start_new_run(daily=daily, distro_key=distro_key)

    def reset_to_menu(self) -> None:
        """Public entry point for state handlers to return to the main menu."""
        self._reset_to_menu()

    def compute_bonus(self) -> PlayerBonus:
        """Public passthrough for state handlers needing the run-start bonus."""
        return self._compute_bonus()

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
        self._lore_repo = LoreRepository(self._database)
        self._intel_repo = IntelRepository(self._database)
        self._combat_log_repo = CombatLogRepository(self._database)
        # Phase 11 — distros, milestones, skip tags.
        self._distros_repo = DistroRepository(self._database)
        self._milestones_repo = MilestoneRepository(self._database)
        self._skip_tags_repo = SkipTagRepository(self._database)
        self._distros_repo.ensure_seeded(
            [d.key for d in DISTROS], first_unlocked=first_distro_key()
        )
        self._settings = settings_module.load(self._meta)
        # Phase 11 — apply persisted locale immediately so first frame is correct.
        from kernelquest.ui import i18n as _i18n

        _i18n.set_language(self._settings.language)
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
            self._sfx.start_music("safe")
            clock = pygame.time.Clock()

            # Apply persisted player palette to the renderer.
            ui.player_palette = get_player_palette(self._settings.player_palette)

            assert self._meta is not None
            # Phase 7 — first-launch intro cutscene (replaces text "first boot").
            if not settings_module.is_intro_seen(self._meta):
                self._start_intro()

            # First-launch onboarding nudge (after intro auto-skips).
            if not settings_module.is_tutorial_done(self._meta):
                self._console.cron("try the Tutorial from the main menu.")

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
        if self._cinematic is not None and self._state in (GameState.INTRO, GameState.ENDING):
            self._cinematic.step(dt)
            if self._cinematic.finished:
                self._end_cinematic()
        # Phase 8 — adaptive music crossfade.
        self._music.step(dt)
        if self._sfx is not None:
            self._sfx.apply_stem_volumes(self._music.current_volumes())

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

            handler = self._active_state
            if handler is not None:
                handler.handle_event(self, event)

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
            self._state = GameState.QUIT_CONFIRM
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._menu_index = (self._menu_index - 1) % len(_MENU_OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._menu_index = (self._menu_index + 1) % len(_MENU_OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate_menu_option()

    def _activate_menu_option(self) -> None:
        choice = _MENU_OPTIONS[self._menu_index]
        if choice == "new_run":
            self._open_distro_select(daily=False)
        elif choice == "daily_run":
            self._open_distro_select(daily=True)
        elif choice == "training":
            self._start_tutorial_range()
        elif choice == "howtoplay":
            self._start_tutorial()
        elif choice == "codex":
            self._open_codex()
        elif choice == "high_scores":
            self._state = GameState.HIGH_SCORES
        elif choice == "daily_board":
            self._state = GameState.DAILY_BOARD
        elif choice == "stats":
            self._state = GameState.STATS
        elif choice == "shop":
            self._shop_index = 0
            self._shop_message = None
            self._state = GameState.SHOP
        elif choice == "settings":
            self._settings_index = 0
            self._state = GameState.SETTINGS
        elif choice == "quit":
            self._state = GameState.QUIT_CONFIRM

    def _handle_back_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._state = GameState.MENU

    def _handle_quit_confirm_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._state = GameState.QUIT
        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
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
        "palette",
        "auto_skip_intro",
        "language",
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
        elif key == "palette":
            self._settings.cycle_palette(direction)
            if self._ui is not None:
                self._ui.player_palette = get_player_palette(self._settings.player_palette)
        elif key == "auto_skip_intro":
            self._settings.toggle_auto_skip_intro()
        elif key == "language":
            self._settings.cycle_language(direction)

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
                player.crash_cause = "SIGINT — manual exit"
            self._enter_game_over()
            return

        if event.key in (pygame.K_QUESTION, pygame.K_SLASH, pygame.K_F1):
            self._show_help_overlay = not self._show_help_overlay
            return

        if event.key == pygame.K_i:
            self._enter_inspect_mode()
            return

        if event.key == pygame.K_b:
            self._state = GameState.BESTIARY
            self._bestiary_scroll = 0
            return

        if event.key == pygame.K_SPACE:
            self._end_player_turn()
            return

        program_slot = _key_to_program_slot(event.key)
        if program_slot is not None:
            result = execute_program(world, program_slot, self._rng)
            self._console.info(result.message)
            if result.success:
                self._track_lesson("programs_fired", key=result.program_key or "")
                if result.program_key and result.target_species:
                    self._record_combat(
                        program_key=result.program_key,
                        species_key=result.target_species,
                        damage=result.damage_dealt,
                        killed=1 if result.killed_enemy is not None else 0,
                    )
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
        handler = self._active_state
        if handler is not None:
            handler.render(self, ui)
        ui.present()

    # ----- transitions -----

    def _start_new_run(self, *, daily: bool = False, distro_key: str | None = None) -> None:
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

        # Phase 11 — pick the active distro (default to first available).
        distro = get_distro(distro_key or first_distro_key())
        self._distro = distro
        self._run_progress = RunProgress(distro_key=distro.key)
        self._vendor_free = False
        self._double_bits_pending = False
        self._extra_daemon_slot_pending = False
        self._bonus_score_pending = 0
        self._run_was_successful = False
        self._run_summary_payload = {}
        # Phase 11 — snapshot meta bits so failed runs revert to this value.
        if self._meta is not None:
            self._meta_bits_snapshot = self._meta.get_int(_KEY_BITS, 0)

        bonus = self._compute_bonus()
        max_ram = PLAYER_START_RAM + bonus.bonus_ram + distro.bonus_ram
        max_cycles = PLAYER_START_CPU_CYCLES + bonus.bonus_cycles + distro.bonus_cycles
        max_cycles = max(1, max_cycles)
        player = Player(
            max_ram=max_ram,
            ram=max_ram,
            max_cpu_cycles=max_cycles,
            cpu_cycles=max_cycles,
            cache_capacity=PLAYER_CACHE_CAPACITY + bonus.bonus_cache + distro.bonus_cache,
            base_damage=PLAYER_BASE_DAMAGE + bonus.bonus_damage + distro.bonus_damage,
            bonus_scan_radius=bonus.bonus_scan_radius,
        )
        # Phase 5 — equip programs and persisted daemons. Phase 11 — distro overrides.
        if distro.starter_program_keys:
            slots: list[ProgramSlot] = []
            for prog_key in distro.starter_program_keys:
                try:
                    prog = get_program(prog_key)
                except KeyError:
                    continue
                slots.append(ProgramSlot(program=prog, charges=prog.max_charges))
            player.programs = slots if slots else starter_loadout()
        else:
            player.programs = starter_loadout()
        player.daemons = self._equipped_daemons()
        if distro.starter_daemon_keys:
            for d_key in distro.starter_daemon_keys:
                try:
                    player.daemons.append(get_daemon(d_key))
                except KeyError:
                    continue
        if distro.random_starter_daemons > 0:
            extras = self._rng.sample(
                list(DAEMON_CATALOG),
                k=min(distro.random_starter_daemons, len(DAEMON_CATALOG)),
            )
            for d in extras:
                player.daemons.append(d)

        self._world = generate_world(player=player, depth=1, rng=self._rng)
        self._world.recompute_fov()
        self._viewport = self._make_viewport(self._world)
        self._name_buffer = ""
        self._console.clear()
        prefix = "DAILY " if daily else ""
        self._console.kernel(
            f"{prefix}init(0) spawned in sector 0x{player.depth_reached:02X} "
            f"(seed={seed}, distro={distro.name})"
        )
        self._particles.clear()
        if self._sfx is not None:
            self._sfx.start_music("main")
        self._refresh_boss_state()
        # Begin milestone bookkeeping for release 0, milestone 0.
        self._run_progress.begin_milestone(player.score + self._bonus_score_pending)
        if self._bonus_score_pending:
            player.score += self._bonus_score_pending
            self._bonus_score_pending = 0
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
        result = player_attack(
            self._world,
            enemy,
            self._rng,
            damage=damage,
            damage_type=DamageType.KINETIC,
            program_key="bump",
        )
        self._record_combat(
            program_key="bump",
            species_key=enemy.species_key,
            damage=result.damage_dealt,
            killed=1 if result.killed else 0,
        )
        self._console.info(result.log_message)
        self._play_sfx("attack")
        if result.phase_advanced is not None:
            self._on_boss_phase_advanced(enemy, result.phase_advanced)
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

    def _record_combat(
        self,
        *,
        program_key: str,
        species_key: str,
        damage: int,
        killed: int,
    ) -> None:
        if not species_key:
            return
        if damage > 0 and self._intel_repo is not None:
            self._intel_repo.record_damage_to(species_key, damage)
        bucket = self._run_combat_log.setdefault(
            (program_key, species_key), {"damage": 0, "kills": 0}
        )
        bucket["damage"] += max(0, damage)
        bucket["kills"] += max(0, killed)

    def _on_enemy_killed(self, enemy: Malware) -> None:
        assert self._world is not None
        player = self._world.player
        self._shake.punch(SCREEN_SHAKE_KILL_INTENSITY)
        # Phase 10 — curriculum tracking.
        self._track_lesson("enemies_killed")
        # Phase 8 \u2014 fire affix on-death side effects (Volatile blast etc.)
        for line in fire_death_effects(self._world, enemy):
            self._console.warn(line)
        # Phase 8 \u2014 intel kill record.
        if self._intel_repo is not None and enemy.species_key:
            self._intel_repo.record_kill(enemy.species_key)
        self._world.remove_dead_enemies()
        self._play_sfx("explode")
        # Phase 7 lore unlocks.
        if self._first_kill_pending:
            self._first_kill_pending = False
            self._unlock_lore_for("first_kill")
        if getattr(enemy, "is_boss", False) and self._first_boss_pending:
            self._first_boss_pending = False
            self._unlock_lore_for("first_boss")
        # Phase 9 — per-boss lore + bestiary trophy on first kill.
        if getattr(enemy, "is_boss", False) and enemy.species_key:
            self._unlock_lore_for(f"boss_{enemy.species_key}")
            if self._intel_repo is not None:
                self._intel_repo.reveal(enemy.species_key)
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
        # Phase 9 — every new boss species awards a daemon on first kill.
        if isinstance(
            enemy, (TheLeak, DeadlockTwin, RootkitHydra, BufferOverflowBoss, ZeroDayBoss)
        ):
            self._maybe_award_daemon(force=True)
        # Boss defeated — release lock and restore main music.
        if getattr(enemy, "is_boss", False) and not self._world.has_living_boss:
            self._boss_active = False
            self._glitch_intensity = 0.0
            self._console.kernel("BOSS terminated. EXIT unlocked.")
            if self._sfx is not None:
                self._sfx.start_music("main")
            # Phase 7 — true-ending trigger (placeholder hook; Phase 11 will
            # gate this on full run success criteria).
            if isinstance(enemy, KernelPanic):
                self._unlock_lore_for("true_ending")
                # Phase 11: during a structured run, the ending only fires
                # from _finish_run(success=True) so the player still has to
                # clear the remaining releases.
                if self._run_progress is None:
                    self._start_ending()

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
        # Phase 10 — curriculum tracking.
        self._track_lesson("moved_steps")

        message = pickup_item_at(self._world, player.position)
        if message is not None:
            patch_effects = self._patches.effects()
            self._console.info(message)
            self._play_sfx("pickup")
            self._track_lesson("items_collected")
            if self._first_pickup_pending:
                self._first_pickup_pending = False
                self._unlock_lore_for("first_pickup")
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
                self._console.kernel(f"EXIT LOCKED — terminate {label} first.", LogLevel.CRIT)
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
        # Phase 8 — refresh adaptive music targets from visible enemies.
        self._refresh_music_targets()
        if not player.is_alive:
            self._enter_game_over()
            return
        if player.cpu_cycles == 0:
            self._end_player_turn()

    def _refresh_music_targets(self) -> None:
        if self._world is None:
            return
        from kernelquest.entities.malware_registry import maybe_get as _maybe

        archetypes = set()
        any_alive = False
        for enemy in self._world.enemies:
            if not enemy.is_alive:
                continue
            any_alive = True
            if enemy.position not in self._world.visible:
                continue
            sp = _maybe(enemy.species_key)
            if sp is not None:
                archetypes.add(sp.archetype)
        safe_zone = not any_alive and not self._boss_active
        self._music.update_targets(
            archetypes,
            boss_active=self._boss_active,
            reduce_motion=self._settings.reduce_motion,
            safe_zone=safe_zone,
        )
        # Phase 9 — swap track to a safe-zone signal when the sector is clear.
        if self._sfx is not None and not self._boss_active:
            target_track = "safe" if safe_zone else "main"
            if self._sfx.current_track != target_track:
                self._sfx.start_music(target_track)

    def _make_viewport(self, world: World) -> Viewport:
        """Phase 9 — fit the map within the play area without overlapping the
        right-side HUD column or the bottom console strip.
        """
        hud_width = 280
        console_height = 120
        margin = 16
        avail_w = max(160, WINDOW_WIDTH - hud_width - margin * 2)
        avail_h = max(160, WINDOW_HEIGHT - console_height - margin * 3)
        gw = max(1, world.grid.width)
        gh = max(1, world.grid.height)
        tile = max(8, min(avail_w // gw, avail_h // gh))
        ox = margin + (avail_w - gw * tile) // 2
        oy = margin + (avail_h - gh * tile) // 2
        return Viewport(origin_x=ox, origin_y=oy, tile_size=tile)

    def _boss_music_track(self, boss: Malware) -> str:
        if isinstance(boss, TheLeak):
            return "the_leak"
        if isinstance(boss, DeadlockTwin):
            return "deadlock"
        if isinstance(boss, RootkitHydra):
            return "hydra"
        if isinstance(boss, BufferOverflowBoss):
            return "buffer_overflow"
        if isinstance(boss, ZeroDayBoss):
            return "zero_day"
        return "boss"

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
        """Phase 11 — EXIT reached. Close the current milestone and gate the
        next sector behind the result screen + vendor.
        """
        assert self._world is not None
        # Tutorial Range / non-structured paths skip Phase 11 progression.
        if self._run_progress is None:
            self._generate_next_sector()
            return
        self._finish_current_milestone(reached_exit=True)

    def _finish_current_milestone(self, *, reached_exit: bool) -> None:
        """Close the active milestone; transition to the result screen / failure.

        Reaching the EXIT is enough to advance — the score *target* is now a
        bonus goal, not a hard fail-state. Hitting it grants extra bits and
        marks the milestone as ``target_hit`` for the result UI.
        """
        assert self._world is not None
        assert self._run_progress is not None
        player = self._world.player
        score_in_milestone = self._run_progress.milestone_score(player.score)
        target = self._run_progress.current_target
        target_hit = score_in_milestone >= target
        # Reaching the exit always clears the milestone now. Failing the run
        # only happens through actual death (handled by _enter_game_over).
        cleared = reached_exit
        kind = self._run_progress.current_kind

        rec = self._run_progress.finish_current(
            reached_score=score_in_milestone,
            was_skipped=False,
            was_cleared=cleared,
        )

        # Bits earned per milestone — base + bonuses + skip-tag multiplier.
        kill_mult = self._distro.bits_kill_multiplier if self._distro is not None else 1.0
        bits = int(round(score_in_milestone / 25 * kill_mult))
        if target_hit:
            bits += 5  # bonus for hitting the score goal
        if self._double_bits_pending:
            bits *= 2
            self._double_bits_pending = False
        self._milestone_result_panel = {
            "release_index": rec.release_index,
            "milestone_index": rec.milestone_index,
            "kind": kind.value,
            "score": score_in_milestone,
            "target": target,
            "bits": bits,
            "cleared": cleared,
            "target_hit": target_hit,
            "boss": kind is MilestoneKind.BOSS,
        }

        if not cleared:
            # Should not happen — _descend only calls us with reached_exit=True.
            player.crash_cause = player.crash_cause or "Target missed"
            self._enter_game_over()
            return

        # Award milestone bits up front (in-run currency).
        if self._meta is not None:
            current = self._meta.get_int(_KEY_BITS, 0)
            self._meta.set_int(_KEY_BITS, current + bits)
        self._console.info(
            f"milestone {rec.release_index + 1}.{rec.milestone_index + 1} "
            f"cleared (+{bits}b{', target hit' if target_hit else ''})"
        )
        self._state = GameState.MILESTONE_RESULT

    def _generate_next_sector(self) -> None:
        """Generate the next world. Used by both the tutorial path and Phase 11
        once the milestone result / vendor screens are dismissed.
        """
        assert self._world is not None
        player = self._world.player
        player.depth_reached += 1
        player.score += SCORE_PER_DESCENT
        self._console.kernel(f"sector 0x{player.depth_reached:02X} mapped.")
        self._play_sfx("descend")
        # Phase 7 — fire depth-gated lore unlocks.
        if self._first_descent_pending and player.depth_reached >= 2:
            self._first_descent_pending = False
            self._unlock_lore_for("first_descent")
        if player.depth_reached >= 5:
            self._unlock_lore_for("sector_5")
        if player.depth_reached >= 10:
            self._unlock_lore_for("sector_10")
        if player.depth_reached >= 15:
            self._unlock_lore_for("sector_15")
        patch_effects = self._patches.effects()
        self._world = generate_world(
            player=player,
            depth=player.depth_reached,
            rng=self._rng,
            extra_enemies=patch_effects.extra_enemies_per_sector,
        )
        self._world.recompute_fov()
        self._viewport = self._make_viewport(self._world)
        self._particles.clear()
        self._floats.clear()
        player.end_turn()
        self._refresh_boss_state()
        # Phase 11 — start the next milestone's score window.
        if self._run_progress is not None:
            self._run_progress.begin_milestone(player.score)
            if self._bonus_score_pending > 0:
                player.score += self._bonus_score_pending
                self._console.info(f"skip-tag bonus: +{self._bonus_score_pending} score")
                self._bonus_score_pending = 0
        # Stack-trace interstitial precedes the patch picker (Phase 7.4).
        self._open_stack_trace()

    def _on_boss_phase_advanced(self, enemy: Malware, phase: object) -> None:
        """Phase 9 — react to a boss entering its next phase."""
        # ``phase`` is a BossPhase; typed loosely to avoid an extra import.
        from kernelquest.entities.boss_phases import BossPhase

        if not isinstance(phase, BossPhase):  # pragma: no cover
            return
        self._console.crit(f"-- {enemy.crash_label}: PHASE = {phase.name} --")
        if phase.telegraph:
            self._console.warn(phase.telegraph)
        self._glitch_intensity = max(self._glitch_intensity, 0.8)
        self._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
        if self._sfx is not None and phase.music_overlay:
            # Re-trigger the boss track to "swap into" the overlay layer.
            self._sfx.start_music(self._boss_music_track(enemy))
        # Phase 10 — curriculum tracking.
        self._track_lesson("boss_phases_seen")

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
            if self._sfx is not None and boss is not None:
                self._sfx.start_music(self._boss_music_track(boss))
            label = boss.crash_label if boss is not None else "BOSS"
            self._console.kernel(f"!! BOSS PROCESS LOADED: {label} !!", LogLevel.CRIT)
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
        cause = self._world.player.crash_cause
        self._console.crit(f"[init] core dumped — signal: {cause}")
        self._play_sfx("crash")
        # Phase 7 lore unlocks.
        if self._first_crash_pending:
            self._first_crash_pending = False
            self._unlock_lore_for("first_crash")
        # Crash-cause-specific lore (e.g. ``cause_Logic Bomb``).
        self._unlock_lore_for(f"cause_{cause}")
        # Phase 8 — compute post-run summary rows + persist combat log.
        self._post_run_summary = self._compose_run_summary()
        self._persist_combat_log()
        self._state = GameState.GAME_OVER

    def _compose_run_summary(self) -> list[tuple[str, str, int, int]]:
        from kernelquest.entities.malware_registry import maybe_get as _maybe

        rows: list[tuple[str, str, int, int]] = []
        for (prog, species), stats in self._run_combat_log.items():
            sp = _maybe(species)
            label = sp.label if sp is not None else species
            rows.append((prog, label, stats["damage"], stats["kills"]))
        rows.sort(key=lambda r: r[2], reverse=True)
        return rows[:10]

    def _persist_combat_log(self) -> None:
        if self._combat_log_repo is None:
            return
        for (prog, species), stats in self._run_combat_log.items():
            self._combat_log_repo.insert(
                program_key=prog,
                species_key=species,
                damage=stats["damage"],
                kills=stats["kills"],
            )
        self._run_combat_log.clear()

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
            run_id = self._runs.insert(
                player_name=name,
                seed=self._run_meta.seed,
                depth_reached=player.depth_reached,
                total_score=player.score,
                crash_cause=player.crash_cause or "unknown",
                duration_ms=self._run_meta.elapsed_ms(),
                distro_key=self._distro.key if self._distro is not None else None,
                is_successful=False,
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
            # Phase 11 — record milestone trail / skip tags even on failure.
            self._persist_phase11_artifacts(run_id)
        # Phase 11 — failed run forfeits all in-run bits earned this run.
        if self._run_progress is not None:
            self._meta.set_int(_KEY_BITS, self._meta_bits_snapshot)
            bits_earned = 0
        else:
            # Tutorial / legacy path keeps old reward formula.
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
        from kernelquest.ui.i18n import t

        s = self._settings
        on = t("settings.on")
        off = t("settings.off")
        return [
            (t("settings.music_vol"), f"{int(round(s.music_volume * 100))}%"),
            (t("settings.sfx_vol"), f"{int(round(s.sfx_volume * 100))}%"),
            (t("settings.mute"), on if s.muted else off),
            (t("settings.difficulty"), s.difficulty.value),
            (t("settings.theme"), s.theme),
            (t("settings.fullscreen"), on if s.fullscreen else off),
            (t("settings.ui_scale"), f"{s.ui_scale:.2f}x"),
            (t("settings.reduce_motion"), on if s.reduce_motion else off),
            (t("settings.crt"), on if s.crt_effect else off),
            (t("settings.large_text"), on if s.large_text else off),
            (t("settings.palette"), s.player_palette),
            (t("settings.auto_skip_intro"), on if s.auto_skip_intro else off),
            (t("settings.language"), s.language.upper()),
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

    def _start_tutorial(self) -> None:
        self._tutorial_step = 0
        self._console.clear()
        self._state = GameState.TUTORIAL
        if self._sfx is not None:
            self._sfx.start_music("tutorial")

    def _handle_tutorial_key(self, event: pygame.event.Event) -> None:
        from kernelquest.ui.renderer import TUTORIAL_PAGE_COUNT

        if event.key == pygame.K_ESCAPE:
            self._end_tutorial()
            return
        if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_PAGEUP):
            self._tutorial_step = max(0, self._tutorial_step - 1)
        elif event.key in (
            pygame.K_RIGHT,
            pygame.K_d,
            pygame.K_PAGEDOWN,
            pygame.K_SPACE,
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
        ):
            if self._tutorial_step >= TUTORIAL_PAGE_COUNT - 1:
                self._end_tutorial()
            else:
                self._tutorial_step += 1

    def _end_tutorial(self) -> None:
        if self._meta is not None:
            settings_module.mark_tutorial_done(self._meta)
        if self._sfx is not None:
            self._sfx.start_music("safe")
        self._state = GameState.MENU

    # ----- Phase 10: Tutorial Range -----

    def _start_tutorial_range(self) -> None:
        """Boot the Range scene with curriculum + free-play sandbox."""
        from kernelquest.entities.malware import KernelPanic, SyntaxError_
        from kernelquest.entities.player import Player

        arena = load_range_arena()
        self._range_arena = arena

        # Fresh player with full toolkit so all lessons are reachable.
        player = Player(position=arena.spawn, max_ram=80, ram=80)
        player.programs = starter_loadout()
        # Start with one of every daemon, equip cron + tcpdump.
        player.daemons = [DAEMON_CATALOG[0], DAEMON_CATALOG[3]]
        player.cache = ["gc", "opt", "scan"][: player.cache_capacity]

        world = build_range_world(player, arena)

        # Drop a soft enemy in the Combat Pit.
        combat_room = next(r for r in arena.rooms if r.key == "combat")
        enemy = SyntaxError_(position=(combat_room.x + 2, combat_room.y + 2))
        enemy.hp = max(1, enemy.hp // 4)
        world.enemies.append(enemy)

        # Drop a training dummy boss in the Boss Simulator with low HP per phase.
        boss_room = next(r for r in arena.rooms if r.key == "boss")
        boss = KernelPanic(position=(boss_room.x + 2, boss_room.y + 2))
        boss.max_hp = 6
        boss.hp = 6
        boss.damage = 2
        world.enemies.append(boss)

        # Sprinkle one of each item type across the Item Lab floor.
        item_room = next(r for r in arena.rooms if r.key == "items")
        item_positions = [
            (item_room.x + 1, item_room.y + 1),
            (item_room.x + 3, item_room.y + 1),
            (item_room.x + 1, item_room.y + 3),
        ]
        for pos, item_id in zip(item_positions, ALL_ITEM_IDS, strict=False):
            world.items[pos] = item_id

        self._world = world
        self._viewport = self._make_viewport(world)
        self._is_tutorial_run = True
        self._range_completed = False
        self._lesson_progress.reset()
        self._lesson_index = 0
        self._polygon_open = False
        self._polygon_kind_index = 0
        self._polygon_item_index = 0
        self._range_god_mode = False
        self._range_infinite_cycles = False
        self._range_full_fov = False
        self._patches = PatchState()
        self._patch_choices = []
        self._console.clear()
        self._console.kernel("/dev/sandbox loaded — no DB writes will be made.")
        self._console.info("L1 — take 5 steps to begin.")
        if self._sfx is not None:
            self._sfx.start_music("tutorial")
        self._refresh_boss_state()  # arms the dummy boss banner if needed.
        world.recompute_fov()
        self._state = GameState.TUTORIAL_RANGE

    def _close_tutorial_range(self) -> None:
        """Tear down the Range and return to the main menu without persisting."""
        if self._meta is not None:
            settings_module.mark_tutorial_done(self._meta)
        self._world = None
        self._range_arena = None
        self._is_tutorial_run = False
        self._polygon_open = False
        if self._sfx is not None:
            self._sfx.start_music("main")
        self._state = GameState.MENU

    def _current_lesson(self) -> Lesson | None:
        if self._lesson_index >= len(CURRICULUM):
            return None
        return CURRICULUM[self._lesson_index]

    def _check_lesson_completion(self) -> None:
        """Advance the curriculum index when the current lesson's goal is met."""
        lesson = self._current_lesson()
        if lesson is None:
            return
        if lesson.is_complete(self._lesson_progress):
            self._console.kernel(f"{lesson.title} complete!", LogLevel.CRIT)
            self._lesson_index += 1
            nxt = self._current_lesson()
            if nxt is not None:
                self._console.info(f"{nxt.title} — {nxt.hint}")
            else:
                self._range_completed = True
                self._console.kernel(
                    "Curriculum complete. [~] opens the Polygon. [Esc] returns to menu."
                )
                if self._meta is not None:
                    settings_module.mark_tutorial_done(self._meta)

    def _track_lesson(self, field: str, *, amount: int = 1, key: str = "") -> None:
        """Bump a :class:`LessonProgress` counter (no-op outside Range)."""
        if self._state is not GameState.TUTORIAL_RANGE:
            return
        if field == "programs_fired":
            tally = self._lesson_progress.programs_fired
            tally[key] = tally.get(key, 0) + amount
        else:
            current = int(getattr(self._lesson_progress, field, 0))
            setattr(self._lesson_progress, field, current + amount)
        self._check_lesson_completion()

    def _handle_range_key(self, event: pygame.event.Event) -> None:
        """Key handler for ``GameState.TUTORIAL_RANGE``."""
        if self._polygon_open:
            self._handle_polygon_key(event)
            return

        if event.key == pygame.K_ESCAPE:
            self._close_tutorial_range()
            return
        if event.key in (pygame.K_BACKQUOTE, pygame.K_TAB):
            self._polygon_open = True
            self._console.info("[Polygon] kind: " + _POLYGON_KINDS[self._polygon_kind_index])
            return
        if event.key == pygame.K_t:
            # Daemon swap drill (cycles equipped daemons through the catalog).
            assert self._world is not None
            equipped = self._world.player.daemons
            cat = list(DAEMON_CATALOG)
            if equipped:
                idx = cat.index(equipped[0]) if equipped[0] in cat else 0
                equipped[0] = cat[(idx + 1) % len(cat)]
            else:
                equipped.append(cat[0])
            self._console.info(f"swapped daemon -> {equipped[0].label}")
            self._track_lesson("daemons_swapped")
            return
        if event.key == pygame.K_p:
            # Patch drill — pick the first patch in the catalog (idempotent).
            patch = PATCH_CATALOG[0]
            if patch not in self._patches.selected:
                self._patches.add(patch)
                self._console.info(f"patch acquired -> {patch.label}")
                self._track_lesson("patches_picked")
            return
        if event.key == pygame.K_F1:
            self._range_god_mode = not self._range_god_mode
            assert self._world is not None
            if self._range_god_mode:
                self._world.player.max_ram = 9999
                self._world.player.ram = 9999
            self._console.info(f"god_mode={self._range_god_mode}")
            return
        if event.key == pygame.K_F2:
            self._range_infinite_cycles = not self._range_infinite_cycles
            self._console.info(f"infinite_cycles={self._range_infinite_cycles}")
            return
        if event.key == pygame.K_F3:
            self._range_full_fov = not self._range_full_fov
            assert self._world is not None
            if self._range_full_fov:
                w, h = self._world.grid.width, self._world.grid.height
                self._world.visible = {(x, y) for x in range(w) for y in range(h)}
                self._world.explored |= self._world.visible
            self._console.info(f"full_fov={self._range_full_fov}")
            return

        # Delegate to the regular gameplay handler for movement / programs / cache.
        self._handle_playing_key(event)
        # Keep range cycles topped up if the toggle is on.
        if self._range_infinite_cycles and self._world is not None:
            self._world.player.cpu_cycles = self._world.player.max_cpu_cycles

    # ----- Polygon (free-play sandbox) -----

    def _polygon_current_entries(self) -> list[tuple[str, str]]:
        """Return ``[(label, explain)]`` rows for the active Polygon kind."""
        from kernelquest.entities.daemon import CATALOG as DC
        from kernelquest.entities.items import ALL_ITEM_IDS as AI
        from kernelquest.entities.malware_registry import SPECIES as MC
        from kernelquest.entities.patch import CATALOG as PC
        from kernelquest.entities.program import CATALOG as PRC
        from kernelquest.ui.explain import explain as _explain

        kind = _POLYGON_KINDS[self._polygon_kind_index]
        rows: list[tuple[str, str]] = []
        if kind == "enemy":
            rows = [(s.label, s.lore_blurb or s.archetype.value) for s in MC]
        elif kind == "item":
            rows = [(get_item(k).label, _explain("item", k)) for k in AI]
        elif kind == "program":
            rows = [(p.label, p.description) for p in PRC]
        elif kind == "daemon":
            rows = [(d.label, d.description) for d in DC]
        elif kind == "patch":
            rows = [(p.label, p.description) for p in PC]
        return rows

    def _handle_polygon_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_BACKQUOTE, pygame.K_ESCAPE):
            self._polygon_open = False
            return
        rows = self._polygon_current_entries()
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._polygon_kind_index = (self._polygon_kind_index - 1) % len(_POLYGON_KINDS)
            self._polygon_item_index = 0
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._polygon_kind_index = (self._polygon_kind_index + 1) % len(_POLYGON_KINDS)
            self._polygon_item_index = 0
        elif event.key in (pygame.K_UP, pygame.K_w):
            if rows:
                self._polygon_item_index = (self._polygon_item_index - 1) % len(rows)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            if rows:
                self._polygon_item_index = (self._polygon_item_index + 1) % len(rows)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._polygon_apply_selection()

    def _polygon_apply_selection(self) -> None:
        """Spawn / grant the currently selected polygon entry."""
        from kernelquest.entities.daemon import CATALOG as DC
        from kernelquest.entities.items import ALL_ITEM_IDS as AI
        from kernelquest.entities.malware_registry import SPECIES as MC
        from kernelquest.entities.malware_registry import factory_for
        from kernelquest.entities.patch import CATALOG as PC
        from kernelquest.entities.program import CATALOG as PRC
        from kernelquest.entities.program import ProgramSlot

        if self._world is None:
            return
        kind = _POLYGON_KINDS[self._polygon_kind_index]
        idx = self._polygon_item_index
        player = self._world.player
        if kind == "enemy" and idx < len(MC):
            sp = MC[idx]
            spawn_pos = self._polygon_spawn_position()
            if spawn_pos is None:
                self._console.warn("no free tile to spawn enemy")
                return
            factory = factory_for(sp.key)
            if factory is None:
                self._console.warn(f"no factory for {sp.key}")
                return
            self._world.enemies.append(factory(spawn_pos))
            self._console.info(f"spawned {sp.label} at {spawn_pos}")
        elif kind == "item" and idx < len(AI):
            spawn_pos = self._polygon_spawn_position()
            if spawn_pos is None:
                self._console.warn("no free tile to drop item")
                return
            self._world.items[spawn_pos] = AI[idx]
            self._console.info(f"dropped {AI[idx]} at {spawn_pos}")
        elif kind == "program" and idx < len(PRC):
            prog = PRC[idx]
            player.programs.append(ProgramSlot(program=prog, charges=prog.max_charges))
            self._console.info(f"granted program {prog.label}")
        elif kind == "daemon" and idx < len(DC):
            d = DC[idx]
            if d not in player.daemons:
                player.daemons.append(d)
                self._console.info(f"granted daemon {d.label}")
        elif kind == "patch" and idx < len(PC):
            p = PC[idx]
            if p not in self._patches.selected:
                self._patches.add(p)
                self._console.info(f"granted patch {p.label}")

    def _polygon_spawn_position(self) -> tuple[int, int] | None:
        """Find a walkable empty tile near the player to drop a polygon spawn."""
        if self._world is None:
            return None
        px, py = self._world.player.position
        for radius in range(1, 4):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    pos = (px + dx, py + dy)
                    if pos == self._world.player.position:
                        continue
                    if not self._world.grid.is_walkable(*pos):
                        continue
                    if self._world.enemy_at(pos) is not None:
                        continue
                    if pos in self._world.items:
                        continue
                    return pos
        return None

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

    # ----- Phase 7 narrative plumbing -----

    def _unlock_lore_for(self, condition: str) -> None:
        """If ``condition`` matches a `LoreEntry`, mark it unlocked and toast.

        Idempotent — repeat calls only log on the very first unlock.
        """
        if self._lore_repo is None:
            return
        entry = lore_for_condition(condition)
        if entry is None:
            return
        if self._lore_repo.unlock(entry.key):
            self._console.kernel(f"codex unlocked — {entry.title}")

    def _start_intro(self) -> None:
        if (
            self._meta is not None
            and self._settings.auto_skip_intro
            and (settings_module.is_intro_seen(self._meta))
        ):
            return
        self._cinematic = CinematicPlayer(frames=INTRO_FRAMES)
        self._cinematic.start()
        self._cinematic_kind = "intro"
        self._unlock_lore_for("first_boot")
        self._state = GameState.INTRO

    def _start_ending(self) -> None:
        self._cinematic = CinematicPlayer(frames=ENDING_FRAMES)
        self._cinematic.start()
        self._cinematic_kind = "ending"
        self._state = GameState.ENDING

    def _end_cinematic(self) -> None:
        was_intro = self._cinematic_kind == "intro"
        self._cinematic = None
        self._cinematic_kind = ""
        if was_intro and self._meta is not None:
            settings_module.mark_intro_seen(self._meta)
        # After the ending we still send the player to game-over for naming.
        if self._state is GameState.ENDING and self._world is not None:
            if self._world.player.crash_cause is None:
                self._world.player.crash_cause = "TRUE ENDING"
            self._state = GameState.GAME_OVER
        else:
            self._state = GameState.MENU

    def _handle_cinematic_key(self, event: pygame.event.Event) -> None:
        if self._cinematic is None:
            self._end_cinematic()
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._cinematic.skip()
            if self._cinematic.finished:
                self._end_cinematic()
        elif event.key == pygame.K_ESCAPE:
            self._cinematic.skip_all()
            self._end_cinematic()

    # ----- Codex -----

    def _open_codex(self) -> None:
        self._codex_index = 0
        self._state = GameState.CODEX

    def _codex_view(self) -> tuple[list[tuple[str, str, bool]], int, str | None]:
        unlocked = self._lore_repo.unlocked_keys() if self._lore_repo else set()
        rows = [(entry.key, entry.title, entry.key in unlocked) for entry in LORE_CATALOG]
        idx = max(0, min(self._codex_index, len(rows) - 1))
        body: str | None = None
        if rows and rows[idx][2]:
            body = LORE_CATALOG[idx].body
        return rows, idx, body

    def _handle_codex_key(self, event: pygame.event.Event) -> None:
        n = len(LORE_CATALOG)
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._state = GameState.MENU
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._codex_index = (self._codex_index - 1) % n
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._codex_index = (self._codex_index + 1) % n

    # ----- Stack-trace interstitial -----

    def _open_stack_trace(self) -> None:
        # 2 deterministic-but-varied lines: one [KERNEL] line + one rotating voice.
        idx = self._rng.randrange(len(STACK_TRACE_LINES))
        primary = STACK_TRACE_LINES[idx]
        secondary = STACK_TRACE_LINES[(idx + 1) % len(STACK_TRACE_LINES)]
        self._stack_trace_lines = [primary, secondary]
        self._state = GameState.STACK_TRACE

    def _handle_stack_trace_key(self, event: pygame.event.Event) -> None:
        if event.key in (
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_SPACE,
            pygame.K_ESCAPE,
        ):
            assert self._world is not None
            # Continue into the patch picker (depth >= 2 only).
            if self._world.player.depth_reached >= 2:
                self._open_patch_picker()
            else:
                self._state = GameState.PLAYING

    # ----- Phase 8 — Bestiary & Inspect -----

    def _bestiary_rows(
        self,
    ) -> list[tuple[str, str, int, int, int, str, str, str]]:
        """Compose ``render_bestiary`` rows from the IntelRepository + registry."""
        from kernelquest.entities.malware_registry import SPECIES

        if self._intel_repo is None:
            return []
        intel_by_key = {row.species_key: row for row in self._intel_repo.all()}
        rows: list[tuple[str, str, int, int, int, str, str, str]] = []
        for sp in SPECIES:
            data = intel_by_key.get(sp.key)
            tier = data.intel_level if data is not None else 0
            kills = data.kills if data is not None else 0
            dmg = data.damage_dealt_to if data is not None else 0
            weakness = self._weakness_label(sp)
            rows.append(
                (
                    sp.key,
                    sp.label,
                    tier,
                    kills,
                    dmg,
                    sp.archetype.value,
                    weakness,
                    sp.lore_blurb,
                )
            )
        return rows

    @staticmethod
    def _weakness_label(species: object) -> str:
        # Cheapest weakness: pick the highest resistance-multiplier > 1.0 type.
        weakest = ""
        best = 1.0
        for kind, mult in getattr(species, "resistances", {}).items():
            if mult > best:
                best = mult
                weakest = f"{kind.value} (×{mult:g})"
        if not weakest:
            cp = getattr(species, "counter_program", "")
            if cp:
                weakest = f"counter: {cp}"
        return weakest or "—"

    def _handle_bestiary_key(self, event: pygame.event.Event) -> None:
        rows = self._bestiary_rows()
        if not rows:
            self._state = GameState.PLAYING
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_b):
            # Back to where we came from — PLAYING if we have a world.
            self._state = GameState.PLAYING if self._world is not None else GameState.MENU
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._bestiary_scroll = (self._bestiary_scroll - 1) % len(rows)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._bestiary_scroll = (self._bestiary_scroll + 1) % len(rows)

    def _enter_inspect_mode(self) -> None:
        if self._world is None:
            return
        targets = self._inspectable_enemies()
        if not targets:
            self._console.info("No visible processes to inspect.")
            return
        self._inspect_index = 0
        self._track_lesson("inspect_opened")
        self._state = GameState.INSPECT

    def _inspectable_enemies(self) -> list[Malware]:
        if self._world is None:
            return []
        return [
            e
            for e in self._world.enemies
            if e.is_alive and e.visible_to_player and e.position in self._world.visible
        ]

    def _handle_inspect_key(self, event: pygame.event.Event) -> None:
        targets = self._inspectable_enemies()
        if not targets:
            self._state = GameState.PLAYING
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_BACKSPACE):
            self._state = GameState.PLAYING
        elif event.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_d):
            self._inspect_index = (self._inspect_index + 1) % len(targets)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._inspect_index = (self._inspect_index - 1) % len(targets)

    def _render_inspect_overlay(self, ui: UIManager) -> None:
        targets = self._inspectable_enemies()
        if not targets:
            return
        self._inspect_index = self._inspect_index % len(targets)
        enemy = targets[self._inspect_index]
        species = maybe_get_species(enemy.species_key)
        intel = (
            self._intel_repo.get(enemy.species_key)
            if self._intel_repo is not None and enemy.species_key
            else None
        )
        tier = intel.intel_level if intel is not None else 0
        kills = intel.kills if intel is not None else 0
        dmg = intel.damage_dealt_to if intel is not None else 0
        weakness = self._weakness_label(species) if species is not None else "—"
        ex, ey = enemy.position
        screen_pos = self._viewport.to_screen(ex, ey)
        anchor = (screen_pos[0] + 24, screen_pos[1] - 16)
        ui.render_inspect_overlay(
            anchor,
            label=enemy.name,
            tier=tier,
            kills=kills,
            damage_dealt=dmg,
            weakness=weakness,
            affixes=enemy.affixes.badges(),
        )

    # ------------------------------------------------------------------
    # Phase 11 — Distros, Milestone result, Vendor, Run summary
    # ------------------------------------------------------------------

    _distro_select_for_daily: bool = False

    def _open_distro_select(self, *, daily: bool) -> None:
        """Show the Distro picker before launching a fresh run."""
        self._distro_select_for_daily = daily
        # Default to the most recently unlocked distro.
        unlocked = self._distros_repo.unlocked_keys() if self._distros_repo else {DISTROS[0].key}
        for i, d in enumerate(DISTROS):
            if d.key in unlocked:
                self._distro_index = i
        self._state = GameState.DISTRO_SELECT

    def _distro_rows(self) -> list[dict[str, object]]:
        from kernelquest.ui.i18n import t

        unlocked = self._distros_repo.unlocked_keys() if self._distros_repo else {DISTROS[0].key}
        rows: list[dict[str, object]] = []
        for d in DISTROS:
            # i18n keys use the distro key; fall back to the static catalog text.
            name = t(f"distro.{d.key}.name")
            if name == f"distro.{d.key}.name":
                name = d.name
            description = t(f"distro.{d.key}.desc")
            if description == f"distro.{d.key}.desc":
                description = d.description
            signature = t(f"distro.{d.key}.signature")
            if signature == f"distro.{d.key}.signature":
                signature = d.signature
            unlock_hint = t(f"distro.{d.key}.unlock")
            if unlock_hint == f"distro.{d.key}.unlock":
                unlock_hint = d.unlock_hint
            rows.append(
                {
                    "key": d.key,
                    "name": name,
                    "description": description,
                    "signature": signature,
                    "unlock_hint": unlock_hint,
                    "unlocked": d.key in unlocked,
                    "bonus_ram": d.bonus_ram,
                    "bonus_cycles": d.bonus_cycles,
                    "starter_programs": list(d.starter_program_keys),
                }
            )
        return rows

    def _handle_distro_select_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._state = GameState.MENU
            return
        if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
            self._distro_index = (self._distro_index - 1) % len(DISTROS)
        elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
            self._distro_index = (self._distro_index + 1) % len(DISTROS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            chosen = DISTROS[self._distro_index]
            unlocked = (
                self._distros_repo.unlocked_keys() if self._distros_repo else {DISTROS[0].key}
            )
            if chosen.key not in unlocked:
                self._console.warn(f"{chosen.name} locked — clear earlier distro first")
                return
            self._start_new_run(daily=self._distro_select_for_daily, distro_key=chosen.key)

    # ----- milestone result screen -----

    def _handle_milestone_result_key(self, event: pygame.event.Event) -> None:
        panel = self._milestone_result_panel
        is_boss = bool(panel.get("boss"))
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._proceed_after_milestone()
        elif event.key in (pygame.K_v,) and not is_boss:
            self._open_vendor()
        elif event.key in (pygame.K_s,) and not is_boss:
            self._skip_current_milestone()
        elif event.key == pygame.K_ESCAPE:
            self._proceed_after_milestone()

    def _proceed_after_milestone(self) -> None:
        """Advance the run pointer; either generate next sector or finish run."""
        assert self._run_progress is not None
        self._run_progress.advance()
        if self._run_progress.is_run_complete:
            self._finish_run(success=True)
            return
        # ROADMAP 11.3 — open the Vendor after every played milestone.
        self._open_vendor()

    def _skip_current_milestone(self) -> None:
        """Mark the just-played milestone as skipped instead and grant a tag."""
        assert self._run_progress is not None
        # We've already recorded a clear; convert the most recent record.
        if self._run_progress.records:
            rec = self._run_progress.records[-1]
            rec.was_skipped = True
            rec.was_cleared = False
        # Award a random skip tag.
        tag = self._rng.choice(SKIP_TAG_CATALOG)
        self._run_progress.grant_skip_tag(tag.key)
        self._apply_skip_tag(tag)
        self._console.info(f"skipped milestone, granted: {tag.label}")
        self._milestone_result_panel["skip_tag"] = tag.label
        # Skipped milestone forfeits its score window — no vendor.
        self._run_progress.advance()
        if self._run_progress.is_run_complete:
            self._finish_run(success=True)
            return
        self._generate_next_sector()
        self._state = GameState.PLAYING

    def _apply_skip_tag(self, tag: SkipTag) -> None:
        """Translate a tag's ``effect_type`` into a deferred engine flag."""
        if tag.effect_type == "free_vendor":
            self._vendor_free = True
        elif tag.effect_type == "double_bits":
            self._double_bits_pending = True
        elif tag.effect_type == "extra_daemon_slot":
            self._extra_daemon_slot_pending = True
        elif tag.effect_type == "bonus_score":
            self._bonus_score_pending += tag.magnitude

    # ----- vendor (in-run shop) -----

    def _open_vendor(self) -> None:
        self._vendor_stock = self._build_vendor_stock()
        self._vendor_index = 0
        self._vendor_message = None
        self._state = GameState.VENDOR

    def _build_vendor_stock(self) -> list[dict[str, object]]:
        """Compose 5 stock entries: 2 programs, 2 daemons, 1 patch — distro-biased."""
        from kernelquest.entities.daemon import CATALOG as DAEMONS

        stock: list[dict[str, object]] = []
        # Programs
        progs = list(PROGRAM_CATALOG)
        self._rng.shuffle(progs)
        for prog in progs[:2]:
            stock.append(
                {
                    "kind": "program",
                    "key": prog.key,
                    "label": prog.label,
                    "description": prog.description,
                    "cost": 5,
                }
            )
        # Daemons (filter by distro tag bias when possible).
        daemons = list(DAEMONS)
        bias = self._distro.vendor_tag_bias if self._distro is not None else ()
        if bias:
            preferred = [d for d in daemons if any(t in d.description.lower() for t in bias)]
            daemons = preferred + [d for d in daemons if d not in preferred]
        self._rng.shuffle(daemons)
        for dae in daemons[:2]:
            stock.append(
                {
                    "kind": "daemon",
                    "key": dae.key,
                    "label": dae.label,
                    "description": dae.description,
                    "cost": 8,
                }
            )
        # One patch.
        patch = self._rng.choice(list(PATCH_CATALOG))
        stock.append(
            {
                "kind": "patch",
                "key": patch.key,
                "label": patch.label,
                "description": patch.description,
                "cost": 6,
            }
        )
        # Reroll + leave (special entries).
        stock.append(
            {
                "kind": "reroll",
                "key": "reroll",
                "label": "Reroll",
                "description": "",
                "cost": 3,
            }
        )
        stock.append(
            {
                "kind": "leave",
                "key": "leave",
                "label": "Leave",
                "description": "",
                "cost": 0,
            }
        )
        return stock

    def _handle_vendor_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE,):
            self._exit_vendor()
            return
        if not self._vendor_stock:
            self._exit_vendor()
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._vendor_index = (self._vendor_index - 1) % len(self._vendor_stock)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._vendor_index = (self._vendor_index + 1) % len(self._vendor_stock)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._vendor_buy_selected()

    def _vendor_buy_selected(self) -> None:
        item = self._vendor_stock[self._vendor_index]
        kind = str(item["kind"])
        if kind == "leave":
            self._exit_vendor()
            return
        if kind == "reroll":
            cost = 0 if self._vendor_free else 3
            if not self._spend_bits(cost):
                self._vendor_message = "not enough bits"
                return
            self._vendor_stock = self._build_vendor_stock()
            self._vendor_index = 0
            self._vendor_message = "rerolled"
            return
        cost = 0 if self._vendor_free else cast(int, item["cost"])
        if not self._spend_bits(cost):
            self._vendor_message = "not enough bits"
            return
        self._vendor_apply_purchase(item)
        self._vendor_message = f"{item['label']} purchased"
        # Free-vendor tag is a single-vendor effect (every item free).
        # Remove the bought entry so the player can't reuse it.
        self._vendor_stock = [
            s for i, s in enumerate(self._vendor_stock) if i != self._vendor_index
        ]
        self._vendor_index = max(0, self._vendor_index - 1)

    def _spend_bits(self, cost: int) -> bool:
        if cost <= 0:
            return True
        if self._meta is None:
            return False
        current = self._meta.get_int(_KEY_BITS, 0)
        if current < cost:
            return False
        self._meta.set_int(_KEY_BITS, current - cost)
        return True

    def _vendor_apply_purchase(self, item: dict[str, object]) -> None:
        if self._world is None:
            return
        player = self._world.player
        kind = str(item["kind"])
        key = str(item["key"])
        if kind == "program":
            try:
                prog = get_program(key)
            except KeyError:
                return
            player.programs.append(ProgramSlot(program=prog, charges=prog.max_charges))
        elif kind == "daemon":
            try:
                player.daemons.append(get_daemon(key))
            except KeyError:
                return
        elif kind == "patch":
            for p in PATCH_CATALOG:
                if p.key == key:
                    self._patches.add(p)
                    break

    def _exit_vendor(self) -> None:
        # Reset the free-vendor effect after one visit.
        self._vendor_free = False
        self._generate_next_sector()
        self._state = GameState.PLAYING

    # ----- run completion (success path) -----

    def _finish_run(self, *, success: bool) -> None:
        """Phase 11 — close out the run and route to the summary screen."""
        if self._world is None:
            return
        self._run_was_successful = success
        player = self._world.player
        bits_to_meta = 0
        unlocked_distro: str | None = None
        if success:
            self._console.kernel("[init] uptime certified — kernel stable.")
            # Carry-over to meta `bits` only on successful run (per 11.3).
            bits_to_meta = max(50, player.score // 5)
            if self._meta is not None:
                current = self._meta.get_int(_KEY_BITS, 0)
                self._meta.set_int(_KEY_BITS, current + bits_to_meta)
            # Sequential distro unlock.
            if self._distro is not None and self._distros_repo is not None:
                nxt = next_in_chain(self._distro.key)
                if nxt is not None and self._distros_repo.unlock(nxt.key):
                    unlocked_distro = nxt.name
        self._run_summary_payload = {
            "success": success,
            "distro": self._distro.name if self._distro is not None else "?",
            "releases_cleared": (
                self._run_progress.releases_cleared if self._run_progress is not None else 0
            ),
            "bits_to_meta": bits_to_meta,
            "unlocked_distro": unlocked_distro or "",
            "score": player.score,
        }
        # Persist run as successful.
        self._save_successful_run()
        self._state = GameState.RUN_SUMMARY

    def _save_successful_run(self) -> None:
        if self._scores is None or self._runs is None or self._world is None:
            return
        player = self._world.player
        name = self._name_buffer.strip() or "anon_process"
        self._scores.insert(
            player_name=name,
            depth_reached=player.depth_reached,
            total_score=player.score,
            crash_cause="run_complete",
        )
        run_id = 0
        if self._run_meta is not None:
            run_id = self._runs.insert(
                player_name=name,
                seed=self._run_meta.seed,
                depth_reached=player.depth_reached,
                total_score=player.score,
                crash_cause="run_complete",
                duration_ms=self._run_meta.elapsed_ms(),
                distro_key=self._distro.key if self._distro is not None else None,
                is_successful=True,
            )
        self._persist_phase11_artifacts(run_id)

    def _persist_phase11_artifacts(self, run_id: int) -> None:
        if self._run_progress is None:
            return
        if self._milestones_repo is not None and run_id > 0:
            rows: list[tuple[int, int, str, int, int, bool, bool]] = [
                (
                    rec.release_index,
                    rec.milestone_index,
                    rec.kind.value,
                    rec.target_score,
                    rec.reached_score,
                    rec.was_skipped,
                    rec.was_cleared,
                )
                for rec in self._run_progress.records
            ]
            self._milestones_repo.insert_many(run_id, rows)
        if self._skip_tags_repo is not None and run_id > 0:
            for tag in self._run_progress.skip_tags:
                self._skip_tags_repo.insert(run_id, tag.key, tag.used)

    def _handle_run_summary_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_SPACE):
            self._run_progress = None
            self._distro = None
            self._world = None
            self._state = GameState.MENU


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
