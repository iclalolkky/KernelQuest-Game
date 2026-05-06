"""The `World` aggregate: grid + player + enemies + items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kernelquest.core.config import (
    DEFAULT_SCAN_RADIUS,
    SCAN_BOOST_RADIUS_BONUS,
)
from kernelquest.entities.malware import Malware
from kernelquest.systems.fov import compute_visible
from kernelquest.world.grid import MemoryGrid

if TYPE_CHECKING:
    from kernelquest.entities.player import Player


@dataclass
class World:
    """Mutable game world for a single sector.

    The engine creates a new ``World`` per sector (or run). Items live as a
    sparse mapping ``position -> item_id`` to keep lookups O(1).

    Tek bir sektör için değişken oyun dünyası, motor her sektör için yeni World oluşturur.
    """

    grid: MemoryGrid
    player: Player
    enemies: list[Malware] = field(default_factory=list)
    items: dict[tuple[int, int], str] = field(default_factory=dict)
    depth: int = 1
    visible: set[tuple[int, int]] = field(default_factory=set)
    explored: set[tuple[int, int]] = field(default_factory=set)

    # ----- queries -----

    def enemy_at(self, position: tuple[int, int]) -> Malware | None:
        for enemy in self.enemies:
            if enemy.is_alive and enemy.position == position:
                return enemy
        return None

    def is_blocked(self, position: tuple[int, int]) -> bool:
        """Return ``True`` if a tile is unwalkable or occupied."""
        x, y = position
        if not self.grid.is_walkable(x, y):
            return True
        if self.player.is_alive and self.player.position == position:
            return True
        return self.enemy_at(position) is not None

    def occupied_positions(self) -> set[tuple[int, int]]:
        """Positions other entities currently sit on (excluding the queried one)."""
        return {e.position for e in self.enemies if e.is_alive} | {self.player.position}

    # ----- mutations -----

    def remove_dead_enemies(self) -> list[Malware]:
        dead = [e for e in self.enemies if not e.is_alive]
        self.enemies = [e for e in self.enemies if e.is_alive]
        return dead

    def recompute_fov(self) -> None:
        """Recalculate the visible set from the player's current position."""
        # Oyuncunun mevcut pozisyonundan görünür kümesini yeniden hesaplar.
        radius = DEFAULT_SCAN_RADIUS + self.player.bonus_scan_radius
        if self.player.has_scan_boost:
            radius += SCAN_BOOST_RADIUS_BONUS
        self.visible = compute_visible(self.grid, self.player.position, radius)
        self.explored |= self.visible
