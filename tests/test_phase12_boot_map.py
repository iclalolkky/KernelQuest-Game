"""Phase 12.5 — Boot Map main menu."""

from __future__ import annotations

from kernelquest.core.settings import Settings
from kernelquest.core.state import GameState
from kernelquest.core.states.menu_map_state import (
    KIOSKS,
    MenuMapStateHandler,
    closest_kiosk,
    next_kiosk,
)
from kernelquest.core.states.registry import build_state_registry


def test_settings_default_to_boot_map() -> None:
    assert Settings().menu_layout == "map"


def test_toggle_menu_layout_round_trip() -> None:
    s = Settings()
    s.toggle_menu_layout()
    assert s.menu_layout == "classic"
    s.toggle_menu_layout()
    assert s.menu_layout == "map"


def test_kiosks_have_unique_keys_and_actions() -> None:
    keys = [k.key for k in KIOSKS]
    assert len(keys) == len(set(keys))
    for k in KIOSKS:
        assert callable(k.action)
        assert k.label_key.startswith("menu.")


def test_closest_kiosk_picks_nearest() -> None:
    assert closest_kiosk(KIOSKS[0].x).key == KIOSKS[0].key
    mid = (KIOSKS[2].x + KIOSKS[3].x) // 2
    chosen = closest_kiosk(mid - 1)
    assert chosen.key == KIOSKS[2].key


def test_next_kiosk_wraps() -> None:
    last = KIOSKS[-1]
    assert next_kiosk(last.x + 100).key == KIOSKS[0].key


def test_handler_registered_for_menu_map() -> None:
    reg = build_state_registry()
    assert isinstance(reg[GameState.MENU_MAP], MenuMapStateHandler)
