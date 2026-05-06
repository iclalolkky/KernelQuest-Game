"""Behavioural tests for systems.ai with difficulty multiplier wiring."""

from __future__ import annotations

import random

from kernelquest.entities.malware import KernelPanic, LogicBomb, SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _floor_world(width: int = 10, height: int = 10) -> World:
    tiles = [[TileType.EMPTY for _ in range(height)] for _ in range(width)]
    grid = MemoryGrid(width=width, height=height, tiles=tiles)
    return World(grid=grid, player=Player(position=(width // 2, height // 2)))


def test_syntax_error_attacks_player_at_range_one() -> None:
    world = _floor_world()
    px, py = world.player.position
    enemy = SyntaxError_(position=(px + 1, py))
    world.enemies.append(enemy)

    starting_ram = world.player.ram
    msgs = run_enemy_turn(world, random.Random(0), damage_multiplier=1.0)

    assert any("ısırdı" in m for m in msgs)
    assert world.player.ram < starting_ram


def test_damage_multiplier_amplifies_enemy_damage() -> None:
    world = _floor_world()
    px, py = world.player.position
    world.enemies.append(SyntaxError_(position=(px + 1, py)))
    starting_ram = world.player.ram
    run_enemy_turn(world, random.Random(0), damage_multiplier=3.0)
    delta = starting_ram - world.player.ram
    assert delta >= 3  # scaled by mult; baseline syntax-error damage is 1


def test_logic_bomb_detonates_in_range() -> None:
    world = _floor_world()
    px, py = world.player.position
    bomb = LogicBomb(position=(px + 1, py))
    world.enemies.append(bomb)
    msgs = run_enemy_turn(world, random.Random(0), damage_multiplier=1.0)
    assert any("patlıyor" in m for m in msgs)
    # Bomb consumed itself.
    assert not bomb.is_alive


def test_kernel_panic_melee() -> None:
    world = _floor_world()
    px, py = world.player.position
    world.enemies.append(KernelPanic(position=(px + 1, py)))
    starting_ram = world.player.ram
    msgs = run_enemy_turn(world, random.Random(123), damage_multiplier=1.0)
    assert any("ezdi" in m for m in msgs)
    assert world.player.ram < starting_ram
