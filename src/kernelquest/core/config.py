"""Centralized constants and tunables.

Keep magic numbers out of game logic — import from here instead.
"""

from __future__ import annotations

from typing import Final

# --- Display ---
WINDOW_TITLE: Final[str] = "Kernel Quest: The Memory Leak"
WINDOW_WIDTH: Final[int] = 1280
WINDOW_HEIGHT: Final[int] = 720
FPS: Final[int] = 60

# --- Grid ---
GRID_WIDTH: Final[int] = 20
GRID_HEIGHT: Final[int] = 20
TILE_SIZE: Final[int] = 32

# --- Fog of War ---
DEFAULT_SCAN_RADIUS: Final[int] = 4

# --- Player defaults ---
PLAYER_START_RAM: Final[int] = 100
PLAYER_START_CPU_CYCLES: Final[int] = 5
PLAYER_CACHE_CAPACITY: Final[int] = 8

# --- Combat ---
PLAYER_BASE_DAMAGE: Final[int] = 10

# --- Persistence ---
DATABASE_FILENAME: Final[str] = "database.db"
