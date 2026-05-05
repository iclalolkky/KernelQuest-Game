"""Unit tests for the State Pattern in :mod:`kernelquest.core.states`."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kernelquest.core.state import GameState
from kernelquest.core.states import (
    GameStateHandler,
    build_state_registry,
    get_state_handler,
)
from kernelquest.core.states.cinematic_states import (
    CodexStateHandler,
    EndingStateHandler,
    IntroStateHandler,
)
from kernelquest.core.states.game_over_state import (
    GameOverStateHandler,
    RunSummaryStateHandler,
)
from kernelquest.core.states.menu_states import (
    DailyBoardStateHandler,
    DistroSelectStateHandler,
    HighScoresStateHandler,
    HowToPlayStateHandler,
    MenuStateHandler,
    SettingsStateHandler,
    StatsStateHandler,
)
from kernelquest.core.states.playing_states import (
    BestiaryStateHandler,
    InspectStateHandler,
    MilestoneResultStateHandler,
    PatchPickStateHandler,
    PlayingStateHandler,
    StackTraceStateHandler,
    VendorStateHandler,
)
from kernelquest.core.states.shop_state import ShopStateHandler
from kernelquest.core.states.tutorial_state import (
    TutorialRangeStateHandler,
    TutorialStateHandler,
)

# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------


def test_registry_covers_every_non_quit_state() -> None:
    """Every :class:`GameState` except ``QUIT`` must have a handler."""
    registry = build_state_registry()
    expected = {s for s in GameState if s is not GameState.QUIT}
    assert set(registry.keys()) == expected


def test_quit_state_has_no_handler() -> None:
    """``QUIT`` is terminal — the engine loop exits before dispatch."""
    assert get_state_handler(GameState.QUIT) is None


def test_handlers_are_game_state_handler_subclasses() -> None:
    for handler in build_state_registry().values():
        assert isinstance(handler, GameStateHandler)


# ---------------------------------------------------------------------------
# Per-state mapping (sanity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "handler_cls"),
    [
        (GameState.MENU, MenuStateHandler),
        (GameState.SETTINGS, SettingsStateHandler),
        (GameState.HOWTOPLAY, HowToPlayStateHandler),
        (GameState.HIGH_SCORES, HighScoresStateHandler),
        (GameState.STATS, StatsStateHandler),
        (GameState.DAILY_BOARD, DailyBoardStateHandler),
        (GameState.DISTRO_SELECT, DistroSelectStateHandler),
        (GameState.PLAYING, PlayingStateHandler),
        (GameState.PATCH_PICK, PatchPickStateHandler),
        (GameState.STACK_TRACE, StackTraceStateHandler),
        (GameState.BESTIARY, BestiaryStateHandler),
        (GameState.INSPECT, InspectStateHandler),
        (GameState.MILESTONE_RESULT, MilestoneResultStateHandler),
        (GameState.VENDOR, VendorStateHandler),
        (GameState.SHOP, ShopStateHandler),
        (GameState.TUTORIAL, TutorialStateHandler),
        (GameState.TUTORIAL_RANGE, TutorialRangeStateHandler),
        (GameState.INTRO, IntroStateHandler),
        (GameState.ENDING, EndingStateHandler),
        (GameState.CODEX, CodexStateHandler),
        (GameState.GAME_OVER, GameOverStateHandler),
        (GameState.RUN_SUMMARY, RunSummaryStateHandler),
    ],
)
def test_state_to_handler_mapping(state: GameState, handler_cls: type[GameStateHandler]) -> None:
    handler = get_state_handler(state)
    assert isinstance(handler, handler_cls)


# ---------------------------------------------------------------------------
# Default no-op base behavior
# ---------------------------------------------------------------------------


def test_base_handler_default_hooks_are_noops() -> None:
    """Default ``enter``/``exit``/``update`` are inert."""
    handler = GameStateHandler()
    engine = MagicMock(name="engine")
    event = MagicMock(name="event")
    ui = MagicMock(name="ui")

    assert handler.enter(engine) is None
    assert handler.exit(engine) is None
    assert handler.handle_event(engine, event) is None
    assert handler.update(engine, 0.016) is None
    assert handler.render(engine, ui) is None

    # Default base must not touch the engine.
    assert engine.method_calls == []


# ---------------------------------------------------------------------------
# Delegation contract — handlers must forward to the correct engine method.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("handler_cls", "engine_method"),
    [
        (MenuStateHandler, "_handle_menu_key"),
        (SettingsStateHandler, "_handle_settings_key"),
        (HowToPlayStateHandler, "_handle_howtoplay_key"),
        (HighScoresStateHandler, "_handle_back_key"),
        (StatsStateHandler, "_handle_back_key"),
        (DailyBoardStateHandler, "_handle_back_key"),
        (DistroSelectStateHandler, "_handle_distro_select_key"),
        (PlayingStateHandler, "_handle_playing_key"),
        (PatchPickStateHandler, "_handle_patch_pick_key"),
        (StackTraceStateHandler, "_handle_stack_trace_key"),
        (BestiaryStateHandler, "_handle_bestiary_key"),
        (InspectStateHandler, "_handle_inspect_key"),
        (MilestoneResultStateHandler, "_handle_milestone_result_key"),
        (VendorStateHandler, "_handle_vendor_key"),
        (ShopStateHandler, "_handle_shop_key"),
        (TutorialStateHandler, "_handle_tutorial_key"),
        (TutorialRangeStateHandler, "_handle_range_key"),
        (IntroStateHandler, "_handle_cinematic_key"),
        (EndingStateHandler, "_handle_cinematic_key"),
        (CodexStateHandler, "_handle_codex_key"),
        (GameOverStateHandler, "_handle_game_over_key"),
        (RunSummaryStateHandler, "_handle_run_summary_key"),
    ],
)
def test_handle_event_delegates_to_engine(
    handler_cls: type[GameStateHandler], engine_method: str
) -> None:
    handler = handler_cls()
    engine = MagicMock(name="engine")
    event = MagicMock(name="event")
    handler.handle_event(engine, event)
    getattr(engine, engine_method).assert_called_once_with(event)


# ---------------------------------------------------------------------------
# Render delegates to UIManager (smoke checks for a representative few)
# ---------------------------------------------------------------------------


def test_menu_state_render_invokes_render_menu() -> None:
    handler = MenuStateHandler()
    engine = MagicMock(name="engine")
    engine._menu_index = 0
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    assert ui.render_menu.called


def test_settings_state_render_invokes_render_settings() -> None:
    handler = SettingsStateHandler()
    engine = MagicMock(name="engine")
    engine._settings_rows.return_value = []
    engine._settings_index = 0
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    ui.render_settings.assert_called_once()


def test_milestone_result_render_invokes_render_milestone_result() -> None:
    handler = MilestoneResultStateHandler()
    engine = MagicMock(name="engine")
    engine._milestone_result_panel = {"foo": 1}
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    ui.render_milestone_result.assert_called_once_with({"foo": 1})


def test_playing_state_render_skips_when_world_is_none() -> None:
    handler = PlayingStateHandler()
    engine = MagicMock(name="engine")
    engine._world = None
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    assert not ui.method_calls


def test_inspect_state_render_skips_when_world_is_none() -> None:
    handler = InspectStateHandler()
    engine = MagicMock(name="engine")
    engine._world = None
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    assert not ui.method_calls


def test_game_over_render_skips_when_world_is_none() -> None:
    handler = GameOverStateHandler()
    engine = MagicMock(name="engine")
    engine._world = None
    ui = MagicMock(name="ui")
    handler.render(engine, ui)
    assert not ui.render_game_over.called


# ---------------------------------------------------------------------------
# Public engine helpers exposed for state handlers
# ---------------------------------------------------------------------------


def test_engine_exposes_public_helpers_for_handlers() -> None:
    """``GameEngine`` advertises ``start_new_run`` / ``reset_to_menu`` etc."""
    from kernelquest.core.engine import GameEngine

    for name in ("start_new_run", "reset_to_menu", "compute_bonus"):
        assert callable(getattr(GameEngine, name)), f"missing helper: {name}"
