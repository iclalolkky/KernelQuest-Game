"""Phase 7 — cinematic intro / ending player.

Frames live in `data.lore_catalog`; this module owns their playback state
(current index, elapsed time, skip/auto-skip handling) and a tiny renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from kernelquest.core.config import WINDOW_HEIGHT, WINDOW_WIDTH
from kernelquest.data.lore_catalog import CinematicFrame
from kernelquest.ui import theme


@dataclass
class CinematicPlayer:
    """Drives a sequence of `CinematicFrame`s.

    Frame advances when ``elapsed_s`` exceeds the frame's duration, or when
    ``skip()`` is called. The cutscene is finished when ``finished`` is True.
    """

    frames: tuple[CinematicFrame, ...]
    index: int = 0
    elapsed_s: float = 0.0
    skipped: bool = False
    finished: bool = False
    _started: bool = field(default=False, repr=False)

    def reset(self) -> None:
        self.index = 0
        self.elapsed_s = 0.0
        self.skipped = False
        self.finished = False
        self._started = False

    def start(self) -> None:
        self.reset()
        self._started = True
        self.finished = not self.frames

    def step(self, dt: float) -> None:
        if self.finished or not self._started:
            return
        self.elapsed_s += dt
        cur = self.frames[self.index]
        if self.elapsed_s >= cur.duration_s:
            self._advance()

    def skip(self) -> None:
        """Advance to the next frame, finishing if we were on the last one."""
        if self.finished:
            return
        self.skipped = True
        self._advance()

    def skip_all(self) -> None:
        self.finished = True

    def _advance(self) -> None:
        self.index += 1
        self.elapsed_s = 0.0
        if self.index >= len(self.frames):
            self.finished = True


def render_cinematic(
    screen: pygame.Surface,
    player: CinematicPlayer,
    *,
    font_title: pygame.font.Font,
    font_body: pygame.font.Font,
    font_small: pygame.font.Font,
) -> None:
    """Render the current frame.

    No-op if the cutscene is finished or has no frames yet.
    """
    screen.fill((0, 0, 0))
    if player.finished or not player.frames:
        return
    frame = player.frames[player.index]
    cx = WINDOW_WIDTH // 2
    cy = WINDOW_HEIGHT // 2

    title_surf = font_title.render(frame.title, True, theme.NEON_CYAN)
    screen.blit(title_surf, title_surf.get_rect(center=(cx, cy - 120)))

    y = cy - 40
    for line in frame.body:
        body_surf = font_body.render(line, True, theme.TEXT_PRIMARY)
        screen.blit(body_surf, body_surf.get_rect(center=(cx, y)))
        y += 32

    progress = font_small.render(
        f"{player.index + 1} / {len(player.frames)}    " "[ENTER] next     [ESC] skip all",
        True,
        theme.TEXT_DIM,
    )
    screen.blit(progress, progress.get_rect(center=(cx, WINDOW_HEIGHT - 40)))


__all__ = ["CinematicPlayer", "render_cinematic"]
