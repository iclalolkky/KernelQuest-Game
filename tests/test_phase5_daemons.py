"""Phase 5 — daemon hooks (cron/swapd/oom-killer/tcpdump/niced)."""

from __future__ import annotations

from kernelquest.entities.daemon import (
    DAEMON_CRON,
    DAEMON_NICED,
    DAEMON_OOM_KILLER,
    DAEMON_SWAPD,
    DAEMON_TCPDUMP,
)
from kernelquest.entities.malware import SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.systems.daemons import (
    damage_multiplier_on_attack,
    on_pickup,
    on_turn_end,
    reveals_through_fog,
)
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _floor() -> World:
    tiles = [[TileType.EMPTY for _ in range(10)] for _ in range(10)]
    return World(grid=MemoryGrid(width=10, height=10, tiles=tiles), player=Player(position=(5, 5)))


def test_cron_heals_every_ten_turns() -> None:
    world = _floor()
    world.player.daemons = [DAEMON_CRON]
    world.player.ram = 50
    world.player.max_ram = 100
    msgs = on_turn_end(world, 9)
    assert world.player.ram == 50  # not yet
    assert msgs == []
    on_turn_end(world, 10)
    assert world.player.ram == 55


def test_niced_grants_cycle_when_no_enemy_in_fov() -> None:
    world = _floor()
    world.player.daemons = [DAEMON_NICED]
    world.player.cpu_cycles = 5
    world.player.max_cpu_cycles = 10
    on_turn_end(world, 1)
    assert world.player.cpu_cycles == 6


def test_oom_killer_boosts_low_ram_attacks() -> None:
    p = Player(max_ram=100, ram=100)
    p.daemons = [DAEMON_OOM_KILLER]
    assert damage_multiplier_on_attack(p) == 1.0
    p.ram = 10  # below 20 threshold
    assert damage_multiplier_on_attack(p) == 1.5


def test_swapd_pickup_bonus_scales_with_combo() -> None:
    world = _floor()
    world.player.daemons = [DAEMON_SWAPD]
    assert on_pickup(world) == 5  # combo=0 → max(1, 0)*5
    world.player.combo_count = 4
    assert on_pickup(world) == 20


def test_tcpdump_enables_fog_reveal() -> None:
    p = Player()
    assert reveals_through_fog(p) is False
    p.daemons = [DAEMON_TCPDUMP]
    assert reveals_through_fog(p) is True


def test_niced_skips_when_enemy_in_fov() -> None:
    world = _floor()
    world.player.daemons = [DAEMON_NICED]
    world.player.cpu_cycles = 5
    world.player.max_cpu_cycles = 10
    enemy = SyntaxError_(position=(5, 6))
    world.enemies.append(enemy)
    world.visible = {(5, 6)}
    on_turn_end(world, 1)
    assert world.player.cpu_cycles == 5
