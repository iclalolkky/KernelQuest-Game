"""Tron-flavored color palette and font sizes."""

from __future__ import annotations

# --- Colors (R, G, B) ---
BACKGROUND: tuple[int, int, int] = (8, 12, 24)
GRID_LINE: tuple[int, int, int] = (20, 32, 56)
PANEL_BG: tuple[int, int, int] = (14, 20, 36)

NEON_CYAN: tuple[int, int, int] = (0, 230, 255)
NEON_GREEN: tuple[int, int, int] = (57, 255, 170)
NEON_MAGENTA: tuple[int, int, int] = (255, 80, 200)
NEON_AMBER: tuple[int, int, int] = (255, 170, 60)
TEXT_PRIMARY: tuple[int, int, int] = (220, 240, 255)
TEXT_DIM: tuple[int, int, int] = (120, 150, 180)

# --- Tile colors ---
TILE_EMPTY: tuple[int, int, int] = (16, 24, 44)
TILE_SYSTEM_DATA: tuple[int, int, int] = (40, 70, 120)
TILE_BAD_SECTOR: tuple[int, int, int] = (140, 30, 60)
TILE_EXIT: tuple[int, int, int] = (255, 80, 200)

# --- Entity colors ---
PLAYER_COLOR: tuple[int, int, int] = NEON_GREEN
ENEMY_SYNTAX_ERROR: tuple[int, int, int] = (255, 200, 80)
ENEMY_LOGIC_BOMB: tuple[int, int, int] = (255, 90, 90)
ENEMY_KERNEL_PANIC: tuple[int, int, int] = (200, 80, 255)

# --- Item colors ---
ITEM_GC: tuple[int, int, int] = (80, 255, 170)
ITEM_OPTIMIZATION: tuple[int, int, int] = (255, 200, 60)
ITEM_SCAN_BOOST: tuple[int, int, int] = (80, 200, 255)

# --- Font sizes ---
FONT_SIZE_SMALL: int = 14
FONT_SIZE_BODY: int = 18
FONT_SIZE_TITLE: int = 36
