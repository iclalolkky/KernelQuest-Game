"""Tron-flavored color palette and font sizes."""

from __future__ import annotations

from typing import Final

# --- Colors (R, G, B) ---
BACKGROUND: Final[tuple[int, int, int]] = (8, 12, 24)
GRID_LINE: Final[tuple[int, int, int]] = (20, 32, 56)
PANEL_BG: Final[tuple[int, int, int]] = (14, 20, 36)

NEON_CYAN: Final[tuple[int, int, int]] = (0, 230, 255)
NEON_GREEN: Final[tuple[int, int, int]] = (57, 255, 170)
NEON_MAGENTA: Final[tuple[int, int, int]] = (255, 80, 200)
NEON_AMBER: Final[tuple[int, int, int]] = (255, 170, 60)
TEXT_PRIMARY: Final[tuple[int, int, int]] = (220, 240, 255)
TEXT_DIM: Final[tuple[int, int, int]] = (120, 150, 180)

# --- Tile colors ---
TILE_EMPTY: Final[tuple[int, int, int]] = (16, 24, 44)
TILE_SYSTEM_DATA: Final[tuple[int, int, int]] = (40, 70, 120)
TILE_BAD_SECTOR: Final[tuple[int, int, int]] = (140, 30, 60)
TILE_EXIT: Final[tuple[int, int, int]] = (255, 80, 200)

# --- Entity colors ---
PLAYER_COLOR: Final[tuple[int, int, int]] = NEON_GREEN
ENEMY_SYNTAX_ERROR: Final[tuple[int, int, int]] = (255, 200, 80)
ENEMY_LOGIC_BOMB: Final[tuple[int, int, int]] = (255, 90, 90)
ENEMY_KERNEL_PANIC: Final[tuple[int, int, int]] = (200, 80, 255)

# --- Item colors ---
ITEM_GC: Final[tuple[int, int, int]] = (80, 255, 170)
ITEM_OPTIMIZATION: Final[tuple[int, int, int]] = (255, 200, 60)
ITEM_SCAN_BOOST: Final[tuple[int, int, int]] = (80, 200, 255)

# --- Font sizes ---
FONT_SIZE_SMALL: Final[int] = 14
FONT_SIZE_BODY: Final[int] = 18
FONT_SIZE_TITLE: Final[int] = 36
