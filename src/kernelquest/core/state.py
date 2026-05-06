"""Üst düzey oyun durum makinesi."""

from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    """GameEngine'in üst düzey durumu."""

    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    HIGH_SCORES = auto()
    STATS = auto()
    SHOP = auto()
    SETTINGS = auto()
    TUTORIAL = auto()
    QUIT_CONFIRM = auto()
    QUIT = auto()
