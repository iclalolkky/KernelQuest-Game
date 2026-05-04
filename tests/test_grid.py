"""Tests for `MemoryGrid` and tile semantics."""

from __future__ import annotations

import pytest

from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType


def test_tile_walkability() -> None:
    assert TileType.EMPTY.walkable is True
    assert TileType.BAD_SECTOR.walkable is True
    assert TileType.SYSTEM_DATA.walkable is False


def test_static_default_has_perimeter_walls() -> None:
    grid = MemoryGrid.static_default(width=10, height=10)
    for x in range(10):
        assert grid.get(x, 0) is TileType.SYSTEM_DATA
        assert grid.get(x, 9) is TileType.SYSTEM_DATA
    for y in range(10):
        assert grid.get(0, y) is TileType.SYSTEM_DATA
        assert grid.get(9, y) is TileType.SYSTEM_DATA


def test_static_default_interior_is_walkable() -> None:
    grid = MemoryGrid.static_default(width=8, height=8)
    # Inner walls only land at coords inside the 8x8 grid; (1,1) is reserved
    # as the player's spawn and must always be walkable.
    assert grid.is_walkable(1, 1)


def test_in_bounds_and_walkable() -> None:
    grid = MemoryGrid.static_default(width=6, height=6)
    assert grid.in_bounds(0, 0)
    assert not grid.in_bounds(-1, 0)
    assert not grid.in_bounds(6, 0)
    assert not grid.is_walkable(-1, 0)
    assert not grid.is_walkable(0, 0)  # perimeter wall


def test_get_out_of_bounds_raises() -> None:
    grid = MemoryGrid.static_default(width=5, height=5)
    with pytest.raises(IndexError):
        grid.get(99, 99)


def test_set_replaces_tile() -> None:
    grid = MemoryGrid.static_default(width=5, height=5)
    grid.set(2, 2, TileType.BAD_SECTOR)
    assert grid.get(2, 2) is TileType.BAD_SECTOR
