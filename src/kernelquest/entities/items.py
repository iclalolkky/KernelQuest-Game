"""Oyuncunun cache'ine toplanabilecek itemler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from kernelquest.core.config import (
    GC_HEAL_AMOUNT,
    OPTIMIZATION_CYCLES,
    SCAN_BOOST_TURNS,
)
from kernelquest.entities.player import Player


@dataclass(frozen=True)
class Item:
    """`Player.cache`'de depolanan tüketilebilir bir paket."""

    id: str
    label: str
    short_label: str
    apply: Callable[[Player], str]


def _apply_garbage_collector(player: Player) -> str:
    player.heal(GC_HEAL_AMOUNT)
    return f"GarbageCollector {GC_HEAL_AMOUNT} RAM geri yükledi"


def _apply_optimization(player: Player) -> str:
    player.grant_cycles(OPTIMIZATION_CYCLES)
    return f"Optimization +{OPTIMIZATION_CYCLES} CPU cycle verdi"


def _apply_scan_boost(player: Player) -> str:
    player.grant_scan_boost(SCAN_BOOST_TURNS)
    return f"ScanBoost tarama yarıçapını {SCAN_BOOST_TURNS} tur uzattı"


GARBAGE_COLLECTOR: Item = Item(
    id="gc",
    label="GarbageCollector",
    short_label="G",
    apply=_apply_garbage_collector,
)
OPTIMIZATION: Item = Item(
    id="opt",
    label="Optimization",
    short_label="O",
    apply=_apply_optimization,
)
SCAN_BOOST: Item = Item(
    id="scan",
    label="ScanBoost",
    short_label="S",
    apply=_apply_scan_boost,
)


_REGISTRY: dict[str, Item] = {
    GARBAGE_COLLECTOR.id: GARBAGE_COLLECTOR,
    OPTIMIZATION.id: OPTIMIZATION,
    SCAN_BOOST.id: SCAN_BOOST,
}

ALL_ITEM_IDS: tuple[str, ...] = tuple(_REGISTRY.keys())


def get_item(item_id: str) -> Item:
    """Bir `Item`'i kayıt kimliğine göre ara."""
    if item_id not in _REGISTRY:
        raise KeyError(f"unknown item id: {item_id!r}")
    return _REGISTRY[item_id]
