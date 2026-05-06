"""Phase 12.6 — tab-grouped main-menu hubs (Manual / Launch / Records).

Each hub is a stateless handler that draws a tab strip via
:meth:`UIManager.render_tabbed_hub` and dispatches to the matching engine
method when ENTER is pressed. ESC bounces back to ``GameState.MENU``.

Tabs are described as ``(label_key, description_key, action)`` triples; the
action is a unary callable receiving the engine.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from kernelquest.core.state import GameState
from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


HubAction = Callable[["GameEngine"], None]


def _go_high_scores(engine: GameEngine) -> None:
    engine._state = GameState.HIGH_SCORES


def _go_daily_board(engine: GameEngine) -> None:
    engine._state = GameState.DAILY_BOARD


def _go_stats(engine: GameEngine) -> None:
    engine._state = GameState.STATS


def _go_bestiary(engine: GameEngine) -> None:
    engine._state = GameState.BESTIARY
    engine._bestiary_scroll = 0


# Each hub: (title_key, [(label_key, desc_key, action)])
MANUAL_TABS: tuple[tuple[str, str, HubAction], ...] = (
    ("menu.training", "hub.manual.training_desc", lambda e: e._start_tutorial_range()),
    ("menu.howtoplay", "hub.manual.howtoplay_desc", lambda e: e._start_tutorial()),
    ("menu.codex", "hub.manual.codex_desc", lambda e: e._open_codex()),
)

LAUNCH_TABS: tuple[tuple[str, str, HubAction], ...] = (
    ("menu.new_run", "hub.launch.new_desc", lambda e: e._open_distro_select(daily=False)),
    ("menu.daily_run", "hub.launch.daily_desc", lambda e: e._open_distro_select(daily=True)),
)

RECORDS_TABS: tuple[tuple[str, str, HubAction], ...] = (
    ("menu.high_scores", "hub.records.high_desc", _go_high_scores),
    ("menu.daily_board", "hub.records.daily_desc", _go_daily_board),
    ("menu.stats", "hub.records.stats_desc", _go_stats),
    ("menu.bestiary", "hub.records.bestiary_desc", _go_bestiary),
)


class _HubBase(GameStateHandler):
    """Shared event/render logic for tabbed sub-menus."""

    title_key: str = ""
    tabs: tuple[tuple[str, str, HubAction], ...] = ()
    index_attr: str = "_hub_tab_index"

    def _index(self, engine: GameEngine) -> int:
        return getattr(engine, self.index_attr, 0)

    def _set_index(self, engine: GameEngine, value: int) -> None:
        setattr(engine, self.index_attr, value % max(1, len(self.tabs)))

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            engine._state = GameState.MENU
            return
        n = len(self.tabs)
        if n == 0:
            return
        idx = self._index(engine)
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._set_index(engine, idx - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
            self._set_index(engine, idx + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            _, _, action = self.tabs[idx]
            action(engine)
        elif pygame.K_1 <= event.key <= pygame.K_9:
            digit = event.key - pygame.K_1
            if digit < n:
                self._set_index(engine, digit)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        from kernelquest.ui.i18n import t

        labels = [t(label) for (label, _, _) in self.tabs]
        descs = [t(desc) for (_, desc, _) in self.tabs]
        ui.render_tabbed_hub(
            title=t(self.title_key),
            tabs=labels,
            selected=self._index(engine),
            descriptions=descs,
        )


class ManualHubStateHandler(_HubBase):
    name = "MANUAL_HUB"
    title_key = "hub.manual.title"
    tabs = MANUAL_TABS


class LaunchHubStateHandler(_HubBase):
    name = "LAUNCH_HUB"
    title_key = "hub.launch.title"
    tabs = LAUNCH_TABS


class RecordsHubStateHandler(_HubBase):
    name = "RECORDS_HUB"
    title_key = "hub.records.title"
    tabs = RECORDS_TABS
