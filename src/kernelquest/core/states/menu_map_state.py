"""Phase 12.5 — Boot Map main menu state.

The Boot Map replaces the textual main menu with an interactive scene where
``init(0)`` (the protagonist) walks between labeled kiosks. Each kiosk maps to
the same engine action the legacy menu would have triggered (Launch, Manual,
Records, Shop, Settings, Quit).

Players can fall back to the classic list-style menu via Settings; that toggle
flips ``Settings.menu_layout`` between ``"map"`` and ``"classic"``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from kernelquest.core.config import WINDOW_HEIGHT, WINDOW_WIDTH
from kernelquest.core.state import GameState
from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


KioskAction = Callable[["GameEngine"], None]


@dataclass(frozen=True)
class Kiosk:
    """A single addressable kiosk in the Boot Map."""

    key: str
    label_key: str
    x: int  # centre x in window pixels
    action: KioskAction


def _go_launch(engine: GameEngine) -> None:
    engine._hub_tab_index = 0
    engine._state = GameState.LAUNCH_HUB


def _go_manual(engine: GameEngine) -> None:
    engine._hub_tab_index = 0
    engine._state = GameState.MANUAL_HUB


def _go_records(engine: GameEngine) -> None:
    engine._hub_tab_index = 0
    engine._state = GameState.RECORDS_HUB


def _go_shop(engine: GameEngine) -> None:
    engine._shop_index = 0
    engine._shop_message = None
    engine._state = GameState.SHOP


def _go_settings(engine: GameEngine) -> None:
    engine._settings_index = 0
    engine._state = GameState.SETTINGS


def _go_quit(engine: GameEngine) -> None:
    engine._state = GameState.QUIT_CONFIRM


# Six evenly-spaced kiosks across the window width.
_KIOSK_ROW_Y = WINDOW_HEIGHT // 2 + 80
_KIOSK_GAP = WINDOW_WIDTH // 7

KIOSKS: tuple[Kiosk, ...] = (
    Kiosk("launch", "menu.launch", _KIOSK_GAP * 1, _go_launch),
    Kiosk("manual", "menu.manual", _KIOSK_GAP * 2, _go_manual),
    Kiosk("records", "menu.records", _KIOSK_GAP * 3, _go_records),
    Kiosk("shop", "menu.shop", _KIOSK_GAP * 4, _go_shop),
    Kiosk("settings", "menu.settings", _KIOSK_GAP * 5, _go_settings),
    Kiosk("quit", "menu.quit", _KIOSK_GAP * 6, _go_quit),
)

#: Pixel speed of init(0) on the Boot Map (per-frame, fixed-step).
_AVATAR_SPEED: int = 6


class MenuMapStateHandler(GameStateHandler):
    """init(0) walks between kiosks; ENTER triggers the closest one."""

    name = "MENU_MAP"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            engine._state = GameState.QUIT_CONFIRM
            return
        if event.key in (pygame.K_LEFT, pygame.K_a):
            engine._menu_map_x = max(40, engine._menu_map_x - _AVATAR_SPEED * 8)
            engine._menu_map_facing = -1
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            engine._menu_map_x = min(WINDOW_WIDTH - 40, engine._menu_map_x + _AVATAR_SPEED * 8)
            engine._menu_map_facing = 1
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            kiosk = closest_kiosk(engine._menu_map_x)
            kiosk.action(engine)
        elif event.key == pygame.K_TAB:
            # Quick warp between kiosks.
            kiosk = next_kiosk(engine._menu_map_x)
            engine._menu_map_x = kiosk.x

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        # Music + render handled by UIManager.render_menu_map.
        if engine._sfx is not None and engine._sfx.current_track != "menu":
            engine._sfx.start_music("menu")
        focused = closest_kiosk(engine._menu_map_x)
        ui.render_menu_map(
            kiosks=KIOSKS,
            avatar_x=engine._menu_map_x,
            avatar_y=_KIOSK_ROW_Y - 6,
            focused_key=focused.key,
        )


def closest_kiosk(x: int) -> Kiosk:
    """Return the kiosk whose centre is nearest to ``x``."""
    return min(KIOSKS, key=lambda k: abs(k.x - x))


def next_kiosk(x: int) -> Kiosk:
    """Return the next kiosk to the right of ``x`` (wraps to the first)."""
    for k in KIOSKS:
        if k.x > x + 4:
            return k
    return KIOSKS[0]
