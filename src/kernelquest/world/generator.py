"""Procedural sector generator using a rooms-and-corridors algorithm.

The generator is fully deterministic given a `random.Random` seed and the
target depth. Reachability is guaranteed by carving corridors between every
consecutive room.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from kernelquest.core.config import (
    BAD_SECTORS_PER_LEVEL,
    ENEMIES_BASE_COUNT,
    GRID_HEIGHT,
    GRID_WIDTH,
    ITEMS_BASE_COUNT,
    KERNEL_PANIC_DEPTH,
    PLAYER_START_POSITION,
    ROOM_MAX_ATTEMPTS,
    ROOM_MAX_SIZE,
    ROOM_MIN_SIZE,
)
from kernelquest.entities.affix import apply_at_spawn, roll_affixes
from kernelquest.entities.items import ALL_ITEM_IDS
from kernelquest.entities.malware import (
    Bruiser,
    BufferOverflowBoss,
    Daemonizer,
    DeadlockTwin,
    ForkBomb,
    IndexError_,
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
from kernelquest.entities.player import Player
from kernelquest.world.boss_arenas import BossArena, load_arena
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World


@dataclass(frozen=True)
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def overlaps(self, other: Room) -> bool:
        return (
            self.x <= other.x + other.w
            and self.x + self.w >= other.x
            and self.y <= other.y + other.h
            and self.y + self.h >= other.y
        )

    def inner_tiles(self) -> list[tuple[int, int]]:
        return [
            (x, y) for x in range(self.x, self.x + self.w) for y in range(self.y, self.y + self.h)
        ]


def generate_world(
    *,
    player: Player,
    depth: int,
    rng: random.Random,
    width: int = GRID_WIDTH,
    height: int = GRID_HEIGHT,
    extra_enemies: int = 0,
) -> World:
    """Build a fresh `World` for the given depth.

    The same `(seed, depth)` pair always yields the same world. ``extra_enemies``
    is added to the base spawn count (used by Patch Notes like ``Fragmented``).
    """
    grid = _all_walls(width, height)
    rooms = _carve_rooms(grid, rng, width, height)
    if not rooms:  # pragma: no cover - vanishingly unlikely with default settings
        raise RuntimeError("Level generator failed to place any rooms")

    _connect_rooms(grid, rooms)
    _scatter_bad_sectors(grid, rooms, rng)

    # Phase 9 — boss arena override.
    boss_key = _which_boss(depth)
    if boss_key is not None:
        arena = load_arena(boss_key)
        if arena is not None:
            return _build_boss_world(player, depth, rng, arena, boss_key)

    # Place the player in the first room.
    spawn = rooms[0].center
    player.position = spawn

    # Drop the exit in the farthest room from the player.
    exit_pos = rooms[-1].center
    if exit_pos == spawn and len(rooms) > 1:
        exit_pos = rooms[-2].center
    grid.set(*exit_pos, TileType.EXIT)

    enemies = _spawn_enemies(rooms, rng, depth, exclude={spawn, exit_pos}, extra=extra_enemies)
    item_exclude = {spawn, exit_pos, *(e.position for e in enemies)}
    items = _spawn_items(rooms, rng, depth, exclude=item_exclude)

    return World(grid=grid, player=player, enemies=enemies, items=items, depth=depth)


def generate_starting_world(
    *,
    seed: int | None = None,
    width: int = GRID_WIDTH,
    height: int = GRID_HEIGHT,
) -> tuple[World, random.Random]:
    """Convenience helper that builds a fresh `Player`, RNG, and depth-1 world."""
    rng = random.Random(seed)
    player = Player(position=PLAYER_START_POSITION)
    world = generate_world(player=player, depth=1, rng=rng, width=width, height=height)
    return world, rng


# ----- internals -----


def _all_walls(width: int, height: int) -> MemoryGrid:
    tiles: list[list[TileType]] = [
        [TileType.SYSTEM_DATA for _ in range(width)] for _ in range(height)
    ]
    return MemoryGrid(width=width, height=height, tiles=tiles)


def _carve_rooms(grid: MemoryGrid, rng: random.Random, width: int, height: int) -> list[Room]:
    rooms: list[Room] = []
    for _ in range(ROOM_MAX_ATTEMPTS):
        w = rng.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = rng.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        x = rng.randint(1, width - w - 1)
        y = rng.randint(1, height - h - 1)
        candidate = Room(x=x, y=y, w=w, h=h)
        if any(candidate.overlaps(r) for r in rooms):
            continue
        for tx, ty in candidate.inner_tiles():
            grid.set(tx, ty, TileType.EMPTY)
        rooms.append(candidate)
    return rooms


def _connect_rooms(grid: MemoryGrid, rooms: list[Room]) -> None:
    for previous, current in zip(rooms, rooms[1:], strict=False):
        x1, y1 = previous.center
        x2, y2 = current.center
        # L-shaped corridor: horizontal then vertical.
        for x in range(min(x1, x2), max(x1, x2) + 1):
            grid.set(x, y1, TileType.EMPTY)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            grid.set(x2, y, TileType.EMPTY)


def _scatter_bad_sectors(grid: MemoryGrid, rooms: list[Room], rng: random.Random) -> None:
    candidates: list[tuple[int, int]] = []
    for room in rooms[1:]:  # skip spawn room
        candidates.extend(room.inner_tiles())
    rng.shuffle(candidates)
    placed = 0
    for pos in candidates:
        if placed >= BAD_SECTORS_PER_LEVEL:
            break
        if grid.get(*pos) is TileType.EMPTY:
            grid.set(*pos, TileType.BAD_SECTOR)
            placed += 1


def _spawn_enemies(
    rooms: list[Room],
    rng: random.Random,
    depth: int,
    exclude: set[tuple[int, int]],
    extra: int = 0,
) -> list[Malware]:
    enemies: list[Malware] = []
    target_count = ENEMIES_BASE_COUNT + depth + max(0, extra)
    occupied: set[tuple[int, int]] = set(exclude)

    candidate_positions: list[tuple[int, int]] = []
    for room in rooms[1:]:
        candidate_positions.extend(room.inner_tiles())
    rng.shuffle(candidate_positions)

    # Phase 9 — boss every KERNEL_PANIC_DEPTH levels via the boss wheel.
    boss_key = _which_boss(depth)
    if boss_key is not None:
        for pos in candidate_positions:
            if pos in occupied:
                continue
            if boss_key == "deadlock_twin":
                # Deadlock spawns paired; pick a second position too.
                second = _second_open_position(candidate_positions, occupied | {pos})
                if second is None:
                    second = pos  # degenerate
                twin_a = DeadlockTwin(position=pos, twin_id=0)
                twin_b = DeadlockTwin(position=second, twin_id=1)
                for tw in (twin_a, twin_b):
                    tw.affixes.keys = roll_affixes(rng, depth=depth, is_boss=True)
                    apply_at_spawn(tw, rng)
                enemies.extend([twin_a, twin_b])
                occupied.add(pos)
                occupied.add(second)
                break
            boss = _boss_factory(boss_key, pos)
            boss.affixes.keys = roll_affixes(rng, depth=depth, is_boss=True)
            apply_at_spawn(boss, rng)
            enemies.append(boss)
            occupied.add(pos)
            break

    for pos in candidate_positions:
        if len(enemies) >= target_count:
            break
        if pos in occupied:
            continue
        enemy = _pick_species(rng, depth, pos)
        # Phase 8 — roll & apply affixes.
        enemy.affixes.keys = roll_affixes(rng, depth=depth, is_boss=enemy.is_boss)
        apply_at_spawn(enemy, rng)
        enemies.append(enemy)
        occupied.add(pos)
    return enemies


def _pick_species(rng: random.Random, depth: int, pos: tuple[int, int]) -> Malware:
    """Phase 8 — depth-weighted enemy roller covering the full registry."""
    pool: list[tuple[float, type[Malware]]] = [(1.0, SyntaxError_)]
    if depth >= 2:
        pool.append((0.55, LogicBomb))
    if depth >= 3:
        pool.append((0.50, RuntimeError_))
        pool.append((0.30, IndexError_))
        pool.append((0.30, StackOverflow))
    if depth >= 4:
        pool.append((0.45, ZombieProcess))
        pool.append((0.30, NullPointer))
        pool.append((0.25, Daemonizer))
        pool.append((0.25, RaceCondition))
    if depth >= 5:
        pool.append((0.30, ForkBomb))
        pool.append((0.25, Bruiser))
    total = sum(weight for weight, _ in pool)
    roll = rng.random() * total
    cursor = 0.0
    for weight, cls in pool:
        cursor += weight
        if roll <= cursor:
            return cls(position=pos)
    return SyntaxError_(position=pos)


def _spawn_items(
    rooms: list[Room],
    rng: random.Random,
    depth: int,
    exclude: set[tuple[int, int]],
) -> dict[tuple[int, int], str]:
    items: dict[tuple[int, int], str] = {}
    target_count = ITEMS_BASE_COUNT + depth // 2

    candidate_positions: list[tuple[int, int]] = []
    for room in rooms:
        candidate_positions.extend(room.inner_tiles())
    rng.shuffle(candidate_positions)

    occupied: set[tuple[int, int]] = set(exclude)
    for pos in candidate_positions:
        if len(items) >= target_count:
            break
        if pos in occupied:
            continue
        items[pos] = rng.choice(ALL_ITEM_IDS)
        occupied.add(pos)
    return items


# ---------------------------------------------------------------------------
# Phase 9 — boss wheel + arena helpers.
# ---------------------------------------------------------------------------


_BOSS_WHEEL: tuple[str, ...] = (
    "kernel_panic",
    "segfault",
    "buffer_overflow",
    "rootkit_hydra",
    "deadlock_twin",
    "the_leak",
)


def _which_boss(depth: int) -> str | None:
    """Return the boss species_key scheduled for ``depth`` (or ``None``)."""
    if depth < KERNEL_PANIC_DEPTH or depth % KERNEL_PANIC_DEPTH != 0:
        return None
    idx = (depth // KERNEL_PANIC_DEPTH - 1) % len(_BOSS_WHEEL)
    return _BOSS_WHEEL[idx]


def _boss_factory(key: str, pos: tuple[int, int]) -> Malware:
    if key == "segfault":
        return SegFault(position=pos)
    if key == "the_leak":
        return TheLeak(position=pos)
    if key == "rootkit_hydra":
        return RootkitHydra(position=pos)
    if key == "buffer_overflow":
        return BufferOverflowBoss(position=pos)
    if key == "deadlock_twin":
        return DeadlockTwin(position=pos)
    if key == "zero_day":
        return ZeroDayBoss(position=pos)
    return KernelPanic(position=pos)


def _second_open_position(
    candidates: list[tuple[int, int]], occupied: set[tuple[int, int]]
) -> tuple[int, int] | None:
    for cand in candidates:
        if cand not in occupied:
            return cand
    return None


def _build_boss_world(
    player: Player,
    depth: int,
    rng: random.Random,
    arena: BossArena,
    boss_key: str,
) -> World:
    """Lay the player + boss into a pre-authored arena grid."""
    grid = arena.grid
    player.position = arena.player_spawn
    grid.set(*arena.exit_pos, TileType.EXIT)
    enemies: list[Malware] = []
    pos = arena.boss_spawn
    if boss_key == "deadlock_twin":
        # Place the second twin on the opposite axis.
        sx, sy = pos
        second = (max(1, sx - 2), sy)
        twin_a = DeadlockTwin(position=pos, twin_id=0)
        twin_b = DeadlockTwin(position=second, twin_id=1)
        for tw in (twin_a, twin_b):
            tw.affixes.keys = roll_affixes(rng, depth=depth, is_boss=True)
            apply_at_spawn(tw, rng)
        enemies.extend([twin_a, twin_b])
    else:
        boss = _boss_factory(boss_key, pos)
        boss.affixes.keys = roll_affixes(rng, depth=depth, is_boss=True)
        apply_at_spawn(boss, rng)
        enemies.append(boss)
    return World(grid=grid, player=player, enemies=enemies, items={}, depth=depth)
