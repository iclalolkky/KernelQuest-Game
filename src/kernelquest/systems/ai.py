"""Enemy AI — runs after the player has spent all cycles for the turn."""

from __future__ import annotations

import random

from kernelquest.entities.affix import on_turn_end as _affix_turn_end
from kernelquest.entities.malware import (
    Bruiser,
    BufferOverflowBoss,
    Daemonizer,
    DeadlockTwin,
    ForkBomb,
    KernelPanic,
    LogicBomb,
    Malware,
    NullPointer,
    RaceCondition,
    RootkitHydra,
    RuntimeError_,
    SegFault,
    StackOverflow,
    SyntaxError_,
    TheLeak,
    ZeroDayBoss,
    ZombieProcess,
)
from kernelquest.systems.combat import enemy_attack
from kernelquest.systems.pathfinding import (
    bfs_next_step,
    chebyshev_distance,
)
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


def run_enemy_turn(world: World, rng: random.Random, damage_multiplier: float = 1.0) -> list[str]:
    """Tick every alive enemy. Returns log messages for each meaningful event."""
    log: list[str] = []
    if world.player.enemies_skip_turns > 0:
        log.append("Enemies stalled (nice).")
        return log
    # Phase 9 — reset DeadlockTwin same-turn flag at the start of each
    # enemy turn (player just finished their actions).
    for enemy in world.enemies:
        if isinstance(enemy, DeadlockTwin):
            enemy.attacked_this_turn = False
    # Snapshot to avoid mutation during iteration.
    for enemy in list(world.enemies):
        if not enemy.is_alive or not world.player.is_alive:
            continue
        log.extend(_act(enemy, world, rng, damage_multiplier))
        log.extend(_affix_turn_end(enemy, world))
        # Overclocked affix → take an extra act every other turn.
        if enemy.affixes.has("overclocked") and enemy.is_alive:
            if enemy.affixes.overclock_extra_turn:
                log.extend(_act(enemy, world, rng, damage_multiplier))
            enemy.affixes.overclock_extra_turn = not enemy.affixes.overclock_extra_turn
    world.remove_dead_enemies()
    return log


def _scaled_damage(base: int, multiplier: float) -> int:
    return max(1, int(round(base * multiplier)))


def _act(enemy: Malware, world: World, rng: random.Random, mult: float) -> list[str]:
    if isinstance(enemy, LogicBomb):
        return _act_logic_bomb(enemy, world, mult)
    if isinstance(enemy, SegFault):
        return _act_segfault(enemy, world, rng, mult)
    if isinstance(enemy, KernelPanic):
        return _act_kernel_panic(enemy, world, rng, mult)
    if isinstance(enemy, TheLeak):
        return _act_the_leak(enemy, world, rng, mult)
    if isinstance(enemy, DeadlockTwin):
        return _act_deadlock_twin(enemy, world, rng, mult)
    if isinstance(enemy, RootkitHydra):
        return _act_rootkit_hydra(enemy, world, rng, mult)
    if isinstance(enemy, BufferOverflowBoss):
        return _act_buffer_overflow(enemy, world, rng, mult)
    if isinstance(enemy, ZeroDayBoss):
        return _act_zero_day(enemy, world, rng, mult)
    if isinstance(enemy, (ZombieProcess, ForkBomb)):
        return _act_zombie_process(enemy, world, rng, mult)
    if isinstance(enemy, StackOverflow):
        return _act_stack_overflow(enemy, world, rng, mult)
    if isinstance(enemy, NullPointer):
        return _act_null_pointer(enemy, world, rng, mult)
    if isinstance(enemy, RaceCondition):
        return _act_race_condition(enemy, world, rng, mult)
    if isinstance(enemy, Daemonizer):
        return _act_daemonizer(enemy, world, rng, mult)
    if isinstance(enemy, Bruiser):
        return _act_bruiser(enemy, world, rng, mult)
    if isinstance(enemy, RuntimeError_):
        return _act_runtime_error(enemy, world, rng, mult)
    if isinstance(enemy, SyntaxError_):
        return _act_syntax_error(enemy, world, rng, mult)
    return _step_toward_player(enemy, world)  # pragma: no cover


def _act_syntax_error(
    enemy: SyntaxError_, world: World, rng: random.Random, mult: float
) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) == 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} bit you for {dmg} RAM"]

    # 25% chance to wander randomly; otherwise pathfind.
    if rng.random() < 0.25:
        return _wander(enemy, world, rng)
    return _step_toward_player(enemy, world)


def _act_runtime_error(
    enemy: RuntimeError_, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Faster `Skirmisher` — moves twice if not adjacent."""
    log = _act_syntax_error(enemy, world, rng, mult)
    if enemy.is_alive and chebyshev_distance(enemy.position, world.player.position) > 1:
        log.extend(_step_toward_player(enemy, world))
    return log


def _act_logic_bomb(enemy: LogicBomb, world: World, mult: float) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) <= enemy.radius:
        return _detonate(enemy, world, mult)
    return _step_toward_player(enemy, world)


def _detonate(enemy: LogicBomb, world: World, mult: float) -> list[str]:
    log: list[str] = [f"{enemy.name} detonates!"]
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
                log.append(f"You take {blast_dmg} RAM from the blast")
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
        return [f"{enemy.name} crushes you for {dmg} RAM"]

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
            return [f"{enemy.name} fires a kernel trap (-{dmg} RAM)"]
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


def _act_zombie_process(enemy: Malware, world: World, rng: random.Random, mult: float) -> list[str]:
    player = world.player
    if chebyshev_distance(enemy.position, player.position) == 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} clawed you for {dmg} RAM"]
    if rng.random() < 0.2:
        return _wander(enemy, world, rng)
    return _step_toward_player(enemy, world)


def _act_segfault(enemy: SegFault, world: World, rng: random.Random, mult: float) -> list[str]:
    if enemy.pending_teleport:
        new_pos = _random_walkable(world, rng, exclude={enemy.position})
        if new_pos is not None:
            enemy.position = new_pos
        enemy.pending_teleport = False
        return [f"{enemy.name} segfaults to a new address!"]

    player = world.player
    if chebyshev_distance(enemy.position, player.position) <= 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} corrupted you for {dmg} RAM"]
    return _step_toward_player(enemy, world)


def _act_stack_overflow(
    enemy: StackOverflow, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Caster: ranged attack within FoV that knocks the player back one tile."""
    player = world.player
    dist = chebyshev_distance(enemy.position, player.position)
    if dist <= 1:
        # Adjacent: bump-attack like a melee.
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} overflows for {dmg} RAM"]
    if dist <= 5 and enemy.cooldown == 0:
        dmg = _scaled_damage(enemy.damage, mult)
        enemy_attack(player, enemy, damage=dmg)
        # Knock player one tile away (no-op if blocked).
        dx = (
            0
            if player.position[0] == enemy.position[0]
            else (1 if player.position[0] > enemy.position[0] else -1)
        )
        dy = (
            0
            if player.position[1] == enemy.position[1]
            else (1 if player.position[1] > enemy.position[1] else -1)
        )
        nx, ny = player.position[0] + dx, player.position[1] + dy
        if world.grid.is_walkable(nx, ny) and (nx, ny) not in world.occupied_positions():
            player.position = (nx, ny)
        enemy.cooldown = 2
        return [f"{enemy.name} pushes you for {dmg} RAM"]
    if enemy.cooldown > 0:
        enemy.cooldown -= 1
    return _step_toward_player(enemy, world)


def _act_null_pointer(
    enemy: NullPointer, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Caster: ranged hit that adds 1 ``enemies_skip_turns`` to player."""
    player = world.player
    dist = chebyshev_distance(enemy.position, player.position)
    if dist <= 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} dereferenced you for {dmg} RAM"]
    if dist <= 4 and enemy.cooldown == 0:
        dmg = _scaled_damage(enemy.damage, mult)
        enemy_attack(player, enemy, damage=dmg)
        # Skip the player's next available turn (subtracts a cycle).
        player.cpu_cycles = 0
        enemy.cooldown = 3
        return [f"{enemy.name} nullified you (-{dmg} RAM, skipped cycle)"]
    if enemy.cooldown > 0:
        enemy.cooldown -= 1
    return _step_toward_player(enemy, world)


def _act_race_condition(
    enemy: RaceCondition, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Stalker: invisible until adjacent; full-strength bump attack."""
    player = world.player
    dist = chebyshev_distance(enemy.position, player.position)
    enemy.visible_to_player = dist <= 1
    if dist == 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} surfaced — {dmg} RAM"]
    if rng.random() < 0.4:
        return _wander(enemy, world, rng)
    return _step_toward_player(enemy, world)


def _act_daemonizer(enemy: Daemonizer, world: World, rng: random.Random, mult: float) -> list[str]:
    """Support: backs away from player, buffs nearby allies +1 dmg next turn."""
    player = world.player
    # Buff aura applied each turn (refreshed): allies within 2 tiles get +1 damage.
    buffed = 0
    for ally in world.enemies:
        if ally is enemy or not ally.is_alive:
            continue
        if chebyshev_distance(enemy.position, ally.position) <= 2:
            ally.damage = max(ally.damage, ally.damage)  # placeholder no-op
            ally.damage += 1 if not getattr(ally, "_daemonizer_buffed", False) else 0
            ally._daemonizer_buffed = True  # type: ignore[attr-defined]
            buffed += 1
    # Flee if too close.
    if chebyshev_distance(enemy.position, player.position) <= 2:
        # Step away.
        dx = enemy.position[0] - player.position[0]
        dy = enemy.position[1] - player.position[1]
        sx = 0 if dx == 0 else (1 if dx > 0 else -1)
        sy = 0 if dy == 0 else (1 if dy > 0 else -1)
        nx, ny = enemy.position[0] + sx, enemy.position[1] + sy
        if world.grid.is_walkable(nx, ny) and (nx, ny) not in world.occupied_positions():
            enemy.position = (nx, ny)
            return [f"{enemy.name} forks ({buffed} buffed)"] if buffed else []
    return [f"{enemy.name} buffs {buffed} allies"] if buffed else []


def _act_bruiser(enemy: Bruiser, world: World, rng: random.Random, mult: float) -> list[str]:
    """Slow, heavy hits. Moves every other turn."""
    player = world.player
    if chebyshev_distance(enemy.position, player.position) == 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} smashes for {dmg} RAM"]
    # Pseudo-slow: skip half the time.
    if rng.random() < 0.5:
        return []
    return _step_toward_player(enemy, world)


def _random_walkable(
    world: World, rng: random.Random, exclude: set[tuple[int, int]]
) -> tuple[int, int] | None:
    occupied = world.occupied_positions() | exclude
    candidates: list[tuple[int, int]] = []
    for x in range(world.grid.width):
        for y in range(world.grid.height):
            if not world.grid.is_walkable(x, y):
                continue
            if (x, y) in occupied:
                continue
            candidates.append((x, y))
    if not candidates:
        return None
    return rng.choice(candidates)


# ---------------------------------------------------------------------------
# Phase 9 boss AIs.
# ---------------------------------------------------------------------------


def _act_the_leak(enemy: TheLeak, world: World, rng: random.Random, mult: float) -> list[str]:
    """Heals each turn it isn't damaged; corrupts a random EMPTY tile."""
    log: list[str] = []
    if enemy.last_damaged_turn != world.turn_counter:
        if enemy.hp < enemy.max_hp:
            enemy.hp = min(enemy.max_hp, enemy.hp + 1)
        candidates = [
            (x, y)
            for x in range(world.grid.width)
            for y in range(world.grid.height)
            if world.grid.get(x, y) is TileType.EMPTY and (x, y) != world.player.position
        ]
        if candidates:
            tx, ty = rng.choice(candidates)
            world.grid.set(tx, ty, TileType.BAD_SECTOR)
            log.append(f"{enemy.name} corrupts ({tx},{ty})")
    if chebyshev_distance(enemy.position, world.player.position) <= 1:
        dmg = enemy_attack(world.player, enemy, damage=_scaled_damage(enemy.damage, mult))
        log.append(f"{enemy.name} oozes for {dmg} RAM")
        return log
    log.extend(_step_toward_player(enemy, world))
    return log


def _act_deadlock_twin(
    enemy: DeadlockTwin, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Plain-vanilla melee; the twin gimmick lives in the combat module."""
    if chebyshev_distance(enemy.position, world.player.position) <= 1:
        dmg = enemy_attack(world.player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} stalls you for {dmg} RAM"]
    return _step_toward_player(enemy, world)


def _act_rootkit_hydra(
    enemy: RootkitHydra, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Damage scales with remaining heads."""
    if chebyshev_distance(enemy.position, world.player.position) <= 1:
        scaled = _scaled_damage(enemy.damage * max(1, enemy.heads_remaining), mult)
        dmg = enemy_attack(world.player, enemy, damage=scaled)
        return [f"{enemy.name} bites with {enemy.heads_remaining} heads (-{dmg} RAM)"]
    return _step_toward_player(enemy, world)


def _act_buffer_overflow(
    enemy: BufferOverflowBoss, world: World, rng: random.Random, mult: float
) -> list[str]:
    """Every 3 turns drops `BAD_SECTOR` projectiles diagonally around the player."""
    enemy.fill_counter += 1
    log: list[str] = []
    if enemy.fill_counter % 3 == 0:
        px, py = world.player.position
        for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            tx, ty = px + dx, py + dy
            if world.grid.in_bounds(tx, ty) and world.grid.get(tx, ty) is TileType.EMPTY:
                world.grid.set(tx, ty, TileType.BAD_SECTOR)
        log.append(f"{enemy.name} writes data-blocks around you!")
    if chebyshev_distance(enemy.position, world.player.position) <= 1:
        dmg = enemy_attack(world.player, enemy, damage=_scaled_damage(enemy.damage, mult))
        log.append(f"{enemy.name} smashes for {dmg} RAM")
        return log
    log.extend(_step_toward_player(enemy, world))
    return log


def _act_zero_day(enemy: ZeroDayBoss, world: World, rng: random.Random, mult: float) -> list[str]:
    """Hard-hitting melee with occasional 2-tile lunge."""
    player = world.player
    dist = chebyshev_distance(enemy.position, player.position)
    if dist <= 1:
        dmg = enemy_attack(player, enemy, damage=_scaled_damage(enemy.damage, mult))
        return [f"{enemy.name} 0-days you for {dmg} RAM"]
    if dist <= 2 and rng.random() < 0.5:
        dmg = _scaled_damage(enemy.damage, mult)
        enemy_attack(player, enemy, damage=dmg)
        return [f"{enemy.name} chains an exploit ({dmg} RAM)"]
    return _step_toward_player(enemy, world)
