"""Handlers for cinematic-style states (INTRO, ENDING, CODEX)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


class _CinematicBase(GameStateHandler):
    """Shared rendering for INTRO and ENDING — both stream a `CinematicPlayer`."""

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_cinematic_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        if engine._cinematic is not None:
            ui.render_cinematic(engine._cinematic)


class IntroStateHandler(_CinematicBase):
    name = "INTRO"


class EndingStateHandler(_CinematicBase):
    name = "ENDING"


class CodexStateHandler(GameStateHandler):
    name = "CODEX"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_codex_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_codex(*engine._codex_view())
