"""Phase 12.14 — Boss dev menu."""

from __future__ import annotations

from kernelquest.core import engine as eng
from kernelquest.entities.malware_registry import SPECIES


def test_boss_kind_in_polygon_kinds() -> None:
    assert "boss" in eng._POLYGON_KINDS


def test_polygon_boss_tab_lists_only_bosses() -> None:
    bosses = [s for s in SPECIES if s.is_boss]
    assert len(bosses) >= 1
    # Ensure every is_boss species has a registered factory.
    from kernelquest.entities.malware_registry import factory_for

    for sp in bosses:
        assert factory_for(sp.key) is not None, f"missing factory for boss {sp.key}"


def test_menu_options_default_excludes_boss_test(monkeypatch) -> None:
    monkeypatch.delenv("KQ_DEV", raising=False)
    assert "boss_test" not in eng._menu_options()


def test_menu_options_dev_flag_inserts_boss_test(monkeypatch) -> None:
    monkeypatch.setenv("KQ_DEV", "1")
    options = eng._menu_options()
    assert "boss_test" in options
    # Quit must remain the last entry.
    assert options[-1] == "quit"
