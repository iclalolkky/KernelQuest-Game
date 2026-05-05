"""Phase 7 — narrative & lore unit tests."""

from __future__ import annotations

import pytest

from kernelquest.data.database import Database
from kernelquest.data.lore_catalog import (
    CATALOG,
    ENDING_FRAMES,
    INTRO_FRAMES,
    STACK_TRACE_LINES,
    all_keys,
    for_condition,
    get,
)
from kernelquest.data.repositories import LoreRepository
from kernelquest.ui.console_log import ConsoleLog


def test_catalog_keys_are_unique() -> None:
    keys = [e.key for e in CATALOG]
    assert len(keys) == len(set(keys))
    assert set(all_keys()) == set(keys)


def test_for_condition_lookup() -> None:
    entry = for_condition("first_boot")
    assert entry is not None
    assert entry.key == "boot_sequence"
    assert for_condition("definitely_not_real") is None


def test_get_lookup_by_key() -> None:
    entry = get("boot_sequence")
    assert entry is not None
    assert "init(0)" in entry.body
    with pytest.raises(KeyError):
        get("nonexistent")


def test_intro_and_ending_frames_present() -> None:
    assert len(INTRO_FRAMES) >= 3
    assert len(ENDING_FRAMES) >= 3
    assert all(frame.title for frame in INTRO_FRAMES)


def test_stack_trace_lines_have_voice_tags() -> None:
    assert len(STACK_TRACE_LINES) >= 5
    allowed = {"[KERNEL]", "[init]", "[THE_LEAK]", "[VENDOR]", "[CRON]"}
    for speaker, _line in STACK_TRACE_LINES:
        assert speaker in allowed


def test_lore_repository_unlock_is_idempotent() -> None:
    db = Database.in_memory()
    repo = LoreRepository(db)

    assert repo.unlocked_keys() == set()
    assert repo.unlock("boot_sequence") is True
    assert repo.unlock("boot_sequence") is False
    assert repo.is_unlocked("boot_sequence")
    assert "boot_sequence" in repo.unlocked_keys()


def test_console_voice_helpers_prefix_entries() -> None:
    log = ConsoleLog()
    log.kernel("system online")
    log.init("ready")
    log.leak("you are running out of time")
    log.vendor("buy more")
    log.cron("scheduled")
    bodies = [e.message for e in log.entries()]
    assert any(b.startswith("[KERNEL]") for b in bodies)
    assert any(b.startswith("[init]") for b in bodies)
    assert any(b.startswith("[THE_LEAK]") for b in bodies)
    assert any(b.startswith("[VENDOR]") for b in bodies)
    assert any(b.startswith("[CRON]") for b in bodies)
