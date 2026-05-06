"""Handlers for in-run gameplay states.

PLAYING is the main grid view; PATCH_PICK / STACK_TRACE / BESTIARY / INSPECT /
MILESTONE_RESULT / VENDOR are overlays or inline modals reachable from the
running game loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core.states.base import GameStateHandler

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine
    from kernelquest.ui.renderer import UIManager

# Phase 12.4 — keybind hints rendered in the dedicated bottom bar (so they
# never overlap the play area or the side HUD).
_PLAYING_HINTS: list[str] = [
    "[↑/↓/←/→] move/attack",
    "[space] wait",
    "[Q/E/R] programs",
    "[1..9] cache",
    "[I] inspect",
    "[?] help",
    "[esc] menu",
]
_INSPECT_HINTS: list[str] = [
    "[↑/↓/←/→] move cursor",
    "[enter] reveal",
    "[esc] back",
]


class PlayingStateHandler(GameStateHandler):
    """Active grid view: world, HUD, console."""

    name = "PLAYING"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_playing_key(event)

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
            sector=world.player.depth_reached,
            world=world,
            patches=[p.label for p in engine._patches.selected],
        )
        # Phase 12.7 — RELEASE ladder strip below the HUD column.
        from kernelquest.core.config import WINDOW_WIDTH

        ui.render_ladder_strip(engine._run_progress, (WINDOW_WIDTH - 270, 470))
        ui.render_bottom_bar(_PLAYING_HINTS)
        if engine._show_ladder_overlay:
            ui.render_ladder_overlay(engine._run_progress)
        if engine._boss_active:
            boss = world.living_boss()
            if boss is not None:
                ui.render_boss_hp_bar(boss)
            if engine._boss_banner_ttl > 0.0:
                ui.render_boss_banner(
                    boss.crash_label if boss is not None else "BOSS",
                    engine._boss_banner_ttl / 2.5,
                )
            ui.render_glitch_overlay(max(0.25, engine._glitch_intensity))
        elif engine._glitch_intensity > 0.0:
            ui.render_glitch_overlay(engine._glitch_intensity)
        # Phase 12.9 — overlay the phase-shift cinematic on top of everything
        # except the console so the kernel line remains legible.
        if engine._phase_shift_ttl > 0.0:
            ui.render_phase_shift(engine._phase_shift_ttl)
        ui.render_console(engine._console)
        if engine._show_help_overlay:
            ui.render_help_overlay()
        if engine._settings.crt_effect:
            ui.render_scanlines()


class PatchPickStateHandler(GameStateHandler):
    name = "PATCH_PICK"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_patch_pick_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_patch_pick(
            [(p.label, p.description) for p in engine._patch_choices],
            engine._patch_pick_index,
        )


class StackTraceStateHandler(GameStateHandler):
    name = "STACK_TRACE"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_stack_trace_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        depth = engine._world.player.depth_reached if engine._world is not None else 0
        elapsed_ms = max(0, pygame.time.get_ticks() - engine._stack_trace_started_ms)
        ui.render_stack_trace(engine._stack_trace_lines, depth, elapsed_ms=elapsed_ms)


class BestiaryStateHandler(GameStateHandler):
    name = "BESTIARY"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_bestiary_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        rows = engine._bestiary_rows()
        if rows:
            engine._bestiary_scroll = max(0, min(engine._bestiary_scroll, len(rows) - 1))
        ui.render_bestiary(rows, engine._bestiary_scroll)


class InspectStateHandler(GameStateHandler):
    """Inspect overlay drawn on top of the live world view."""

    name = "INSPECT"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_inspect_key(event)

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
            sector=world.player.depth_reached,
            world=world,
            patches=[p.label for p in engine._patches.selected],
        )
        ui.render_bottom_bar(_INSPECT_HINTS)
        ui.render_console(engine._console)
        engine._render_inspect_overlay(ui)


class MilestoneResultStateHandler(GameStateHandler):
    name = "MILESTONE_RESULT"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_milestone_result_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_milestone_result(engine._milestone_result_panel)


class VendorStateHandler(GameStateHandler):
    name = "VENDOR"

    def handle_event(self, engine: GameEngine, event: pygame.event.Event) -> None:
        engine._handle_vendor_key(event)

    def render(self, engine: GameEngine, ui: UIManager) -> None:
        ui.render_vendor(
            bits=engine._fetch_bits(),
            stock=engine._vendor_stock,
            selected=engine._vendor_index,
            message=engine._vendor_message,
            free=engine._vendor_free,
        )
