"""High-level game state machine."""

from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    """Top-level state of the GameEngine."""

    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    HIGH_SCORES = auto()
    STATS = auto()
    SHOP = auto()
    SETTINGS = auto()
    TUTORIAL = auto()
    QUIT = auto()
