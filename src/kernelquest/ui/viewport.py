"""Viewport math: convert grid coordinates to screen pixels.

The viewport simply centers the grid in the available render area. Phase 1
grids (20x20) fit on screen, but this abstraction is in place for larger
sectors in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.core.config import TILE_SIZE


@dataclass(frozen=True)
class Viewport:
    """Translates grid coordinates to screen pixels."""

    origin_x: int
    origin_y: int
    tile_size: int = TILE_SIZE

    @classmethod
    def centered(
        cls,
        screen_width: int,
        screen_height: int,
        grid_width: int,
        grid_height: int,
        tile_size: int = TILE_SIZE,
    ) -> Viewport:
        ox = (screen_width - grid_width * tile_size) // 2
        oy = (screen_height - grid_height * tile_size) // 2
        return cls(origin_x=ox, origin_y=oy, tile_size=tile_size)

    def to_screen(self, x: int, y: int) -> tuple[int, int]:
        return (self.origin_x + x * self.tile_size, self.origin_y + y * self.tile_size)
