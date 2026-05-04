"""Phase 5 — programs (kill9, sudo, grep, nice, fork)."""

from __future__ import annotations

import random

from kernelquest.entities.malware import KernelPanic, SyntaxError_, ZombieProcess
from kernelquest.entities.player import Player
from kernelquest.entities.program import (
    PROGRAM_FORK,
    PROGRAM_GREP,
    PROGRAM_KILL_DASH9,
    PROGRAM_NICE,
    PROGRAM_SUDO,
    ProgramSlot,
    starter_loadout,
)
from kernelquest.systems.programs import execute_program
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _floor(width: int = 10, height: int = 10) -> World:
    tiles = [[TileType.EMPTY for _ in range(height)] for _ in range(width)]
    grid = MemoryGrid(width=width, height=height, tiles=tiles)
    return World(grid=grid, player=Player(position=(width // 2, height // 2)))


def test_starter_loadout_has_three_programs() -> None:
    loadout = starter_loadout()
    assert len(loadout) == 3
    keys = [s.program.key for s in loadout]
    assert "kill9" in keys and "sudo" in keys and "grep" in keys


def test_kill9_terminates_adjacent_enemy() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_KILL_DASH9, charges=1)]
    world.player.cpu_cycles = 99
    px, py = world.player.position
    enemy = SyntaxError_(position=(px + 1, py))
    world.enemies.append(enemy)

    result = execute_program(world, 0, random.Random(0))
    assert result.success
    assert result.killed_enemy is enemy
    assert not enemy.is_alive


def test_kill9_refuses_kernel_panic() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_KILL_DASH9, charges=1)]
    world.player.cpu_cycles = 99
    px, py = world.player.position
    boss = KernelPanic(position=(px + 1, py))
    world.enemies.append(boss)

    result = execute_program(world, 0, random.Random(0))
    assert not result.success
    assert boss.is_alive


def test_kill9_double_taps_zombie_process() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_KILL_DASH9, charges=1)]
    world.player.cpu_cycles = 99
    px, py = world.player.position
    z = ZombieProcess(position=(px + 1, py))
    world.enemies.append(z)

    result = execute_program(world, 0, random.Random(0))
    assert result.success
    assert not z.is_alive


def test_sudo_sets_next_attack_multiplier() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_SUDO, charges=2)]
    world.player.cpu_cycles = 99
    result = execute_program(world, 0, random.Random(0))
    assert result.success
    assert world.player.next_attack_multiplier == 3.0


def test_grep_reveals_full_grid() -> None:
    world = _floor(8, 8)
    world.player.programs = [ProgramSlot(program=PROGRAM_GREP, charges=2)]
    world.player.cpu_cycles = 99
    result = execute_program(world, 0, random.Random(0))
    assert result.success
    assert len(world.visible) == 8 * 8
    assert len(world.explored) == 8 * 8


def test_nice_skips_enemy_turns() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_NICE, charges=1)]
    world.player.cpu_cycles = 99
    result = execute_program(world, 0, random.Random(0))
    assert result.success
    assert world.player.enemies_skip_turns >= 2


def test_fork_spawns_decoy() -> None:
    world = _floor()
    world.player.programs = [ProgramSlot(program=PROGRAM_FORK, charges=2)]
    world.player.cpu_cycles = 99
    result = execute_program(world, 0, random.Random(7))
    assert result.success
    assert result.spawned_decoy_at is not None


def test_program_fails_when_no_charges() -> None:
    world = _floor()
    slot = ProgramSlot(program=PROGRAM_SUDO, charges=0)
    world.player.programs = [slot]
    world.player.cpu_cycles = 99
    result = execute_program(world, 0, random.Random(0))
    assert not result.success
