"""`MemoryGrid`: OS bellek sektörlerini temsil eden karelerin 2D dizisi."""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.core.config import GRID_HEIGHT, GRID_WIDTH
from kernelquest.world.tile import TileType


@dataclass
class MemoryGrid:
    """Bellek karelerinin dikdörtgen grid'i.

    Koordinatlar `(x, y)` ile `(0, 0)` sol üstte. İç temsil
    row-major: ``tiles[y][x]``.
    """

    width: int
    height: int
    tiles: list[list[TileType]]

    @classmethod
    def static_default(cls, width: int = GRID_WIDTH, height: int = GRID_HEIGHT) -> MemoryGrid:
        """Phase 1 tarafından kullanılan elle yazılmış statik düzen oluştur.

        Prosedürel üretim Phase 2'de gelir.
        """
        tiles: list[list[TileType]] = [
            [TileType.EMPTY for _ in range(width)] for _ in range(height)
        ]

        # Perimeter duvarları.
        for x in range(width):
            tiles[0][x] = TileType.SYSTEM_DATA
            tiles[height - 1][x] = TileType.SYSTEM_DATA
        for y in range(height):
            tiles[y][0] = TileType.SYSTEM_DATA
            tiles[y][width - 1] = TileType.SYSTEM_DATA

        # Bir avuç içi engeli.
        inner_walls = [(5, 5), (6, 5), (10, 10), (10, 11), (12, 7), (3, 14), (14, 3)]
        for x, y in inner_walls:
            if 0 < x < width - 1 and 0 < y < height - 1:
                tiles[y][x] = TileType.SYSTEM_DATA

        # Birkaçı kötü sektör (tuzağa düşüren).
        bad_sectors = [(8, 4), (15, 12)]
        for x, y in bad_sectors:
            if 0 < x < width - 1 and 0 < y < height - 1:
                tiles[y][x] = TileType.BAD_SECTOR

        return cls(width=width, height=height, tiles=tiles)

    # ----- sorgular -----

    def in_bounds(self, x: int, y: int) -> bool:
        """Koordinatın grid içinde olup olmadığını kontrol et."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> TileType:
        """`(x, y)` koordinatındaki kareyi döndür. OOB ise `IndexError` fırlatır."""
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) grid {self.width}x{self.height} için geçerli değil")
        return self.tiles[y][x]

    def set(self, x: int, y: int, tile: TileType) -> None:
        """`(x, y)` koordinatındaki kareyi değiştir."""
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) grid {self.width}x{self.height} için geçerli değil")
        self.tiles[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        """Koordinatın geçerli ve yürünebilir olup olmadığını kontrol et."""
        return self.in_bounds(x, y) and self.tiles[y][x].walkable
