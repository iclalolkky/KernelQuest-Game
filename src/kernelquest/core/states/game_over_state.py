"""Handlers for the post-run flow: GAME_OVER and RUN_SUMMARY."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


class GameOverStateHandler(GameStateHandler):
    name = "GAME_OVER"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_game_over_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        if engine._world is None:
            return
        ui.render_game_over(engine._world.player, engine._name_buffer)
        ui.render_post_run_summary(engine._post_run_summary)


class RunSummaryStateHandler(GameStateHandler):
    name = "RUN_SUMMARY"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_run_summary_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_run_summary(engine._run_summary_payload)
