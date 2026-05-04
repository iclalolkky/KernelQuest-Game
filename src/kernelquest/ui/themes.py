"""Theme registry — switchable color palettes.

The legacy `kernelquest.ui.theme` module exposes module-level constants used
across the renderer. To support runtime theme switching without a large
refactor, this module mutates those module attributes via :func:`apply_theme`.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.ui import theme as theme_mod


@dataclass(frozen=True)
class Theme:
    """A complete color palette for a single theme."""

    key: str
    label: str
    BACKGROUND: tuple[int, int, int]
    GRID_LINE: tuple[int, int, int]
    PANEL_BG: tuple[int, int, int]
    NEON_CYAN: tuple[int, int, int]
    NEON_GREEN: tuple[int, int, int]
    NEON_MAGENTA: tuple[int, int, int]
    NEON_AMBER: tuple[int, int, int]
    TEXT_PRIMARY: tuple[int, int, int]
    TEXT_DIM: tuple[int, int, int]
    TILE_EMPTY: tuple[int, int, int]
    TILE_SYSTEM_DATA: tuple[int, int, int]
    TILE_BAD_SECTOR: tuple[int, int, int]
    TILE_EXIT: tuple[int, int, int]
    PLAYER_COLOR: tuple[int, int, int]
    ENEMY_SYNTAX_ERROR: tuple[int, int, int]
    ENEMY_LOGIC_BOMB: tuple[int, int, int]
    ENEMY_KERNEL_PANIC: tuple[int, int, int]
    ITEM_GC: tuple[int, int, int]
    ITEM_OPTIMIZATION: tuple[int, int, int]
    ITEM_SCAN_BOOST: tuple[int, int, int]


THEME_KERNEL = Theme(
    key="kernel",
    label="Kernel (Default)",
    BACKGROUND=(8, 12, 24),
    GRID_LINE=(20, 32, 56),
    PANEL_BG=(14, 20, 36),
    NEON_CYAN=(0, 230, 255),
    NEON_GREEN=(57, 255, 170),
    NEON_MAGENTA=(255, 80, 200),
    NEON_AMBER=(255, 170, 60),
    TEXT_PRIMARY=(220, 240, 255),
    TEXT_DIM=(120, 150, 180),
    TILE_EMPTY=(16, 24, 44),
    TILE_SYSTEM_DATA=(40, 70, 120),
    TILE_BAD_SECTOR=(140, 30, 60),
    TILE_EXIT=(255, 80, 200),
    PLAYER_COLOR=(57, 255, 170),
    ENEMY_SYNTAX_ERROR=(255, 200, 80),
    ENEMY_LOGIC_BOMB=(255, 90, 90),
    ENEMY_KERNEL_PANIC=(200, 80, 255),
    ITEM_GC=(80, 255, 170),
    ITEM_OPTIMIZATION=(255, 200, 60),
    ITEM_SCAN_BOOST=(80, 200, 255),
)


THEME_PHOSPHOR = Theme(
    key="phosphor",
    label="Phosphor Green",
    BACKGROUND=(2, 12, 6),
    GRID_LINE=(12, 36, 18),
    PANEL_BG=(6, 22, 10),
    NEON_CYAN=(120, 255, 160),
    NEON_GREEN=(60, 255, 80),
    NEON_MAGENTA=(180, 255, 200),
    NEON_AMBER=(220, 255, 140),
    TEXT_PRIMARY=(180, 255, 200),
    TEXT_DIM=(80, 160, 100),
    TILE_EMPTY=(8, 24, 12),
    TILE_SYSTEM_DATA=(20, 80, 30),
    TILE_BAD_SECTOR=(120, 60, 30),
    TILE_EXIT=(220, 255, 200),
    PLAYER_COLOR=(60, 255, 80),
    ENEMY_SYNTAX_ERROR=(180, 255, 100),
    ENEMY_LOGIC_BOMB=(255, 120, 80),
    ENEMY_KERNEL_PANIC=(255, 200, 80),
    ITEM_GC=(120, 255, 140),
    ITEM_OPTIMIZATION=(220, 255, 140),
    ITEM_SCAN_BOOST=(160, 255, 200),
)


THEME_AMBER = Theme(
    key="amber",
    label="Amber CRT",
    BACKGROUND=(16, 8, 0),
    GRID_LINE=(48, 24, 0),
    PANEL_BG=(28, 14, 0),
    NEON_CYAN=(255, 200, 80),
    NEON_GREEN=(255, 220, 100),
    NEON_MAGENTA=(255, 140, 60),
    NEON_AMBER=(255, 180, 40),
    TEXT_PRIMARY=(255, 220, 140),
    TEXT_DIM=(180, 120, 60),
    TILE_EMPTY=(28, 16, 4),
    TILE_SYSTEM_DATA=(120, 70, 0),
    TILE_BAD_SECTOR=(180, 60, 0),
    TILE_EXIT=(255, 220, 80),
    PLAYER_COLOR=(255, 220, 100),
    ENEMY_SYNTAX_ERROR=(255, 200, 80),
    ENEMY_LOGIC_BOMB=(255, 100, 60),
    ENEMY_KERNEL_PANIC=(255, 140, 60),
    ITEM_GC=(255, 220, 140),
    ITEM_OPTIMIZATION=(255, 200, 80),
    ITEM_SCAN_BOOST=(255, 240, 180),
)


THEME_HIGH_CONTRAST = Theme(
    key="high-contrast",
    label="High Contrast (A11y)",
    BACKGROUND=(0, 0, 0),
    GRID_LINE=(60, 60, 60),
    PANEL_BG=(20, 20, 20),
    NEON_CYAN=(255, 255, 255),
    NEON_GREEN=(255, 255, 0),
    NEON_MAGENTA=(0, 255, 255),
    NEON_AMBER=(255, 128, 0),
    TEXT_PRIMARY=(255, 255, 255),
    TEXT_DIM=(180, 180, 180),
    TILE_EMPTY=(20, 20, 20),
    TILE_SYSTEM_DATA=(80, 80, 80),
    TILE_BAD_SECTOR=(255, 0, 0),
    TILE_EXIT=(0, 255, 255),
    PLAYER_COLOR=(255, 255, 0),
    ENEMY_SYNTAX_ERROR=(255, 128, 0),
    ENEMY_LOGIC_BOMB=(255, 0, 0),
    ENEMY_KERNEL_PANIC=(255, 0, 255),
    ITEM_GC=(0, 255, 0),
    ITEM_OPTIMIZATION=(255, 255, 0),
    ITEM_SCAN_BOOST=(0, 255, 255),
)


CATALOG: tuple[Theme, ...] = (THEME_KERNEL, THEME_PHOSPHOR, THEME_AMBER, THEME_HIGH_CONTRAST)


def get_theme(key: str) -> Theme:
    for theme in CATALOG:
        if theme.key == key:
            return theme
    return THEME_KERNEL


_THEME_ATTRS: tuple[str, ...] = (
    "BACKGROUND",
    "GRID_LINE",
    "PANEL_BG",
    "NEON_CYAN",
    "NEON_GREEN",
    "NEON_MAGENTA",
    "NEON_AMBER",
    "TEXT_PRIMARY",
    "TEXT_DIM",
    "TILE_EMPTY",
    "TILE_SYSTEM_DATA",
    "TILE_BAD_SECTOR",
    "TILE_EXIT",
    "PLAYER_COLOR",
    "ENEMY_SYNTAX_ERROR",
    "ENEMY_LOGIC_BOMB",
    "ENEMY_KERNEL_PANIC",
    "ITEM_GC",
    "ITEM_OPTIMIZATION",
    "ITEM_SCAN_BOOST",
)


def apply_theme(theme: Theme | str) -> Theme:
    """Apply ``theme`` by mutating the legacy ``ui.theme`` module globals."""
    resolved = theme if isinstance(theme, Theme) else get_theme(theme)
    for attr in _THEME_ATTRS:
        setattr(theme_mod, attr, getattr(resolved, attr))
    return resolved


__all__ = [
    "CATALOG",
    "THEME_AMBER",
    "THEME_HIGH_CONTRAST",
    "THEME_KERNEL",
    "THEME_PHOSPHOR",
    "Theme",
    "apply_theme",
    "get_theme",
]
