"""High-level game state machine."""

from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    """Top-level state of the GameEngine."""

    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    QUIT = auto()
