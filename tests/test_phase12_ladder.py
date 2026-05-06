"""Phase 12.7 — RELEASE ladder strip + fullscreen toggle."""

from __future__ import annotations

import os

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.display.init()
pygame.font.init()

from kernelquest.core.run_progress import (  # noqa: E402
    MILESTONES_PER_RELEASE,
    TOTAL_RELEASES,
    MilestoneRecord,
    RunProgress,
    kind_for_milestone,
    target_score_for,
)
from kernelquest.ui import renderer as renderer_mod  # noqa: E402


def _ui() -> renderer_mod.UIManager:
    screen = pygame.display.set_mode(
        (renderer_mod.WINDOW_WIDTH, renderer_mod.WINDOW_HEIGHT), pygame.HIDDEN
    )
    return renderer_mod.UIManager(screen)


def test_render_ladder_strip_is_safe_with_empty_progress() -> None:
    ui = _ui()
    ui.render_ladder_strip(RunProgress(), (10, 10))
    ui.render_ladder_strip(None, (10, 10))


def test_render_ladder_strip_with_records() -> None:
    ui = _ui()
    progress = RunProgress(release_index=1, milestone_index=0)
    progress.records.append(
        MilestoneRecord(
            release_index=0,
            milestone_index=0,
            target_score=target_score_for(0, 0),
            kind=kind_for_milestone(0),
            reached_score=200,
            was_cleared=True,
        )
    )
    ui.render_ladder_strip(progress, (10, 10))


def test_render_ladder_overlay_runs() -> None:
    ui = _ui()
    progress = RunProgress(release_index=2, milestone_index=1)
    ui.render_ladder_overlay(progress)


def test_total_milestones_match_grid() -> None:
    assert TOTAL_RELEASES * MILESTONES_PER_RELEASE == 24
