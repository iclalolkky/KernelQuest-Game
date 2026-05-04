"""Tests for the in-game console log."""

from __future__ import annotations

import pytest

from kernelquest.ui.console_log import ConsoleLog, LogLevel


def test_push_appends_entries() -> None:
    log = ConsoleLog(capacity=4)
    log.info("a")
    log.warn("b")
    entries = log.entries()
    assert [e.level for e in entries] == [LogLevel.INFO, LogLevel.WARN]
    assert [e.message for e in entries] == ["a", "b"]


def test_ring_buffer_drops_oldest() -> None:
    log = ConsoleLog(capacity=2)
    log.info("a")
    log.info("b")
    log.info("c")
    assert [e.message for e in log.entries()] == ["b", "c"]


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ConsoleLog(capacity=0)


def test_severity_helpers_set_level() -> None:
    log = ConsoleLog()
    log.error("oops")
    log.crit("doom")
    levels = [e.level for e in log.entries()]
    assert LogLevel.ERROR in levels
    assert LogLevel.CRIT in levels


def test_clear_empties_buffer() -> None:
    log = ConsoleLog()
    log.info("a")
    log.clear()
    assert log.entries() == []
