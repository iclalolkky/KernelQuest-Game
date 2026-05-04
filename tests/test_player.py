"""Tests for the `Player` entity."""

from __future__ import annotations

import pytest

from kernelquest.entities.player import Player
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType


def _open_grid(size: int = 6) -> MemoryGrid:
    """Build a grid with no inner obstacles for movement tests."""
    tiles = [[TileType.EMPTY for _ in range(size)] for _ in range(size)]
    for x in range(size):
        tiles[0][x] = TileType.SYSTEM_DATA
        tiles[size - 1][x] = TileType.SYSTEM_DATA
    for y in range(size):
        tiles[y][0] = TileType.SYSTEM_DATA
        tiles[y][size - 1] = TileType.SYSTEM_DATA
    return MemoryGrid(width=size, height=size, tiles=tiles)


def test_default_player_is_alive_and_full() -> None:
    p = Player()
    assert p.is_alive
    assert p.ram == p.max_ram
    assert p.cpu_cycles == p.max_cpu_cycles
    assert p.cache == []


def test_try_move_succeeds_and_consumes_cycle() -> None:
    grid = _open_grid()
    p = Player(position=(2, 2))
    cycles_before = p.cpu_cycles
    assert p.try_move(1, 0, grid) is True
    assert p.position == (3, 2)
    assert p.cpu_cycles == cycles_before - 1


def test_try_move_blocked_by_wall() -> None:
    grid = _open_grid()
    p = Player(position=(1, 1))
    # (0, 1) is a perimeter wall.
    cycles_before = p.cpu_cycles
    assert p.try_move(-1, 0, grid) is False
    assert p.position == (1, 1)
    assert p.cpu_cycles == cycles_before


def test_try_move_blocked_when_no_cycles() -> None:
    grid = _open_grid()
    p = Player(position=(2, 2), cpu_cycles=0)
    assert p.try_move(1, 0, grid) is False
    assert p.position == (2, 2)


def test_end_turn_refills_cycles() -> None:
    p = Player(cpu_cycles=0)
    p.end_turn()
    assert p.cpu_cycles == p.max_cpu_cycles


def test_take_damage_clamps_and_records_cause() -> None:
    p = Player(ram=20)
    p.take_damage(5, source="Logic Bomb")
    assert p.ram == 15
    assert p.crash_cause is None
    p.take_damage(50, source="Kernel Panic")
    assert p.ram == 0
    assert not p.is_alive
    assert p.crash_cause == "Kernel Panic"


def test_take_damage_negative_amount_raises() -> None:
    p = Player()
    with pytest.raises(ValueError):
        p.take_damage(-1, source="oops")


def test_heal_clamps_to_max() -> None:
    p = Player(ram=10)
    p.heal(9999)
    assert p.ram == p.max_ram


def test_cache_capacity_enforced() -> None:
    p = Player(cache_capacity=2)
    assert p.add_to_cache("packet_a") is True
    assert p.add_to_cache("packet_b") is True
    assert p.add_to_cache("packet_c") is False
    assert len(p.cache) == 2


def test_dead_player_cannot_move() -> None:
    grid = _open_grid()
    p = Player(position=(2, 2), ram=0, crash_cause="Out of RAM")
    assert p.try_move(1, 0, grid) is False
