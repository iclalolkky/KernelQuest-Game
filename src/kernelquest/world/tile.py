"""Tile type definitions for the memory grid."""

from __future__ import annotations

from enum import Enum, auto


class TileType(Enum):
    """A cell in the `MemoryGrid`."""

    EMPTY = auto()
    SYSTEM_DATA = auto()  # impassable wall
    BAD_SECTOR = auto()  # walkable but harmful
    EXIT = auto()  # descend to next sector

    @property
    def walkable(self) -> bool:
        """Whether an entity may step onto this tile."""
        return self is not TileType.SYSTEM_DATA
