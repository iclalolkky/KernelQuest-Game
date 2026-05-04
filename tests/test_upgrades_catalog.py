"""Tests for the upgrade catalog (cost curve, applying bonuses)."""

from __future__ import annotations

import pytest

from kernelquest.data.upgrades_catalog import CATALOG, PlayerBonus, get_upgrade


def test_catalog_keys_unique() -> None:
    keys = [u.key for u in CATALOG]
    assert len(keys) == len(set(keys))


def test_get_upgrade_raises_for_unknown() -> None:
    with pytest.raises(KeyError):
        get_upgrade("nope")


def test_cost_curve_grows_then_caps() -> None:
    upgrade = CATALOG[0]
    cost_l0 = upgrade.cost_for_next_level(0)
    cost_l1 = upgrade.cost_for_next_level(1)
    assert cost_l0 is not None and cost_l1 is not None
    assert cost_l1 > cost_l0
    assert upgrade.cost_for_next_level(upgrade.max_level) is None


def test_apply_modifies_bonus() -> None:
    bonus = PlayerBonus()
    for upgrade in CATALOG:
        upgrade.apply(upgrade.max_level, bonus)
    # At least one of the bonus fields must be non-zero after applying every upgrade.
    assert any(
        v > 0
        for v in (
            bonus.bonus_ram,
            bonus.bonus_cycles,
            bonus.bonus_scan_radius,
            bonus.bonus_damage,
            bonus.bonus_cache,
        )
    )


def test_apply_is_additive_per_level() -> None:
    upgrade = next(u for u in CATALOG if u.key == "ram")
    a = PlayerBonus()
    upgrade.apply(1, a)
    b = PlayerBonus()
    upgrade.apply(2, b)
    assert b.bonus_ram == 2 * a.bonus_ram
