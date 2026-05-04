"""Tests for BFS pathfinding helpers."""

from __future__ import annotations

from kernelquest.systems.pathfinding import (
    bfs_next_step,
    chebyshev_distance,
    manhattan_distance,
)
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType


def _empty_grid(w: int = 5, h: int = 5) -> MemoryGrid:
    tiles = [[TileType.EMPTY for _ in range(w)] for _ in range(h)]
    return MemoryGrid(width=w, height=h, tiles=tiles)


def test_chebyshev_and_manhattan() -> None:
    assert chebyshev_distance((0, 0), (3, 4)) == 4
    assert manhattan_distance((0, 0), (3, 4)) == 7


def test_bfs_returns_first_step_toward_goal() -> None:
    grid = _empty_grid()
    step = bfs_next_step(grid, (0, 0), (3, 0))
    assert step == (1, 0)


def test_bfs_returns_none_when_at_goal() -> None:
    grid = _empty_grid()
    assert bfs_next_step(grid, (1, 1), (1, 1)) is None


def test_bfs_routes_around_blocked_tiles() -> None:
    grid = _empty_grid()
    # Block the direct horizontal path with another entity.
    blocked = {(1, 0)}
    step = bfs_next_step(grid, (0, 0), (3, 0), blocked=blocked)
    assert step is not None
    assert step != (1, 0)


def test_bfs_treats_goal_tile_as_reachable() -> None:
    grid = _empty_grid()
    # Even if the goal is in `blocked`, BFS should still target it.
    step = bfs_next_step(grid, (0, 0), (1, 0), blocked={(1, 0)})
    assert step == (1, 0)


def test_bfs_returns_none_when_unreachable() -> None:
    grid = _empty_grid(3, 3)
    # Wall off the goal so BFS cannot reach it.
    grid.set(1, 2, TileType.SYSTEM_DATA)
    grid.set(2, 1, TileType.SYSTEM_DATA)
    step = bfs_next_step(grid, (0, 0), (2, 2))
    assert step is None
