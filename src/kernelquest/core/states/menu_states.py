"""Handlers for menu-style states (MENU, SETTINGS, HOWTOPLAY, …).

These are all read-only / navigation screens that share simple keyboard-driven
flow: ``↑/↓`` to move a cursor, ``ENTER`` to activate, ``ESC`` to back out.

The handlers here are stateless singletons; all data lives on
:class:`~kernelquest.core.engine.GameEngine`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler
from kernelquest.world.daily import today_iso

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


class MenuStateHandler(GameStateHandler):
    """Top-level main menu."""

    name = "MENU"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_menu_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        from kernelquest.core.engine import _MENU_OPTIONS
        from kernelquest.ui.i18n import t as _t

        labels = [_t(f"menu.{key}") for key in _MENU_OPTIONS]
        ui.render_menu(labels, engine._menu_index)


class SettingsStateHandler(GameStateHandler):
    name = "SETTINGS"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_settings_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_settings(engine._settings_rows(), engine._settings_index)


class HowToPlayStateHandler(GameStateHandler):
    name = "HOWTOPLAY"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_howtoplay_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_howtoplay(engine._howtoplay_lines, engine._howtoplay_scroll)


class HighScoresStateHandler(GameStateHandler):
    name = "HIGH_SCORES"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_back_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_high_scores(engine._fetch_high_scores())


class StatsStateHandler(GameStateHandler):
    name = "STATS"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_back_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        avg, deaths, best, count = engine._fetch_stats()
        ui.render_stats(avg, deaths, best, count)


class DailyBoardStateHandler(GameStateHandler):
    name = "DAILY_BOARD"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_back_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_daily_board(today_iso(), engine._fetch_daily_board())


class DistroSelectStateHandler(GameStateHandler):
    """Distro picker shown before a fresh run."""

    name = "DISTRO_SELECT"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_distro_select_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_distro_select(
            rows=engine._distro_rows(),
            selected=engine._distro_index,
            daily=engine._distro_select_for_daily,
        )
