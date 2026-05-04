"""Phase 5 — daily seed + ZombieProcess/SegFault behaviour + Player combo."""

from __future__ import annotations

import datetime
import random

from kernelquest.entities.malware import SegFault, ZombieProcess
from kernelquest.entities.player import Player
from kernelquest.world.daily import seed_for_date, today_iso, today_seed


def test_seed_for_date_is_deterministic() -> None:
    a = seed_for_date("2025-01-01")
    b = seed_for_date("2025-01-01")
    c = seed_for_date("2025-01-02")
    assert a == b
    assert a != c
    assert 0 <= a < 2**31


def test_today_helpers_round_trip() -> None:
    iso = today_iso()
    datetime.date.fromisoformat(iso)
    assert today_seed() == seed_for_date(iso)


def test_zombie_process_revives_once() -> None:
    z = ZombieProcess(position=(0, 0))
    z.take_damage(z.max_hp)
    assert z.is_alive
    assert z.has_revived is True
    z.take_damage(z.max_hp)
    assert not z.is_alive


def test_segfault_sets_pending_teleport_when_hit() -> None:
    boss = SegFault(position=(0, 0))
    boss.take_damage(1)
    assert boss.is_alive
    assert boss.pending_teleport is True


def test_player_combo_increments_and_clamps() -> None:
    p = Player(max_ram=100, ram=100)
    assert p.combo_multiplier == 1.0
    for _ in range(50):
        p.register_combo_event()
    assert p.combo_multiplier <= 5.0
    assert p.combo_multiplier > 1.0


def test_player_combo_breaks_on_damage() -> None:
    p = Player(max_ram=100, ram=100)
    p.register_combo_event()
    p.register_combo_event()
    assert p.combo_count == 2
    p.take_damage(5, source="test")
    assert p.combo_count == 0


def test_player_combo_idle_decay() -> None:
    p = Player(max_ram=100, ram=100)
    p.register_combo_event()
    p.tick_combo_idle()
    p.tick_combo_idle()
    p.tick_combo_idle()
    assert p.combo_count == 0


def test_zombie_process_reuses_random_walkable_indirectly() -> None:
    # Just sanity: ZombieProcess constructed with default fields.
    z = ZombieProcess(position=(1, 1))
    assert z.is_alive
    assert z.has_revived is False
    _ = random.Random(0)  # unused, smoke
