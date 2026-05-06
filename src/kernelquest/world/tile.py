"""Bellek grid'i için kare türü tanımları."""

from __future__ import annotations

from enum import Enum, auto


class TileType(Enum):
    """`MemoryGrid`'de bir hücre."""

    EMPTY = auto()
    SYSTEM_DATA = auto()  # geçilemez duvar
    BAD_SECTOR = auto()  # geçilebilir ama zararlı
    EXIT = auto()  # bir sonraki sektöre in

    @property
    def walkable(self) -> bool:
        """Bir varlığın bu kareye adım atıp atamayacağı."""
        return self is not TileType.SYSTEM_DATA
