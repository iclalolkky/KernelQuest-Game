"""Handlers for tutorial states (linear TUTORIAL and free-form TUTORIAL_RANGE)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler
from kernelquest.world.tutorial_range import CURRICULUM

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager

_POLYGON_KINDS: tuple[str, ...] = ("enemy", "item", "program", "daemon", "patch")


class TutorialStateHandler(GameStateHandler):
    name = "TUTORIAL"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_tutorial_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        steps = engine._TUTORIAL_STEPS
        ui.render_tutorial(
            steps[min(engine._tutorial_step, len(steps) - 1)],
            engine._tutorial_step + 1,
            len(steps),
        )
        if engine._settings.crt_effect:
            ui.render_scanlines()


class TutorialRangeStateHandler(GameStateHandler):
    """Free-form lesson range with the polygon overlay."""

    name = "TUTORIAL_RANGE"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        # ``_handle_range_key`` already forwards to ``_handle_polygon_key``
        # when the polygon overlay is open, so we only need a single entry
        # point here.
        engine._handle_range_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        world = engine._world
        if world is None:
            return
        ui.clear()
        ui.render_world(
            world,
            engine._viewport,
            shake=engine._shake,
            particles=engine._particles,
        )
        ui.render_floating_text(engine._floats, engine._viewport)
        ui.render_hud(
            world.player,
            sector=0,
            world=world,
            patches=[p.label for p in engine._patches.selected],
        )
        ui.render_console(engine._console)
        current = engine._current_lesson()
        ui.render_range_lesson_panel(
            lesson=current,
            lesson_index=engine._lesson_index,
            total_lessons=len(CURRICULUM),
            progress=engine._lesson_progress,
            completed=engine._range_completed,
        )
        if engine._polygon_open:
            ui.render_polygon_overlay(
                kind=_POLYGON_KINDS[engine._polygon_kind_index],
                items=engine._polygon_current_entries(),
                selected=engine._polygon_item_index,
                god_mode=engine._range_god_mode,
                infinite_cycles=engine._range_infinite_cycles,
                full_fov=engine._range_full_fov,
            )
        if engine._settings.crt_effect:
            ui.render_scanlines()
