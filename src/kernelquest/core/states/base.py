"""Base `GameStateHandler` interface used by the State Pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


class GameStateHandler:
    """Base class for per-`GameState` handlers.

    Concrete subclasses live under :mod:`kernelquest.core.states`. Each
    handler is a stateless singleton; the active :class:`GameEngine`
    instance is passed in for any data the handler needs to read or
    mutate.

    The hooks below are intentionally non-abstract — every state needs
    ``handle_event`` and ``render``, but ``enter`` / ``exit`` / ``update``
    are optional and default to no-ops so subclasses only override what
    they care about.
    """

    #: Optional human-friendly tag for debugging/logging.
    name: str = "GameStateHandler"

    def enter(self, engine: GameEngine) -> None:
        """Called once when this state becomes the active state."""
        return None

    def exit(self, engine: GameEngine) -> None:
        """Called once when leaving this state."""
        return None

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        """Handle a single ``pygame.KEYDOWN`` event for this state."""
        return None

    def update(self, engine: GameEngine, dt: float) -> None:
        """Per-frame logic update (most states leave this empty)."""
        return None

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        """Render this state. The frame is presented by the engine."""
        return None
