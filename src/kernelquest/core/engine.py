"""Game engine: pygame init, main loop, top-level state machine."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

from kernelquest.core.config import (
    BAD_SECTOR_DAMAGE,
    DATABASE_FILENAME,
    FPS,
    PLAYER_NAME_MAX_LENGTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from kernelquest.core.state import GameState
from kernelquest.data.database import Database
from kernelquest.data.repositories import ScoreRepository
from kernelquest.entities.player import Player
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.viewport import Viewport
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType

log = logging.getLogger(__name__)


class GameEngine:
    """Owns the pygame window and orchestrates state transitions.

    Lifetime: instantiate, call `run()`. The constructor opens the database
    and prepares the initial state; pygame init happens inside `run()` so
    headless tests can construct an engine without a display server.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self._db_path = database_path or Path(DATABASE_FILENAME)
        self._database: Database | None = None
        self._scores: ScoreRepository | None = None

        self._state: GameState = GameState.MENU
        self._grid: MemoryGrid = MemoryGrid.static_default()
        self._player: Player = Player()
        self._viewport: Viewport = Viewport.centered(
            WINDOW_WIDTH, WINDOW_HEIGHT, self._grid.width, self._grid.height
        )

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
                dt = clock.tick(FPS) / 1000.0
                self._handle_events()
                self._update(dt)
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
        if event.key == pygame.K_ESCAPE:
            # Treat quitting mid-run as a manual shutdown; record the score.
            if self._player.crash_cause is None:
                self._player.crash_cause = "Manual shutdown"
            self._enter_game_over()
            return

        if event.key in (pygame.K_SPACE,):
            self._player.end_turn()
            return

        delta = _key_to_delta(event.key)
        if delta is None:
            return

        moved = self._player.try_move(*delta, self._grid)
        if moved:
            self._on_player_moved()
        if self._player.cpu_cycles == 0:
            # Auto-refill cycles each turn (Phase 1: no enemies act yet).
            self._player.end_turn()

    def _handle_game_over_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._save_run()
            self._reset_to_menu()
            return
        if event.key == pygame.K_BACKSPACE:
            self._name_buffer = self._name_buffer[:-1]
            return
        if event.key == pygame.K_ESCAPE:
            # Skip saving and bail to the menu.
            self._reset_to_menu()
            return
        char = event.unicode
        if char and char.isprintable() and len(self._name_buffer) < PLAYER_NAME_MAX_LENGTH:
            self._name_buffer += char

    def _update(self, dt: float) -> None:
        # Phase 1 has no time-based simulation; reserved for Phase 2.
        del dt

    def _render(self, ui: UIManager) -> None:
        if self._state is GameState.MENU:
            ui.render_menu()
        elif self._state is GameState.PLAYING:
            ui.clear()
            ui.render_grid(self._grid, self._viewport)
            ui.render_player(self._player, self._viewport)
            ui.render_hud(self._player, sector=self._player.depth_reached)
        elif self._state is GameState.GAME_OVER:
            ui.render_game_over(self._player, self._name_buffer)
        ui.present()

    # ----- transitions -----

    def _start_new_run(self) -> None:
        self._grid = MemoryGrid.static_default()
        self._player = Player()
        self._name_buffer = ""
        self._state = GameState.PLAYING

    def _on_player_moved(self) -> None:
        self._player.score += 1  # placeholder scoring
        tile = self._grid.get(*self._player.position)
        if tile is TileType.BAD_SECTOR:
            self._player.take_damage(BAD_SECTOR_DAMAGE, source="Bad Sector")
        if not self._player.is_alive:
            self._enter_game_over()

    def _enter_game_over(self) -> None:
        if self._player.crash_cause is None:
            self._player.crash_cause = "Out of RAM"
        self._state = GameState.GAME_OVER

    def _save_run(self) -> None:
        if self._scores is None:  # pragma: no cover - run() always populates this
            return
        name = self._name_buffer.strip() or "anon_process"
        self._scores.insert(
            player_name=name,
            depth_reached=self._player.depth_reached,
            total_score=self._player.score,
            crash_cause=self._player.crash_cause or "unknown",
        )
        log.info(
            "Saved run: name=%s depth=%d score=%d cause=%s",
            name,
            self._player.depth_reached,
            self._player.score,
            self._player.crash_cause,
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
