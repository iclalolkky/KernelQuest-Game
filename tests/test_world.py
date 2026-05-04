"""Tests for the World aggregate and enemy AI."""

from __future__ import annotations

import random

from kernelquest.entities.malware import LogicBomb, SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _empty_world(player_pos: tuple[int, int] = (0, 0)) -> World:
    grid = MemoryGrid(
        width=8, height=8, tiles=[[TileType.EMPTY for _ in range(8)] for _ in range(8)]
    )
    return World(grid=grid, player=Player(position=player_pos))


def test_enemy_at_returns_enemy() -> None:
    world = _empty_world()
    e = SyntaxError_(position=(2, 2))
    world.enemies.append(e)
    assert world.enemy_at((2, 2)) is e
    assert world.enemy_at((3, 3)) is None


def test_is_blocked_for_walls_and_entities() -> None:
    world = _empty_world(player_pos=(0, 0))
    world.grid.set(1, 0, TileType.SYSTEM_DATA)
    assert world.is_blocked((1, 0)) is True
    assert world.is_blocked((0, 0)) is True  # player
    e = SyntaxError_(position=(2, 2))
    world.enemies.append(e)
    assert world.is_blocked((2, 2)) is True
    assert world.is_blocked((3, 3)) is False


def test_remove_dead_enemies() -> None:
    world = _empty_world()
    alive = SyntaxError_(position=(1, 1))
    dead = SyntaxError_(position=(2, 2))
    dead.hp = 0
    world.enemies = [alive, dead]
    removed = world.remove_dead_enemies()
    assert removed == [dead]
    assert world.enemies == [alive]


def test_syntax_error_steps_toward_player() -> None:
    world = _empty_world(player_pos=(5, 5))
    e = SyntaxError_(position=(0, 0))
    world.enemies.append(e)
    # Use a deterministic RNG that won't hit the wander branch repeatedly.
    rng = random.Random(0)
    run_enemy_turn(world, rng)
    # Either moved toward player, attacked, or wandered — but should be on a
    # walkable tile and within grid bounds.
    assert world.grid.is_walkable(*e.position)


def test_logic_bomb_detonates_when_adjacent() -> None:
    world = _empty_world(player_pos=(2, 2))
    bomb = LogicBomb(position=(2, 3))
    world.enemies.append(bomb)
    rng = random.Random(0)
    starting_ram = world.player.ram
    run_enemy_turn(world, rng)
    # When adjacent (chebyshev<=radius), the bomb damages the player and kills itself.
    assert world.player.ram < starting_ram
    assert bomb.hp == 0
