"""Phase 12.8 — inter-sector cinematic timing."""

from __future__ import annotations

import os

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.display.init()
pygame.font.init()

from kernelquest.ui import renderer as renderer_mod  # noqa: E402


def _ui() -> renderer_mod.UIManager:
    screen = pygame.display.set_mode(
        (renderer_mod.WINDOW_WIDTH, renderer_mod.WINDOW_HEIGHT), pygame.HIDDEN
    )
    return renderer_mod.UIManager(screen)


def test_render_stack_trace_runs_at_intro_and_post_intro() -> None:
    ui = _ui()
    lines = [("[KERNEL]", "sector mapped."), ("[init]", "i hear the leak.")]
    # Intro frame.
    ui.render_stack_trace(lines, sector=3, elapsed_ms=200)
    # Mid-fade frame.
    ui.render_stack_trace(lines, sector=3, elapsed_ms=900)
    # Post-intro: full reveal.
    ui.render_stack_trace(lines, sector=3, elapsed_ms=2_500)


def test_render_stack_trace_default_elapsed_is_post_intro() -> None:
    ui = _ui()
    # Default kwarg is documented as post-intro so legacy callers still work.
    ui.render_stack_trace([("[init]", "ok")], sector=1)
