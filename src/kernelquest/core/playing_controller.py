"""Gameplay (PLAYING / GAME_OVER) input + turn loop.

The :class:`PlayingController` owns the per-turn logic that mutates the
world: handling player keys, attacks, movement, descent, enemy turns, and
the game-over save flow. It also offers the entry point used by
:class:`MenuController` to spin up a fresh run.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

from kernelquest.core.config import (
    BAD_SECTOR_DAMAGE,
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
    WINDOW_WIDTH,
)
from kernelquest.core.state import GameState
from kernelquest.data.upgrades_catalog import CATALOG, PlayerBonus
from kernelquest.entities.malware import Malware
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import player_attack
from kernelquest.systems.inventory import pickup_item_at, use_cache_slot
from kernelquest.ui import theme
from kernelquest.ui.viewport import Viewport
from kernelquest.world.generator import generate_world
from kernelquest.world.tile import TileType

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine

log = logging.getLogger(__name__)

_KEY_BITS = "meta.bits"


@dataclass
class RunMeta:
    """Per-run bookkeeping (seed, start time)."""

    seed: int
    started_at: float = field(default_factory=time.monotonic)

    def elapsed_ms(self) -> int:
        return max(0, int((time.monotonic() - self.started_at) * 1000))


class PlayingController:
    """Owns the gameplay turn loop and game-over flow."""

    def __init__(self, engine: GameEngine) -> None:
        self._engine = engine

    # ----- key handlers -----

    def handle_playing_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        assert eng._world is not None
        world = eng._world
        player = world.player

        if event.key == pygame.K_ESCAPE:
            if player.crash_cause is None:
                player.crash_cause = "Manuel kapatma"
            self._enter_game_over()
            return

        if event.key == pygame.K_SPACE:
            self._end_player_turn()
            return

        slot_index = _key_to_slot(event.key)
        if slot_index is not None:
            message = use_cache_slot(world, slot_index)
            if message is not None:
                eng._console.info(message)
                eng._play_sfx("pickup")
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

    def handle_game_over_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._save_run()
            self._reset_to_menu()
            return
        if event.key == pygame.K_BACKSPACE:
            eng._name_buffer = eng._name_buffer[:-1]
            return
        if event.key == pygame.K_ESCAPE:
            self._reset_to_menu()
            return
        char = event.unicode
        if char and char.isprintable() and len(eng._name_buffer) < PLAYER_NAME_MAX_LENGTH:
            eng._name_buffer += char

    # ----- run lifecycle -----

    def start_new_run(self) -> None:
        eng = self._engine
        seed = eng._seed_override if eng._seed_override is not None else random.randrange(2**31)
        eng._rng = random.Random(seed)
        eng._run_meta = RunMeta(seed=seed)

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

        eng._world = generate_world(player=player, depth=1, rng=eng._rng)
        eng._world.recompute_fov()
        eng._viewport = Viewport.centered(
            WINDOW_WIDTH, WINDOW_HEIGHT, eng._world.grid.width, eng._world.grid.height
        )
        eng._name_buffer = ""
        eng._console.clear()
        eng._console.info(
            f"Process 0x{player.depth_reached:02X} sektöründe başlatıldı (seed={seed})"
        )
        eng._particles.clear()
        eng._state = GameState.PLAYING

    def _compute_bonus(self) -> PlayerBonus:
        bonus = PlayerBonus()
        upgrades = self._engine._upgrades
        if upgrades is None:
            return bonus
        levels = upgrades.all_levels()
        for upgrade in CATALOG:
            level = levels.get(upgrade.key, 0)
            if level > 0:
                upgrade.apply(level, bonus)
        return bonus

    # ----- turn helpers -----

    def _player_attacks(self, enemy: Malware) -> None:
        eng = self._engine
        assert eng._world is not None
        player = eng._world.player
        if not player.spend_cycle():
            return
        damage = max(1, int(round(player.base_damage * eng._settings.player_damage_multiplier)))
        result = player_attack(eng._world, enemy, eng._rng, damage=damage)
        eng._console.info(result.log_message)
        eng._play_sfx("attack")
        ex, ey = enemy.position
        eng._particles.burst(
            (ex + 0.5, ey + 0.5),
            theme.NEON_MAGENTA if result.killed else theme.NEON_AMBER,
            eng._rng,
            count=14 if result.killed else 6,
        )
        if result.killed:
            eng._shake.punch(SCREEN_SHAKE_KILL_INTENSITY)
            eng._world.remove_dead_enemies()
            eng._play_sfx("explode")
        eng._world.recompute_fov()
        self._after_player_action()

    def _on_player_moved(self) -> None:
        eng = self._engine
        assert eng._world is not None
        player = eng._world.player
        player.score += SCORE_PER_MOVE
        eng._play_sfx("move")
        eng._world.recompute_fov()

        message = pickup_item_at(eng._world, player.position)
        if message is not None:
            eng._console.info(message)
            eng._play_sfx("pickup")
            eng._particles.burst(
                (player.position[0] + 0.5, player.position[1] + 0.5),
                theme.NEON_GREEN,
                eng._rng,
                count=8,
                speed=1.6,
            )

        tile = eng._world.grid.get(*player.position)
        if tile is TileType.BAD_SECTOR:
            player.take_damage(BAD_SECTOR_DAMAGE, source="Bad Sector")
            eng._console.warn(f"Bad Sector {BAD_SECTOR_DAMAGE} RAM yaktı")
            eng._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
        elif tile is TileType.EXIT:
            self._descend()
            return

        if not player.is_alive:
            self._enter_game_over()
            return

        self._after_player_action()

    def _after_player_action(self) -> None:
        eng = self._engine
        assert eng._world is not None
        player = eng._world.player
        if not player.is_alive:
            self._enter_game_over()
            return
        if player.cpu_cycles == 0:
            self._end_player_turn()

    def _end_player_turn(self) -> None:
        eng = self._engine
        assert eng._world is not None
        starting_ram = eng._world.player.ram
        for message in run_enemy_turn(
            eng._world, eng._rng, damage_multiplier=eng._settings.enemy_damage_multiplier
        ):
            eng._console.warn(message)

        if eng._world.player.ram < starting_ram:
            eng._shake.punch(SCREEN_SHAKE_DAMAGE_INTENSITY)
            eng._play_sfx("attack")
        if not eng._world.player.is_alive:
            self._enter_game_over()
            return
        eng._world.player.tick_status_effects()
        eng._world.player.end_turn()
        eng._world.recompute_fov()

    def _descend(self) -> None:
        eng = self._engine
        assert eng._world is not None
        player = eng._world.player
        player.depth_reached += 1
        player.score += SCORE_PER_DESCENT
        eng._console.info(f"Sektör 0x{player.depth_reached:02X}'ya iniliyor")
        eng._play_sfx("descend")
        eng._world = generate_world(
            player=player,
            depth=player.depth_reached,
            rng=eng._rng,
        )
        eng._world.recompute_fov()
        eng._particles.clear()
        player.end_turn()

    def _enter_game_over(self) -> None:
        eng = self._engine
        assert eng._world is not None
        if eng._world.player.crash_cause is None:
            eng._world.player.crash_cause = "RAM tükendi"
        eng._console.crit(f"SYSTEM CRASH - {eng._world.player.crash_cause}")
        eng._play_sfx("crash")
        eng._state = GameState.GAME_OVER

    def _save_run(self) -> None:
        eng = self._engine
        if (
            eng._scores is None or eng._runs is None or eng._meta is None or eng._world is None
        ):  # pragma: no cover
            return
        player = eng._world.player
        name = eng._name_buffer.strip() or "anonim_process"
        eng._scores.insert(
            player_name=name,
            depth_reached=player.depth_reached,
            total_score=player.score,
            crash_cause=player.crash_cause or "unknown",
        )
        if eng._run_meta is not None:
            eng._runs.insert(
                player_name=name,
                seed=eng._run_meta.seed,
                depth_reached=player.depth_reached,
                total_score=player.score,
                crash_cause=player.crash_cause or "unknown",
                duration_ms=eng._run_meta.elapsed_ms(),
            )
        bits_earned = player.score // 10 + player.depth_reached * 2
        current = eng._meta.get_int(_KEY_BITS, 0)
        eng._meta.set_int(_KEY_BITS, current + bits_earned)
        log.info(
            "Saved run: name=%s depth=%d score=%d cause=%s bits=+%d",
            name,
            player.depth_reached,
            player.score,
            player.crash_cause,
            bits_earned,
        )

    def _reset_to_menu(self) -> None:
        eng = self._engine
        eng._name_buffer = ""
        eng._state = GameState.MENU


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
