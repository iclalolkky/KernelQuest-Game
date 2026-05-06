"""Görüş penceresi matematik: grid koordinatlarını ekran piksellerine çevir.

Görüş penceresi grid'i mevcut render alanında ortaya yerleştirir. Faz 1
grid'leri (20x20) ekrana sığar, ancak bu soyutlama sonraki fazlarda daha
büyük sektörler için yer tutmak üzere kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.core.config import TILE_SIZE


@dataclass(frozen=True)
class Viewport:
    """Grid koordinatlarını ekran piksellerine çevirir."""

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
