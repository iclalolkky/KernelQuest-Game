"""Tests for items and inventory."""

from __future__ import annotations

import pytest

from kernelquest.core.config import (
    GC_HEAL_AMOUNT,
    OPTIMIZATION_CYCLES,
    SCAN_BOOST_TURNS,
)
from kernelquest.entities.items import (
    GARBAGE_COLLECTOR,
    OPTIMIZATION,
    SCAN_BOOST,
    get_item,
)
from kernelquest.entities.player import Player
from kernelquest.systems.inventory import pickup_item_at, use_cache_slot
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _world() -> World:
    grid = MemoryGrid(
        width=3, height=3, tiles=[[TileType.EMPTY for _ in range(3)] for _ in range(3)]
    )
    return World(grid=grid, player=Player(position=(0, 0)))


def test_get_item_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_item("nope")


def test_garbage_collector_heals() -> None:
    player = Player()
    player.ram = max(1, player.max_ram - 50)
    msg = GARBAGE_COLLECTOR.apply(player)
    assert "RAM" in msg
    assert player.ram <= player.max_ram


def test_optimization_grants_cycles() -> None:
    player = Player()
    player.cpu_cycles = 0
    OPTIMIZATION.apply(player)
    assert player.cpu_cycles == min(OPTIMIZATION_CYCLES, player.max_cpu_cycles)


def test_scan_boost_extends_buff() -> None:
    player = Player()
    SCAN_BOOST.apply(player)
    assert player.has_scan_boost
    assert player.scan_boost_turns == SCAN_BOOST_TURNS


def test_pickup_moves_item_into_cache() -> None:
    world = _world()
    world.items[(0, 0)] = "gc"
    msg = pickup_item_at(world, (0, 0))
    assert msg is not None
    assert (0, 0) not in world.items
    assert world.player.cache == ["gc"]


def test_pickup_no_item_returns_none() -> None:
    world = _world()
    assert pickup_item_at(world, (0, 0)) is None


def test_use_cache_slot_applies_effect() -> None:
    world = _world()
    world.player.add_to_cache("gc")
    world.player.ram = max(1, world.player.max_ram - GC_HEAL_AMOUNT)
    starting = world.player.ram
    msg = use_cache_slot(world, 0)
    assert msg is not None
    assert world.player.ram > starting
    assert world.player.cache == []


def test_use_cache_slot_invalid_returns_none() -> None:
    world = _world()
    assert use_cache_slot(world, 0) is None
