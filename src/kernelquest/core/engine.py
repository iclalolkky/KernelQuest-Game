"""Game engine: pygame init, main loop, top-level state machine."""

from __future__ import annotations

import logging
import random
from pathlib import Path

import pygame

from kernelquest.core import settings as settings_module
from kernelquest.core.config import (
    DATABASE_FILENAME,
    FPS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from kernelquest.core.menu_controller import MENU_OPTIONS, MenuController
from kernelquest.core.playing_controller import PlayingController, RunMeta
from kernelquest.core.settings import Settings
from kernelquest.core.state import GameState
from kernelquest.data.database import Database
from kernelquest.data.repositories import (
    MetaRepository,
    RunRepository,
    ScoreRepository,
    UpgradeRepository,
)
from kernelquest.ui.console_log import ConsoleLog
from kernelquest.ui.fx import ParticleSystem, ScreenShake
from kernelquest.ui.renderer import UIManager
from kernelquest.ui.sfx import SoundManager
from kernelquest.ui.viewport import Viewport
from kernelquest.world.world import World

log = logging.getLogger(__name__)


class GameEngine:
    """Owns the pygame window and orchestrates state transitions."""
    # Ana oyun motoru sınıfı, pygame penceresini ve durum geçişlerini yönetir.

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
        self._run_meta: RunMeta | None = None
        self._tutorial_page: int = 0
        self._menu = MenuController(self)
        self._playing = PlayingController(self)

    # ----- public entry point -----

    def run(self) -> None:
        # Oyunu başlatır ve ana döngüyü çalıştırır.
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
        # Kullanıcı girdilerini işler ve oyun durumuna göre yönlendirir.
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
            elif self._state is GameState.TUTORIAL:
                self._handle_tutorial_key(event)
            elif self._state is GameState.QUIT_CONFIRM:
                self._handle_quit_confirm_key(event)

    def _handle_menu_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_menu_key(event)

    def _handle_quit_confirm_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_quit_confirm_key(event)

    def _handle_back_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_back_key(event)

    def _handle_tutorial_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_tutorial_key(event)

    def _handle_shop_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_shop_key(event)

    def _handle_settings_key(self, event: pygame.event.Event) -> None:
        self._menu.handle_settings_key(event)

    def _handle_playing_key(self, event: pygame.event.Event) -> None:
        self._playing.handle_playing_key(event)

    def _handle_game_over_key(self, event: pygame.event.Event) -> None:
        self._playing.handle_game_over_key(event)

    def _start_new_run(self) -> None:
        self._playing.start_new_run()

    def _play_sfx(self, name: str) -> None:
        if self._sfx is not None:
            self._sfx.play(name)

    def _render(self, ui: UIManager) -> None:
        # Geçerli oyun durumuna göre ekranı çizer.
        if self._state is GameState.MENU:
            ui.render_menu(list(MENU_OPTIONS), self._menu_index)
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
            ui.render_high_scores(self._menu.fetch_high_scores())
        elif self._state is GameState.STATS:
            avg, deaths, best, count = self._menu.fetch_stats()
            ui.render_stats(avg, deaths, best, count)
        elif self._state is GameState.SHOP:
            ui.render_shop(
                self._menu.fetch_bits(),
                self._menu.shop_rows(),
                self._shop_index,
                self._shop_message,
            )
        elif self._state is GameState.SETTINGS:
            ui.render_settings(self._menu.settings_rows(), self._settings_index)
        elif self._state is GameState.TUTORIAL:
            ui.render_tutorial(self._tutorial_page)
        elif self._state is GameState.QUIT_CONFIRM:
            ui.render_menu(list(MENU_OPTIONS), self._menu_index)
            ui.render_quit_confirm()
        ui.present()
