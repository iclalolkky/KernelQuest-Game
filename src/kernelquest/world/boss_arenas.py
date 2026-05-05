"""Phase 9 — boss arena loader.

Boss arenas are pre-authored sub-grids stored as JSON under
``data/boss_arenas/`` (next to this module). Each arena names the boss
species, its dimensions, the player spawn, the boss spawn, the exit, and
a ``tiles`` field encoded as a list of strings using the legend below.

If an arena file is missing the generator falls back to procedural rooms.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType

_LEGEND: Final[dict[str, TileType]] = {
    "#": TileType.SYSTEM_DATA,
    ".": TileType.EMPTY,
    "x": TileType.BAD_SECTOR,
    "E": TileType.EXIT,
}

ARENA_DIR: Final[Path] = Path(__file__).parent.parent / "data" / "boss_arenas"


@dataclass(frozen=True)
class BossArena:
    """Pre-authored boss arena."""

    key: str
    grid: MemoryGrid
    player_spawn: tuple[int, int]
    boss_spawn: tuple[int, int]
    exit_pos: tuple[int, int]


def _build_grid(rows: list[str]) -> MemoryGrid:
    height = len(rows)
    width = max(len(r) for r in rows) if rows else 0
    tiles: list[list[TileType]] = [
        [TileType.SYSTEM_DATA for _ in range(width)] for _ in range(height)
    ]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            tiles[y][x] = _LEGEND.get(ch, TileType.SYSTEM_DATA)
    return MemoryGrid(width=width, height=height, tiles=tiles)


def load_arena(boss_key: str) -> BossArena | None:
    """Load and parse the arena JSON for ``boss_key`` if it exists."""
    path = ARENA_DIR / f"{boss_key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):  # pragma: no cover - bad authoring
        return None
    rows = list(data.get("tiles", []))
    if not rows:
        return None
    grid = _build_grid(rows)
    return BossArena(
        key=str(data.get("key", boss_key)),
        grid=grid,
        player_spawn=tuple(data.get("spawn", [1, 1])),
        boss_spawn=tuple(data.get("boss_spawn", [1, 1])),
        exit_pos=tuple(data.get("exit", [1, 1])),
    )


__all__ = ["BossArena", "ARENA_DIR", "load_arena"]
