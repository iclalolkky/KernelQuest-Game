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
    MetaRepository,
    RunRepository,
    ScoreRepository,
    UpgradeRepository,
)
from kernelquest.data.upgrades_catalog import CATALOG, PlayerBonus
from kernelquest.entities.malware import Malware
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import player_attack
from kernelquest.systems.inventory import pickup_item_at, use_cache_slot
from kernelquest.ui import theme
from kernelquest.ui.console_log import ConsoleLog
from kernelquest.ui.fx import ParticleSystem, ScreenShake
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.sfx import SoundManager
from kernelquest.ui.viewport import Viewport
from kernelquest.world.generator import generate_world
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

log = logging.getLogger(__name__)

_KEY_BITS = "meta.bits"

_MENU_OPTIONS: tuple[str, ...] = (
    "New Run",
    "High Scores",
    "Stats",
    "Shop",
    "Settings",
    "Quit",
)


@dataclass
class _RunMeta:
    """Per-run bookkeeping (seed, start time)."""

    seed: int
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

        self._state: GameState = GameState.MENU
        self._seed_override = seed
        self._rng: random.Random = random.Random(seed)
        self._world: World | None = None
        self._viewport: Viewport = Viewport.centered(WINDOW_WIDTH, WINDOW_HEIGHT, 20, 20)
        self._name_buffer: str = ""

        self._console = ConsoleLog()
        self._shake = ScreenShake()
        self._particles = ParticleSystem()
        self._sfx: SoundManager | None = None

        self._settings: Settings = Settings()
        self._menu_index: int = 0
        self._shop_index: int = 0
        self._settings_index: int = 0
        self._shop_message: str | None = None
        self._run_meta: _RunMeta | None = None

    # ----- public entry point -----

    def run(self) -> None:
        log.info("Booting GameEngine (db=%s)", self._db_path)
        self._database = Database.open(self._db_path)
        self._scores = ScoreRepository(self._database)
        self._runs = RunRepository(self._database)
        self._meta = MetaRepository(self._database)
        self._upgrades = UpgradeRepository(self._database)
        self._settings = settings_module.load(self._meta)

        pygame.init()
        try:
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.display.set_caption(WINDOW_TITLE)
            ui = UIManager(screen)
            self._sfx = SoundManager()
            self._sfx.set_volume(self._settings.volume)
            self._sfx.start_music()
            clock = pygame.time.Clock()

            while self._state is not GameState.QUIT:
                clock.tick(FPS)
                self._handle_events()
                self._step_fx()
                self._render(ui)
        finally:
            if self._sfx is not None:
                self._sfx.stop_music()
            pygame.quit()
            if self._database is not None:
                self._database.close()
            log.info("GameEngine shutdown complete.")

    # ----- per-frame -----

    def _step_fx(self) -> None:
        self._shake.step()
        self._particles.step()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._state = GameState.QUIT
                return
            if event.type != pygame.KEYDOWN:
                continue

            if self._state is GameState.MENU:
                self._handle_menu_key(event)
            elif self._state is GameState.PLAYING:
                self._handle_playing_key(event)
            elif self._state is GameState.GAME_OVER:
                self._handle_game_over_key(event)
            elif self._state in (GameState.HIGH_SCORES, GameState.STATS):
                self._handle_back_key(event)
            elif self._state is GameState.SHOP:
                self._handle_shop_key(event)
            elif self._state is GameState.SETTINGS:
                self._handle_settings_key(event)

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
            self._start_new_run()
        elif choice == "High Scores":
            self._state = GameState.HIGH_SCORES
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
        if event.key in (pygame.K_UP, pygame.K_w):
            self._settings_index = (self._settings_index - 1) % 2
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._settings_index = (self._settings_index + 1) % 2
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._adjust_setting(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._adjust_setting(+1)

    def _adjust_setting(self, direction: int) -> None:
        if self._settings_index == 0:
            self._settings.adjust_volume(0.1 * direction)
            if self._sfx is not None:
                self._sfx.set_volume(self._settings.volume)
        else:
            # Cycle difficulty in either direction.
            self._settings.cycle_difficulty()

    def _handle_playing_key(self, event: pygame.event.Event) -> None:
        assert self._world is not None
        world = self._world
        player = world.player

        if event.key == pygame.K_ESCAPE:
            if player.crash_cause is None:
                player.crash_cause = "Manual shutdown"
            self._enter_game_over()
            return

        if event.key == pygame.K_SPACE:
            self._end_player_turn()
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
            ui.render_hud(
                self._world.player, sector=self._world.player.depth_reached, world=self._world
            )
            ui.render_console(self._console)
        elif self._state is GameState.GAME_OVER and self._world is not None:
            ui.render_game_over(self._world.player, self._name_buffer)
        elif self._state is GameState.HIGH_SCORES:
            ui.render_high_scores(self._fetch_high_scores())
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
        ui.present()

    # ----- transitions -----

    def _start_new_run(self) -> None:
        seed = self._seed_override if self._seed_override is not None else random.randrange(2**31)
        self._rng = random.Random(seed)
        self._run_meta = _RunMeta(seed=seed)

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

        self._world = generate_world(player=player, depth=1, rng=self._rng)
        self._world.recompute_fov()
        self._viewport = Viewport.centered(
            WINDOW_WIDTH, WINDOW_HEIGHT, self._world.grid.width, self._world.grid.height
        )
        self._name_buffer = ""
        self._console.clear()
        self._console.info(f"Process spawned in sector 0x{player.depth_reached:02X} (seed={seed})")
        self._particles.clear()
        self._state = GameState.PLAYING

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
        damage = max(1, int(round(player.base_damage * self._settings.player_damage_multiplier)))
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
            self._shake.punch(SCREEN_SHAKE_KILL_INTENSITY)
            self._world.remove_dead_enemies()
            self._play_sfx("explode")
        self._world.recompute_fov()
        self._after_player_action()

    def _on_player_moved(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.score += SCORE_PER_MOVE
        self._play_sfx("move")
        self._world.recompute_fov()

        message = pickup_item_at(self._world, player.position)
        if message is not None:
            self._console.info(message)
            self._play_sfx("pickup")
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
        elif tile is TileType.EXIT:
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
        for message in run_enemy_turn(
            self._world, self._rng, damage_multiplier=self._settings.enemy_damage_multiplier
        ):
            self._console.warn(message)

        if self._world.player.ram < starting_ram:
            self._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
            self._play_sfx("attack")
        if not self._world.player.is_alive:
            self._enter_game_over()
            return
        self._world.player.tick_status_effects()
        self._world.player.end_turn()
        self._world.recompute_fov()

    def _descend(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.depth_reached += 1
        player.score += SCORE_PER_DESCENT
        self._console.info(f"Descending to sector 0x{player.depth_reached:02X}")
        self._play_sfx("descend")
        self._world = generate_world(
            player=player,
            depth=player.depth_reached,
            rng=self._rng,
        )
        self._world.recompute_fov()
        self._particles.clear()
        player.end_turn()

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
        return [
            ("Volume", f"{int(round(self._settings.volume * 100))}%"),
            ("Difficulty", self._settings.difficulty.value),
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
        best = self._runs.best()
        best_tuple: tuple[str, int, int] | None = None
        if best is not None:
            best_tuple = (best.player_name, best.total_score, best.depth_reached)
        return (avg, deaths, best_tuple, len(runs))


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
