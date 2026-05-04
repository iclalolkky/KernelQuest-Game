"""Tests for field-of-view computation."""

from __future__ import annotations

from kernelquest.systems.fov import compute_visible
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType


def _empty(w: int = 7, h: int = 7) -> MemoryGrid:
    tiles = [[TileType.EMPTY for _ in range(w)] for _ in range(h)]
    return MemoryGrid(width=w, height=h, tiles=tiles)


def test_visible_set_includes_origin() -> None:
    grid = _empty()
    visible = compute_visible(grid, (3, 3), radius=2)
    assert (3, 3) in visible


def test_visible_respects_radius() -> None:
    grid = _empty()
    visible = compute_visible(grid, (3, 3), radius=1)
    assert (3, 4) in visible
    assert (3, 5) not in visible


def test_walls_block_sight() -> None:
    grid = _empty()
    grid.set(3, 4, TileType.SYSTEM_DATA)
    visible = compute_visible(grid, (3, 3), radius=4)
    # The wall itself is visible, but tiles directly behind it are not.
    assert (3, 4) in visible
    assert (3, 6) not in visible


def test_negative_radius_returns_empty() -> None:
    grid = _empty()
    assert compute_visible(grid, (1, 1), radius=-1) == set()
