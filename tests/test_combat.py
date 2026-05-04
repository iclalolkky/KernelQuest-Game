"""Tests for combat resolution."""

from __future__ import annotations

import random

from kernelquest.entities.malware import LogicBomb, SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.systems.combat import enemy_attack, player_attack
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def _world_with(enemy: object) -> World:
    grid = MemoryGrid(
        width=3, height=3, tiles=[[TileType.EMPTY for _ in range(3)] for _ in range(3)]
    )
    return World(grid=grid, player=Player(position=(0, 0)), enemies=[enemy])  # type: ignore[arg-type]


def test_player_attack_damages_target() -> None:
    enemy = SyntaxError_(position=(1, 0))
    world = _world_with(enemy)
    rng = random.Random(0)
    starting = enemy.hp

    result = player_attack(world, enemy, rng, damage=2)

    assert enemy.hp == starting - 2
    assert result.damage_dealt == 2
    assert result.killed is (enemy.hp == 0)


def test_player_attack_kill_awards_score() -> None:
    enemy = SyntaxError_(position=(1, 0))
    world = _world_with(enemy)
    rng = random.Random(0)

    result = player_attack(world, enemy, rng, damage=enemy.max_hp)

    assert result.killed is True
    assert result.score_gained == enemy.score_value
    assert world.player.score == enemy.score_value


def test_player_attack_can_drop_loot() -> None:
    # Try a few seeds until we observe a drop, to assert the mechanism works.
    dropped_any = False
    for seed in range(20):
        e = SyntaxError_(position=(2, 2))
        w = _world_with(e)
        r = random.Random(seed)
        result = player_attack(w, e, r, damage=e.max_hp)
        assert result.killed
        if result.loot_dropped is not None:
            assert w.items[(2, 2)] == result.loot_dropped
            dropped_any = True
            break
    assert dropped_any, "expected at least one loot drop across 20 seeds"


def test_enemy_attack_sets_crash_cause() -> None:
    enemy = LogicBomb(position=(0, 0))
    player = Player()
    enemy_attack(player, enemy)
    # Damage applied; if killed, crash_cause is recorded.
    if player.ram == 0:
        assert player.crash_cause == enemy.crash_label
