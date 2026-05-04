"""The `MemoryGrid`: a 2D array of tiles representing OS memory sectors."""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.core.config import GRID_HEIGHT, GRID_WIDTH
from kernelquest.world.tile import TileType


@dataclass
class MemoryGrid:
    """A rectangular grid of memory tiles.

    Coordinates are `(x, y)` with `(0, 0)` at the top-left. The internal
    representation is row-major: ``tiles[y][x]``.
    """

    width: int
    height: int
    tiles: list[list[TileType]]

    @classmethod
    def static_default(cls, width: int = GRID_WIDTH, height: int = GRID_HEIGHT) -> MemoryGrid:
        """Build a hand-authored static layout used by Phase 1.

        Procedural generation lands in Phase 2.
        """
        tiles: list[list[TileType]] = [
            [TileType.EMPTY for _ in range(width)] for _ in range(height)
        ]

        # Perimeter walls.
        for x in range(width):
            tiles[0][x] = TileType.SYSTEM_DATA
            tiles[height - 1][x] = TileType.SYSTEM_DATA
        for y in range(height):
            tiles[y][0] = TileType.SYSTEM_DATA
            tiles[y][width - 1] = TileType.SYSTEM_DATA

        # A handful of inner obstacles.
        inner_walls = [(5, 5), (6, 5), (10, 10), (10, 11), (12, 7), (3, 14), (14, 3)]
        for x, y in inner_walls:
            if 0 < x < width - 1 and 0 < y < height - 1:
                tiles[y][x] = TileType.SYSTEM_DATA

        # A couple of bad sectors (traps).
        bad_sectors = [(8, 4), (15, 12)]
        for x, y in bad_sectors:
            if 0 < x < width - 1 and 0 < y < height - 1:
                tiles[y][x] = TileType.BAD_SECTOR

        return cls(width=width, height=height, tiles=tiles)

    # ----- queries -----

    def in_bounds(self, x: int, y: int) -> bool:
        """Return ``True`` if the coordinate is inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> TileType:
        """Return the tile at `(x, y)`. Raises `IndexError` if OOB."""
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) is out of bounds for grid {self.width}x{self.height}")
        return self.tiles[y][x]

    def set(self, x: int, y: int, tile: TileType) -> None:
        """Replace the tile at `(x, y)`."""
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) is out of bounds for grid {self.width}x{self.height}")
        self.tiles[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        """Return ``True`` if the coordinate is in-bounds and walkable."""
        return self.in_bounds(x, y) and self.tiles[y][x].walkable
