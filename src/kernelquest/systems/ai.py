"""Enemy AI - runs after the player has spent all cycles for the turn."""

from __future__ import annotations

import random

from kernelquest.entities.malware import KernelPanic, LogicBomb, Malware, SyntaxError_
from kernelquest.systems.combat import enemy_attack
from kernelquest.systems.pathfinding import (
    bfs_next_step,
    chebyshev_distance,
)
from kernelquest.world.world import World


def run_enemy_turn(world: World, rng: random.Random, damage_multiplier: float = 1.0) -> list[str]:
    """Tick every alive enemy. Returns log messages for each meaningful event."""
    log: list[str] = []
    # Snapshot to avoid mutation during iteration.
    for enemy in list(world.enemies):
        if not enemy.is_alive or not world.player.is_alive:
            continue
        log.extend(_act(enemy, world, rng, damage_multiplier))
    world.remove_dead_enemies()
    return log


def _scaled_damage(base: int, multiplier: float) -> int:
    return max(1, int(round(base * multiplier)))


def _act(enemy: Malware, world: World, rng: random.Random, mult: float) -> list[str]:
    if isinstance(enemy, LogicBomb):
        return _act_logic_bomb(enemy, world, mult)
    if isinstance(enemy, KernelPanic):
        return _act_kernel_panic(enemy, world, rng, mult)
    if isinstance(enemy, SyntaxError_):
        return _act_syntax_error(enemy, world, rng, mult)
    return _step_toward_player(enemy, world)  # pragma: no cover


def _act_syntax_error(
    enemy: SyntaxError_, world: World, rng: random.Random, mult: float
) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) == 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} seni ısırdı, -{dmg} RAM"]

    # 25% chance to wander randomly; otherwise pathfind.
    if rng.random() < 0.25:
        return _wander(enemy, world, rng)
    return _step_toward_player(enemy, world)


def _act_logic_bomb(enemy: LogicBomb, world: World, mult: float) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) <= enemy.radius:
        return _detonate(enemy, world, mult)
    return _step_toward_player(enemy, world)


def _detonate(enemy: LogicBomb, world: World, mult: float) -> list[str]:
    log: list[str] = [f"{enemy.name} patlıyor!"]
    cx, cy = enemy.position
    blast_dmg = _scaled_damage(enemy.damage, mult)
    for dx in range(-enemy.radius, enemy.radius + 1):
        for dy in range(-enemy.radius, enemy.radius + 1):
            if dx == 0 and dy == 0:
                continue
            tx, ty = cx + dx, cy + dy
            if not world.grid.in_bounds(tx, ty):
                continue
            if world.player.position == (tx, ty):
                enemy_attack(world.player, enemy, damage=blast_dmg)
                log.append(f"Patlamadan {blast_dmg} RAM hasar aldın")
            other = world.enemy_at((tx, ty))
            if other is not None and other is not enemy:
                other.take_damage(enemy.damage)
    enemy.take_damage(enemy.max_hp)  # bomb consumes itself
    return log


def _act_kernel_panic(
    enemy: KernelPanic, world: World, rng: random.Random, mult: float
) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) <= 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} seni ezdi, -{dmg} RAM"]

    if (
        enemy.is_enraged
        and chebyshev_distance(enemy.position, player.position) <= 3
        and rng.random() < 0.5
    ):
        dx = player.position[0] - enemy.position[0]
        dy = player.position[1] - enemy.position[1]
        if dx == 0 or dy == 0:
            dmg = _scaled_damage(enemy.damage, mult)
            enemy_attack(player, enemy, damage=dmg)
            return [f"{enemy.name} kernel-tuzağı fırlattı (-{dmg} RAM)"]
    return _step_toward_player(enemy, world)


def _step_toward_player(enemy: Malware, world: World) -> list[str]:
    occupied = world.occupied_positions() - {enemy.position}
    next_pos = bfs_next_step(world.grid, enemy.position, world.player.position, blocked=occupied)
    if next_pos is None:
        return []
    enemy.position = next_pos
    return []


def _wander(enemy: Malware, world: World, rng: random.Random) -> list[str]:
    candidates: list[tuple[int, int]] = []
    cx, cy = enemy.position
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = cx + dx, cy + dy
        if not world.grid.is_walkable(nx, ny):
            continue
        if (nx, ny) in world.occupied_positions():
            continue
        candidates.append((nx, ny))
    if not candidates:
        return []
    enemy.position = rng.choice(candidates)
    return []
