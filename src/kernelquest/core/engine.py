"""Game engine: pygame init, main loop, top-level state machine."""

from __future__ import annotations

import logging
import random
from pathlib import Path

import pygame

from kernelquest.core.config import (
    BAD_SECTOR_DAMAGE,
    DATABASE_FILENAME,
    FPS,
    PLAYER_NAME_MAX_LENGTH,
    SCORE_PER_DESCENT,
    SCORE_PER_MOVE,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from kernelquest.core.state import GameState
from kernelquest.data.database import Database
from kernelquest.data.repositories import ScoreRepository
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import player_attack
from kernelquest.systems.inventory import pickup_item_at, use_cache_slot
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.viewport import Viewport
from kernelquest.world.generator import generate_world
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

log = logging.getLogger(__name__)


class GameEngine:
    """Owns the pygame window and orchestrates state transitions."""

    def __init__(self, database_path: Path | None = None, seed: int | None = None) -> None:
        self._db_path = database_path or Path(DATABASE_FILENAME)
        self._database: Database | None = None
        self._scores: ScoreRepository | None = None

        self._state: GameState = GameState.MENU
        self._seed = seed
        self._rng: random.Random = random.Random(seed)
        self._world: World | None = None
        self._viewport: Viewport = Viewport.centered(WINDOW_WIDTH, WINDOW_HEIGHT, 20, 20)
        self._name_buffer: str = ""

    # ----- public entry point -----

    def run(self) -> None:
        log.info("Booting GameEngine (db=%s)", self._db_path)
        self._database = Database.open(self._db_path)
        self._scores = ScoreRepository(self._database)

        pygame.init()
        try:
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.display.set_caption(WINDOW_TITLE)
            ui = UIManager(screen)
            clock = pygame.time.Clock()

            while self._state is not GameState.QUIT:
                clock.tick(FPS)
                self._handle_events()
                self._render(ui)
        finally:
            pygame.quit()
            if self._database is not None:
                self._database.close()
            log.info("GameEngine shutdown complete.")

    # ----- per-frame -----

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

    def _handle_menu_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._state = GameState.QUIT
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._start_new_run()

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

        # Use cache slot via number keys 1-9.
        slot_index = _key_to_slot(event.key)
        if slot_index is not None:
            message = use_cache_slot(world, slot_index)
            if message is not None:
                log.info("[INV] %s", message)
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
            ui.render_menu()
        elif self._state is GameState.PLAYING and self._world is not None:
            ui.clear()
            ui.render_world(self._world, self._viewport)
            ui.render_hud(self._world.player, sector=self._world.player.depth_reached)
        elif self._state is GameState.GAME_OVER and self._world is not None:
            ui.render_game_over(self._world.player, self._name_buffer)
        ui.present()

    # ----- transitions -----

    def _start_new_run(self) -> None:
        self._rng = random.Random(self._seed)
        player = Player()
        self._world = generate_world(player=player, depth=1, rng=self._rng)
        self._viewport = Viewport.centered(
            WINDOW_WIDTH, WINDOW_HEIGHT, self._world.grid.width, self._world.grid.height
        )
        self._name_buffer = ""
        self._state = GameState.PLAYING

    def _player_attacks(self, enemy: object) -> None:
        assert self._world is not None
        # Enemy is a Malware here; type narrowed by caller.
        from kernelquest.entities.malware import Malware  # local to avoid cycles

        assert isinstance(enemy, Malware)
        player = self._world.player
        if not player.spend_cycle():
            return
        result = player_attack(self._world, enemy, self._rng)
        log.info("[CBT] %s", result.log_message)
        if result.killed:
            self._world.remove_dead_enemies()
        self._after_player_action()

    def _on_player_moved(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.score += SCORE_PER_MOVE

        # Pickup any item underfoot.
        message = pickup_item_at(self._world, player.position)
        if message is not None:
            log.info("[INV] %s", message)

        tile = self._world.grid.get(*player.position)
        if tile is TileType.BAD_SECTOR:
            player.take_damage(BAD_SECTOR_DAMAGE, source="Bad Sector")
            log.info("[ENV] Bad Sector burned %d RAM", BAD_SECTOR_DAMAGE)
        elif tile is TileType.EXIT:
            self._descend()
            return

        if not player.is_alive:
            self._enter_game_over()
            return

        self._after_player_action()

    def _after_player_action(self) -> None:
        """Common post-action hook: run AI when cycles run out, check death."""
        assert self._world is not None
        player = self._world.player
        if not player.is_alive:
            self._enter_game_over()
            return
        if player.cpu_cycles == 0:
            self._end_player_turn()

    def _end_player_turn(self) -> None:
        """Hand the turn to the enemies, then refill the player's cycles."""
        assert self._world is not None
        for message in run_enemy_turn(self._world, self._rng):
            log.info("[AI ] %s", message)
        if not self._world.player.is_alive:
            self._enter_game_over()
            return
        self._world.player.tick_status_effects()
        self._world.player.end_turn()

    def _descend(self) -> None:
        assert self._world is not None
        player = self._world.player
        player.depth_reached += 1
        player.score += SCORE_PER_DESCENT
        log.info("[SYS] Descending to sector 0x%02X", player.depth_reached)
        self._world = generate_world(
            player=player,
            depth=player.depth_reached,
            rng=self._rng,
        )
        player.end_turn()

    def _enter_game_over(self) -> None:
        assert self._world is not None
        if self._world.player.crash_cause is None:
            self._world.player.crash_cause = "Out of RAM"
        self._state = GameState.GAME_OVER

    def _save_run(self) -> None:
        if self._scores is None or self._world is None:  # pragma: no cover
            return
        player = self._world.player
        name = self._name_buffer.strip() or "anon_process"
        self._scores.insert(
            player_name=name,
            depth_reached=player.depth_reached,
            total_score=player.score,
            crash_cause=player.crash_cause or "unknown",
        )
        log.info(
            "Saved run: name=%s depth=%d score=%d cause=%s",
            name,
            player.depth_reached,
            player.score,
            player.crash_cause,
        )

    def _reset_to_menu(self) -> None:
        self._name_buffer = ""
        self._state = GameState.MENU


def _key_to_delta(key: int) -> tuple[int, int] | None:
    """Map a pygame key constant to a `(dx, dy)` step or `None`."""
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
    """Map number keys 1-9 to cache slots 0-8."""
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
