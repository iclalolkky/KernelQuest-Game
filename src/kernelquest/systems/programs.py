"""Program execution — runtime effects of active abilities."""

from __future__ import annotations

import random
from dataclasses import dataclass

from kernelquest.entities.malware import KernelPanic, Malware, SegFault
from kernelquest.entities.program import ProgramSlot
from kernelquest.systems.pathfinding import chebyshev_distance
from kernelquest.world.world import World


@dataclass(frozen=True)
class ProgramResult:
    """Outcome of attempting to execute a program."""

    success: bool
    message: str
    killed_enemy: Malware | None = None
    revealed_full_map: bool = False
    spawned_decoy_at: tuple[int, int] | None = None


def execute_program(world: World, slot_index: int, rng: random.Random) -> ProgramResult:
    """Run the program in `player.programs[slot_index]`. Pure-ish (mutates world)."""
    player = world.player
    if slot_index < 0 or slot_index >= len(player.programs):
        return ProgramResult(False, "No program in that slot.")
    slot = player.programs[slot_index]
    if not slot.ready:
        if slot.charges == 0:
            return ProgramResult(False, f"{slot.program.label}: out of charges.")
        return ProgramResult(False, f"{slot.program.label}: cooling down.")
    if player.cpu_cycles < slot.program.cycle_cost:
        return ProgramResult(False, f"{slot.program.label}: not enough cycles.")

    key = slot.program.key
    if key == "kill9":
        return _exec_kill9(world, slot)
    if key == "sudo":
        return _exec_sudo(player, slot)
    if key == "grep":
        return _exec_grep(world, slot)
    if key == "nice":
        return _exec_nice(world, slot)
    if key == "fork":
        return _exec_fork(world, slot, rng)
    return ProgramResult(False, f"{slot.program.label}: unimplemented.")


def _spend(player_cycles_holder: object, slot: ProgramSlot) -> None:
    # Helper to keep type-checking happy — we mutate the player directly.
    pass  # pragma: no cover


def _consume(world: World, slot: ProgramSlot) -> None:
    world.player.cpu_cycles = max(0, world.player.cpu_cycles - slot.program.cycle_cost)
    slot.consume()


def _exec_kill9(world: World, slot: ProgramSlot) -> ProgramResult:
    target: Malware | None = None
    px, py = world.player.position
    for enemy in world.enemies:
        if not enemy.is_alive:
            continue
        if isinstance(enemy, KernelPanic | SegFault):
            continue
        if chebyshev_distance(enemy.position, (px, py)) == 1:
            target = enemy
            break
    if target is None:
        return ProgramResult(False, "kill -9: no adjacent target.")
    target.take_damage(target.max_hp)
    if target.is_alive:
        # Could be a ZombieProcess that revived; finish the job.
        target.take_damage(target.max_hp)
    _consume(world, slot)
    return ProgramResult(True, f"kill -9: terminated {target.name}", killed_enemy=target)


def _exec_sudo(player, slot: ProgramSlot) -> ProgramResult:  # type: ignore[no-untyped-def]
    player.next_attack_multiplier = 3.0
    player.cpu_cycles = max(0, player.cpu_cycles - slot.program.cycle_cost)
    slot.consume()
    return ProgramResult(True, "sudo: next attack 3×.")


def _exec_grep(world: World, slot: ProgramSlot) -> ProgramResult:
    # Reveal the entire grid for this turn.
    full = {(x, y) for x in range(world.grid.width) for y in range(world.grid.height)}
    world.visible = full
    world.explored |= full
    _consume(world, slot)
    return ProgramResult(True, "grep: full sector revealed.", revealed_full_map=True)


def _exec_nice(world: World, slot: ProgramSlot) -> ProgramResult:
    world.player.enemies_skip_turns = max(world.player.enemies_skip_turns, 2)
    _consume(world, slot)
    return ProgramResult(True, "nice: enemies stalled for 2 turns.")


def _exec_fork(world: World, slot: ProgramSlot, rng: random.Random) -> ProgramResult:
    # Decoy spawns adjacent to the player; redirects the nearest enemy for one turn.
    px, py = world.player.position
    candidates = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = px + dx, py + dy
            if world.grid.is_walkable(nx, ny) and (nx, ny) not in world.occupied_positions():
                candidates.append((nx, ny))
    if not candidates:
        return ProgramResult(False, "fork(): no space to spawn decoy.")
    decoy = rng.choice(candidates)
    # Pull the closest enemy one tile toward the decoy.
    closest: Malware | None = None
    best = 999
    for enemy in world.enemies:
        if not enemy.is_alive:
            continue
        d = chebyshev_distance(enemy.position, decoy)
        if d < best:
            best = d
            closest = enemy
    if closest is not None:
        ex, ey = closest.position
        sx = 0 if decoy[0] == ex else (1 if decoy[0] > ex else -1)
        sy = 0 if decoy[1] == ey else (1 if decoy[1] > ey else -1)
        target = (ex + sx, ey + sy)
        if world.grid.is_walkable(*target) and target not in world.occupied_positions():
            closest.position = target
    _consume(world, slot)
    return ProgramResult(True, "fork(): decoy deployed.", spawned_decoy_at=decoy)


__all__ = ["ProgramResult", "execute_program"]
