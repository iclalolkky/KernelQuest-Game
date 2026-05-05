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
    PATCH_PICK = auto()
    DAILY_BOARD = auto()
    HOWTOPLAY = auto()
    TUTORIAL = auto()
    # Phase 7 — narrative & identity.
    INTRO = auto()
    ENDING = auto()
    CODEX = auto()
    STACK_TRACE = auto()
    # Phase 8 — recognition.
    BESTIARY = auto()
    INSPECT = auto()
    # Phase 10 — interactive tutorial range.
    TUTORIAL_RANGE = auto()
    # Phase 11 — distros & structured runs.
    DISTRO_SELECT = auto()
    VENDOR = auto()
    MILESTONE_RESULT = auto()
    RUN_SUMMARY = auto()
    QUIT = auto()
