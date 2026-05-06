"""Phase 12.9 — boss phase shift cinematic burst."""

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


def test_render_phase_shift_no_op_when_ttl_zero() -> None:
    ui = _ui()
    ui.render_phase_shift(0.0)
    ui.render_phase_shift(-0.5)


def test_render_phase_shift_paints_full_intensity() -> None:
    ui = _ui()
    ui.render_phase_shift(0.45)


def test_render_phase_shift_decays() -> None:
    ui = _ui()
    for ttl in (0.45, 0.30, 0.15, 0.05):
        ui.render_phase_shift(ttl)
