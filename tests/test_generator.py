"""Tests for procedural world generation."""

from __future__ import annotations

import random

from kernelquest.entities.player import Player
from kernelquest.world.generator import generate_starting_world, generate_world
from kernelquest.world.tile import TileType


def _has_exit(world: object) -> bool:
    grid = world.grid  # type: ignore[attr-defined]
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.get(x, y) is TileType.EXIT:
                return True
    return False


def test_generate_world_is_deterministic_with_seed() -> None:
    rng_a = random.Random(1234)
    rng_b = random.Random(1234)
    world_a = generate_world(player=Player(), depth=1, rng=rng_a)
    world_b = generate_world(player=Player(), depth=1, rng=rng_b)

    assert world_a.player.position == world_b.player.position
    assert [type(e).__name__ for e in world_a.enemies] == [
        type(e).__name__ for e in world_b.enemies
    ]
    assert sorted(world_a.items.items()) == sorted(world_b.items.items())


def test_generate_world_places_player_on_walkable_tile() -> None:
    rng = random.Random(7)
    world = generate_world(player=Player(), depth=1, rng=rng)
    px, py = world.player.position
    assert world.grid.is_walkable(px, py)


def test_generate_world_places_exit() -> None:
    rng = random.Random(42)
    world = generate_world(player=Player(), depth=1, rng=rng)
    assert _has_exit(world)


def test_enemy_count_scales_with_depth() -> None:
    rng_low = random.Random(1)
    rng_high = random.Random(1)
    low = generate_world(player=Player(), depth=1, rng=rng_low)
    high = generate_world(player=Player(), depth=4, rng=rng_high)
    assert len(high.enemies) > len(low.enemies)


def test_starting_world_helper_returns_rng() -> None:
    world, rng = generate_starting_world(seed=11)
    assert isinstance(rng, random.Random)
    assert world.depth == 1
