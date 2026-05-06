"""Oyuncu için görüş alanı hesaplama.

Chebyshev mesafesi + basit Bresenham segmentleri aracılığıyla görüş hattı kullanır.
Görüşü engelleyen kareler yürünemez karelerdir (`SYSTEM_DATA`).
"""

from __future__ import annotations

from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType

Position = tuple[int, int]


def compute_visible(grid: MemoryGrid, origin: Position, radius: int) -> set[Position]:
    """`origin`'dan `radius` içinde görünür pozisyonların kümesini döndür."""
    if radius < 0:
        return set()
    visible: set[Position] = {origin}
    ox, oy = origin
    for y in range(max(0, oy - radius), min(grid.height, oy + radius + 1)):
        for x in range(max(0, ox - radius), min(grid.width, ox + radius + 1)):
            if max(abs(x - ox), abs(y - oy)) > radius:
                continue
            if _line_of_sight(grid, origin, (x, y)):
                visible.add((x, y))
    return visible


def _line_of_sight(grid: MemoryGrid, a: Position, b: Position) -> bool:
    """`a` ve `b` arasında sıkı bir şekilde yer alan opak bir karenin olup olmadığını kontrol et."""
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    cx, cy = x0, y0
    while (cx, cy) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
        if (cx, cy) == (x1, y1):
            break
        if _blocks_sight(grid, cx, cy):
            return False
    return True


def _blocks_sight(grid: MemoryGrid, x: int, y: int) -> bool:
    if not (0 <= x < grid.width and 0 <= y < grid.height):
        return True
    return grid.get(x, y) is TileType.SYSTEM_DATA
