"""Meta-ilerleme yükseltmelerinin statik kataloğu.

Katalog doğruluk kaynağıdır; veritabanı sadece anahtar başına seviyeleri depolar.
Her yükseltme deterministik seviye → maliyet fonksiyonunu ortaya çıkarır ve motor
bunları yeni doğmuş bir `Player`'a toplamsal bonuslar olarak uygular.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Upgrade:
    """Satın alınabilir, kalıcı bir yükseltme."""

    key: str
    label: str
    description: str
    max_level: int
    base_cost: int
    cost_growth: int  # cost added per level
    apply: Callable[[int, PlayerBonus], None]

    def cost_for_next_level(self, current_level: int) -> int | None:
        """Sonraki seviyeyi satın alma maliyetini döndür, veya sınırdaysa `None`."""
        if current_level >= self.max_level:
            return None
        return self.base_cost + self.cost_growth * current_level


@dataclass
class PlayerBonus:
    """Çalıştırma başlangıcında uygulanan yükseltme efektleri için biriktirici."""

    bonus_ram: int = 0
    bonus_cycles: int = 0
    bonus_scan_radius: int = 0
    bonus_damage: int = 0
    bonus_cache: int = 0


def _ram_apply(level: int, bonus: PlayerBonus) -> None:
    bonus.bonus_ram += 10 * level


def _cycle_apply(level: int, bonus: PlayerBonus) -> None:
    bonus.bonus_cycles += level


def _scan_apply(level: int, bonus: PlayerBonus) -> None:
    bonus.bonus_scan_radius += level


def _damage_apply(level: int, bonus: PlayerBonus) -> None:
    bonus.bonus_damage += 2 * level


def _cache_apply(level: int, bonus: PlayerBonus) -> None:
    bonus.bonus_cache += level


CATALOG: tuple[Upgrade, ...] = (
    Upgrade(
        key="ram",
        label="+RAM",
        description="Her seviyede +10 azami RAM",
        max_level=5,
        base_cost=20,
        cost_growth=15,
        apply=_ram_apply,
    ),
    Upgrade(
        key="cycle",
        label="+Cycle",
        description="Her seviyede +1 başlangıç CPU cycle",
        max_level=3,
        base_cost=40,
        cost_growth=30,
        apply=_cycle_apply,
    ),
    Upgrade(
        key="scan",
        label="+Scan",
        description="Kalıcı tarama yarıçapı (her seviyede +1)",
        max_level=3,
        base_cost=30,
        cost_growth=25,
        apply=_scan_apply,
    ),
    Upgrade(
        key="damage",
        label="+Hasar",
        description="Her seviyede +2 temel hasar",
        max_level=3,
        base_cost=35,
        cost_growth=30,
        apply=_damage_apply,
    ),
    Upgrade(
        key="cache",
        label="+Cache",
        description="Her seviyede +1 cache yuvası",
        max_level=2,
        base_cost=50,
        cost_growth=50,
        apply=_cache_apply,
    ),
)


def get_upgrade(key: str) -> Upgrade:
    for upgrade in CATALOG:
        if upgrade.key == key:
            return upgrade
    raise KeyError(f"unknown upgrade: {key!r}")


__all__ = ["CATALOG", "PlayerBonus", "Upgrade", "get_upgrade"]
