"""Inventory operations: pick-ups and item activation."""

from __future__ import annotations

from kernelquest.entities.items import get_item
from kernelquest.world.world import World


def pickup_item_at(world: World, position: tuple[int, int]) -> str | None:
    """If an item sits at `position`, move it into the player's cache.

    Returns a log message on pickup, or ``None`` if nothing happened (no item
    present, or the cache is full).
    """
    item_id = world.items.get(position)
    if item_id is None:
        return None
    if not world.player.add_to_cache(world.items[position]):
        return f"Cache dolu - {get_item(item_id).label} yerde kaldı"
    del world.items[position]
    return f"{get_item(item_id).label} toplandı"


def use_cache_slot(world: World, slot: int) -> str | None:
    """Activate the item in `slot` (0-indexed). Returns a log message or ``None``."""
    cache = world.player.cache
    if slot < 0 or slot >= len(cache):
        return None
    item_id = cache.pop(slot)
    item = get_item(item_id)
    return item.apply(world.player)
