"""Tests for World fog-of-war integration."""

from __future__ import annotations

from kernelquest.entities.player import Player
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _world(player_pos: tuple[int, int] = (3, 3)) -> World:
    grid = MemoryGrid(
        width=10, height=10, tiles=[[TileType.EMPTY for _ in range(10)] for _ in range(10)]
    )
    return World(grid=grid, player=Player(position=player_pos))


def test_recompute_fov_populates_visible_and_explored() -> None:
    world = _world()
    world.recompute_fov()
    assert world.player.position in world.visible
    assert world.visible.issubset(world.explored)


def test_explored_persists_across_recompute() -> None:
    world = _world(player_pos=(1, 1))
    world.recompute_fov()
    initial_explored = set(world.explored)
    world.player.position = (8, 8)
    world.recompute_fov()
    # Earlier positions remain in explored even after moving away.
    assert initial_explored.issubset(world.explored)
    assert (8, 8) in world.visible


def test_scan_boost_extends_visibility() -> None:
    world_a = _world()
    world_a.recompute_fov()
    base_count = len(world_a.visible)

    world_b = _world()
    world_b.player.grant_scan_boost(5)
    world_b.recompute_fov()
    assert len(world_b.visible) > base_count
