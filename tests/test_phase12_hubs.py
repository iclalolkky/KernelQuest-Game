"""Phase 12.6 — tabbed menu hubs (Manual / Launch / Records)."""

from __future__ import annotations

from kernelquest.core import engine as eng
from kernelquest.core.state import GameState
from kernelquest.core.states.hub_states import (
    LAUNCH_TABS,
    MANUAL_TABS,
    RECORDS_TABS,
    LaunchHubStateHandler,
    ManualHubStateHandler,
    RecordsHubStateHandler,
)
from kernelquest.core.states.registry import build_state_registry


def test_top_level_menu_is_consolidated() -> None:
    options = eng._MENU_OPTIONS
    assert "launch" in options
    assert "manual" in options
    assert "records" in options
    # Old verbose entries are removed from the top level.
    for legacy in ("new_run", "daily_run", "training", "howtoplay", "high_scores"):
        assert legacy not in options


def test_hub_handlers_registered() -> None:
    reg = build_state_registry()
    assert isinstance(reg[GameState.MANUAL_HUB], ManualHubStateHandler)
    assert isinstance(reg[GameState.LAUNCH_HUB], LaunchHubStateHandler)
    assert isinstance(reg[GameState.RECORDS_HUB], RecordsHubStateHandler)


def test_hub_tabs_have_actions() -> None:
    for tabs in (MANUAL_TABS, LAUNCH_TABS, RECORDS_TABS):
        assert len(tabs) >= 2
        for label, desc, action in tabs:
            assert label.startswith("menu.")
            assert desc.startswith("hub.")
            assert callable(action)
