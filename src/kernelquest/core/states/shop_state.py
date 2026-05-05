"""Handler for the meta-progression shop state."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager


class ShopStateHandler(GameStateHandler):
    name = "SHOP"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_shop_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_shop(
            engine._fetch_bits(),
            engine._shop_rows(),
            engine._shop_index,
            engine._shop_message,
        )
