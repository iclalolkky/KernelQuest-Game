"""Phase 10 — Interactive Tutorial Range: ``/dev/sandbox``.

Builds the Range world from a JSON spec and exposes the **Curriculum**
(L1–L8) with declarative lesson goals. Lessons are stateless: the engine
hands them the player + world after each player action and asks
``Lesson.is_complete(progress)``.

The Range never persists to the database; the engine guards every call to
:class:`ScoreRepository`/:class:`RunRepository` with the
``_is_tutorial_run`` / ``_in_tutorial_range`` flags.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from kernelquest.entities.player import Player
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

# ---------------------------------------------------------------------------
# Range arena
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RangeRoom:
    """A labelled rectangle within the Range arena."""

    key: str
    label: str
    x: int
    y: int
    w: int
    h: int

    def contains(self, position: tuple[int, int]) -> bool:
        px, py = position
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h


@dataclass(frozen=True)
class RangeArena:
    """Pre-authored Range arena loaded from JSON."""

    name: str
    grid: MemoryGrid
    rooms: tuple[RangeRoom, ...]
    spawn: tuple[int, int]
    exit_pos: tuple[int, int]


_RANGE_PATH: Final[Path] = Path(__file__).parent.parent / "data" / "tutorial" / "range.json"


def load_range_arena(path: Path | None = None) -> RangeArena:
    """Load the Range arena from disk (or use the bundled JSON)."""
    target = path or _RANGE_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))

    rooms = tuple(
        RangeRoom(
            key=str(r["key"]),
            label=str(r["label"]),
            x=int(r["x"]),
            y=int(r["y"]),
            w=int(r["w"]),
            h=int(r["h"]),
        )
        for r in raw["rooms"]
    )

    # Compute grid extent from rooms (+1 cell border).
    width = max(r.x + r.w for r in rooms) + 2
    height = max(r.y + r.h for r in rooms) + 2

    tiles: list[list[TileType]] = [
        [TileType.SYSTEM_DATA for _ in range(width)] for _ in range(height)
    ]
    grid = MemoryGrid(width=width, height=height, tiles=tiles)

    # Carve out each room as EMPTY.
    for room in rooms:
        for x in range(room.x, room.x + room.w):
            for y in range(room.y, room.y + room.h):
                grid.set(x, y, TileType.EMPTY)

    # Carve corridors connecting room centres horizontally then vertically.
    centres = [(r.x + r.w // 2, r.y + r.h // 2) for r in rooms]
    for i in range(len(centres) - 1):
        ax, ay = centres[i]
        bx, by = centres[i + 1]
        for x in range(min(ax, bx), max(ax, bx) + 1):
            grid.set(x, ay, TileType.EMPTY)
        for y in range(min(ay, by), max(ay, by) + 1):
            grid.set(bx, y, TileType.EMPTY)

    spawn = (int(raw["spawn"][0]), int(raw["spawn"][1]))
    exit_pos = (int(raw["exit"][0]), int(raw["exit"][1]))
    grid.set(exit_pos[0], exit_pos[1], TileType.EXIT)

    return RangeArena(
        name=str(raw.get("name", "/dev/sandbox")),
        grid=grid,
        rooms=rooms,
        spawn=spawn,
        exit_pos=exit_pos,
    )


def build_range_world(player: Player, arena: RangeArena) -> World:
    """Wrap the arena into a :class:`World` ready for rendering."""
    player.position = arena.spawn
    world = World(grid=arena.grid, player=player, depth=0)
    world.recompute_fov()
    return world


# ---------------------------------------------------------------------------
# Curriculum (L1–L8)
# ---------------------------------------------------------------------------


@dataclass
class LessonProgress:
    """Mutable bookkeeping the engine flips while the player plays."""

    moved_steps: int = 0
    enemies_killed: int = 0
    items_collected: int = 0
    programs_fired: dict[str, int] = field(default_factory=dict)
    daemons_swapped: int = 0
    patches_picked: int = 0
    inspect_opened: int = 0
    boss_phases_seen: int = 0

    def reset(self) -> None:
        self.moved_steps = 0
        self.enemies_killed = 0
        self.items_collected = 0
        self.programs_fired.clear()
        self.daemons_swapped = 0
        self.patches_picked = 0
        self.inspect_opened = 0
        self.boss_phases_seen = 0


@dataclass(frozen=True)
class Lesson:
    """A single curriculum step. Pure data; engine evaluates ``goal_field``."""

    key: str
    title: str
    body: str
    hint: str
    goal_field: str
    goal_target: int
    room: str  # which RangeRoom to highlight on the minimap

    def is_complete(self, progress: LessonProgress) -> bool:
        if self.goal_field == "programs_fired":
            # any program counts
            return sum(progress.programs_fired.values()) >= self.goal_target
        return int(getattr(progress, self.goal_field)) >= self.goal_target


CURRICULUM: Final[tuple[Lesson, ...]] = (
    Lesson(
        key="L1_boot",
        title="L1 — Boot",
        body=(
            "Move with WASD or arrows. The console (bottom-left) narrates every"
            " action. Walls are SYSTEM_DATA; you cannot pass through them."
        ),
        hint="Take 5 steps in any direction.",
        goal_field="moved_steps",
        goal_target=5,
        room="movement",
    ),
    Lesson(
        key="L2_combat",
        title="L2 — Combat",
        body=(
            "Walk INTO an enemy to bump-attack. Each swing costs 1 cycle and"
            " applies KINETIC damage. Watch the RAM bar in the HUD."
        ),
        hint="Defeat 1 training malware in the Combat Pit.",
        goal_field="enemies_killed",
        goal_target=1,
        room="combat",
    ),
    Lesson(
        key="L3_items",
        title="L3 — Items",
        body=(
            "Step onto an item to add it to your CACHE. Press 1/2/3 to use it."
            " GarbageCollector heals; Optimization grants cycles; ScanBoost"
            " widens your line-of-sight."
        ),
        hint="Pick up 1 item.",
        goal_field="items_collected",
        goal_target=1,
        room="items",
    ),
    Lesson(
        key="L4_programs",
        title="L4 — Programs",
        body=(
            "Programs are your active abilities. Press Q/E/R to fire your three"
            " loadout slots. Each costs cycles and goes on cooldown."
        ),
        hint="Fire any program once.",
        goal_field="programs_fired",
        goal_target=1,
        room="programs",
    ),
    Lesson(
        key="L5_daemons",
        title="L5 — Daemons",
        body=(
            "Daemons are passive modifiers. The Daemon Lounge contains podiums"
            " for swapping daemon loadouts. Tags overlap → you score a synergy."
        ),
        hint="Swap a daemon (press [T]).",
        goal_field="daemons_swapped",
        goal_target=1,
        room="daemons",
    ),
    Lesson(
        key="L6_patches",
        title="L6 — Patches",
        body=(
            "Patches are run modifiers. They add HUD chips and bend stats."
            " Picking one is permanent for the session — read the description."
        ),
        hint="Accept a Patch from the kiosk (press [P]).",
        goal_field="patches_picked",
        goal_target=1,
        room="daemons",
    ),
    Lesson(
        key="L7_recognition",
        title="L7 — Recognition",
        body=(
            "Press [I] to enter Inspect mode. It shows tier, kills logged,"
            " damage dealt, and weakness. Use [Tab] to cycle targets."
        ),
        hint="Open Inspect once.",
        goal_field="inspect_opened",
        goal_target=1,
        room="combat",
    ),
    Lesson(
        key="L8_boss_drill",
        title="L8 — Boss Drill",
        body=(
            "A training dummy boss with 1 HP per phase paces the Simulator."
            " Strike it to watch the phase telegraph fire. Bosses lock the EXIT"
            " — beat the drill to graduate."
        ),
        hint="Trigger 2 boss phase transitions.",
        goal_field="boss_phases_seen",
        goal_target=2,
        room="boss",
    ),
)


def lesson_by_key(key: str) -> Lesson:
    for lesson in CURRICULUM:
        if lesson.key == key:
            return lesson
    raise KeyError(f"unknown lesson: {key!r}")


__all__ = [
    "CURRICULUM",
    "Lesson",
    "LessonProgress",
    "RangeArena",
    "RangeRoom",
    "build_range_world",
    "lesson_by_key",
    "load_range_arena",
]
