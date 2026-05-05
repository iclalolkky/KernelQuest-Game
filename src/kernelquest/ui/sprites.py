"""Phase 7 — procedural entity sprites.

Pygame is the only graphics dep, so rather than ship PNG assets we draw the
player and every malware species directly into a ``pygame.Surface`` from
primitives. Frames are produced on demand and cached by ``(species, frame,
palette, hp_ratio_bucket)`` to avoid re-rasterising every render call.

Animation is driven by a global frame counter incremented once per
``UIManager.render_*`` call; entities sample ``frame_index`` to choose which
of their idle / walk frames to display.

Each sprite is a square the size of one tile. Bosses keep a 1-tile footprint
so the existing collision grid stays untouched (Phase 9 introduces real 2x2
arena sprites; here we only telegraph the boss with a glitched glyph).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from kernelquest.entities.malware import (
    KernelPanic,
    LogicBomb,
    Malware,
    SegFault,
    SyntaxError_,
    ZombieProcess,
)
from kernelquest.ui import theme

# ----- Player palette swaps (7.2) -----


@dataclass(frozen=True)
class PlayerPalette:
    """Color set used by `draw_player_sprite`."""

    key: str
    label: str
    core: tuple[int, int, int]
    fin: tuple[int, int, int]
    halo: tuple[int, int, int]
    unlock_hint: str = ""


PALETTE_KERNEL = PlayerPalette(
    key="kernel",
    label="init(0)",
    core=(255, 230, 90),
    fin=(60, 220, 255),
    halo=(60, 220, 255),
    unlock_hint="default",
)
PALETTE_PHOSPHOR = PlayerPalette(
    key="phosphor",
    label="init(0) — phosphor",
    core=(170, 255, 120),
    fin=(60, 220, 120),
    halo=(60, 220, 120),
    unlock_hint="defeat first boss",
)
PALETTE_AMBER = PlayerPalette(
    key="amber",
    label="init(0) — amber",
    core=(255, 200, 90),
    fin=(255, 140, 60),
    halo=(255, 160, 80),
    unlock_hint="reach sector 0x05",
)
PALETTE_LEAK = PlayerPalette(
    key="leak",
    label="init(0) — corrupted",
    core=(220, 80, 220),
    fin=(255, 80, 120),
    halo=(255, 80, 200),
    unlock_hint="dump core 5 times",
)

PLAYER_PALETTES: tuple[PlayerPalette, ...] = (
    PALETTE_KERNEL,
    PALETTE_PHOSPHOR,
    PALETTE_AMBER,
    PALETTE_LEAK,
)


def get_player_palette(key: str) -> PlayerPalette:
    for p in PLAYER_PALETTES:
        if p.key == key:
            return p
    return PALETTE_KERNEL


# ----- Frame counter -----


class FrameClock:
    """Tiny monotonic counter the renderer ticks every frame."""

    def __init__(self) -> None:
        self.frame: int = 0

    def tick(self) -> None:
        self.frame += 1


# ----- Player sprite -----


def draw_player_sprite(
    target: pygame.Surface,
    rect: pygame.Rect,
    *,
    frame: int,
    palette: PlayerPalette,
    has_scan_boost: bool = False,
) -> None:
    """Render the protagonist into ``rect`` on ``target``.

    Process glyph: pulsing diamond core + 4 rotating I/O fins + halo.
    """
    cx = rect.centerx
    cy = rect.centery
    size = min(rect.width, rect.height)
    pulse = (math.sin(frame * 0.25) + 1.0) * 0.5  # 0..1
    core_r = int(size * (0.22 + 0.05 * pulse))

    # Halo (faint outer ring)
    halo_alpha = 90 + int(60 * pulse)
    halo = pygame.Surface((size + 8, size + 8), pygame.SRCALPHA)
    pygame.draw.circle(
        halo,
        (*palette.halo, halo_alpha),
        (halo.get_width() // 2, halo.get_height() // 2),
        size // 2,
    )
    target.blit(halo, halo.get_rect(center=(cx, cy)))

    # Rotating I/O fins (4 small squares around the core)
    rot = frame * 0.18
    fin_dist = size * 0.32
    fin_size = max(3, size // 7)
    for i in range(4):
        a = rot + i * (math.pi / 2)
        fx = cx + int(math.cos(a) * fin_dist)
        fy = cy + int(math.sin(a) * fin_dist)
        fin_rect = pygame.Rect(0, 0, fin_size, fin_size)
        fin_rect.center = (fx, fy)
        pygame.draw.rect(target, palette.fin, fin_rect, border_radius=1)

    # Diamond core
    core_pts = [
        (cx, cy - core_r),
        (cx + core_r, cy),
        (cx, cy + core_r),
        (cx - core_r, cy),
    ]
    pygame.draw.polygon(target, palette.core, core_pts)
    pygame.draw.polygon(target, palette.fin, core_pts, width=1)

    if has_scan_boost:
        ring_r = size // 2 - 2
        pygame.draw.circle(target, palette.halo, (cx, cy), ring_r, 1)


def draw_player_nameplate(
    target: pygame.Surface,
    rect: pygame.Rect,
    name: str,
    font: pygame.font.Font,
) -> None:
    """Tiny label floating just above the player tile (7.2)."""
    if not name:
        return
    surf = font.render(name, True, theme.NEON_CYAN)
    bg = pygame.Surface((surf.get_width() + 8, surf.get_height() + 2), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    pos = (rect.centerx - bg.get_width() // 2, rect.top - bg.get_height() - 2)
    target.blit(bg, pos)
    target.blit(surf, (pos[0] + 4, pos[1] + 1))


# ----- Enemy sprites (7.3) -----


def draw_enemy_sprite(
    target: pygame.Surface,
    rect: pygame.Rect,
    enemy: Malware,
    *,
    frame: int,
    font_small: pygame.font.Font,
    font_body: pygame.font.Font,
) -> None:
    """Dispatch to the right per-species drawer.

    Falls back to a generic amber square so unknown subclasses still render.
    """
    if isinstance(enemy, SyntaxError_):
        _draw_syntax_error(target, rect, enemy, frame, font_body)
    elif isinstance(enemy, LogicBomb):
        _draw_logic_bomb(target, rect, enemy, frame)
    elif isinstance(enemy, ZombieProcess):
        _draw_zombie_process(target, rect, enemy, frame)
    elif isinstance(enemy, KernelPanic):
        _draw_kernel_panic(target, rect, enemy, frame, font_small)
    elif isinstance(enemy, SegFault):
        _draw_segfault(target, rect, enemy, frame, font_small)
    else:  # pragma: no cover — defensive fallback for new species
        pygame.draw.rect(target, theme.NEON_AMBER, rect.inflate(-4, -4), border_radius=4)
    _draw_enemy_hp_pips(target, rect, enemy)


def _draw_enemy_hp_pips(target: pygame.Surface, rect: pygame.Rect, enemy: Malware) -> None:
    pip_count = max(1, min(8, enemy.max_hp // 4))
    pip_w = (rect.width - 8) // pip_count
    filled = int(round(pip_count * (enemy.hp / max(1, enemy.max_hp))))
    color = theme.NEON_MAGENTA if getattr(enemy, "is_boss", False) else theme.NEON_AMBER
    for i in range(pip_count):
        pip_color = color if i < filled else theme.PANEL_BG
        pip_rect = pygame.Rect(rect.x + 4 + i * pip_w, rect.y + 1, max(2, pip_w - 1), 3)
        pygame.draw.rect(target, pip_color, pip_rect)


def _draw_syntax_error(
    target: pygame.Surface,
    rect: pygame.Rect,
    _enemy: SyntaxError_,
    frame: int,
    font_body: pygame.font.Font,
) -> None:
    """Flickering red ``;`` glyph; jittery patrol idle."""
    flicker = (frame // 3) % 5 != 0
    color = theme.ENEMY_SYNTAX_ERROR if flicker else (200, 60, 60)
    jitter_x = ((frame * 7) % 5) - 2
    jitter_y = ((frame * 11) % 5) - 2
    body = rect.inflate(-8, -8).move(jitter_x, jitter_y)
    pygame.draw.rect(target, (40, 0, 0), body, border_radius=3)
    glyph = font_body.render(";", True, color)
    target.blit(glyph, glyph.get_rect(center=body.center))


def _draw_logic_bomb(
    target: pygame.Surface, rect: pygame.Rect, _enemy: LogicBomb, frame: int
) -> None:
    """Pulsing amber circle with a growing fuse-ring telegraph."""
    cx = rect.centerx
    cy = rect.centery
    base_r = rect.width // 2 - 4
    pulse = (math.sin(frame * 0.32) + 1.0) * 0.5
    core_r = base_r - int(2 * pulse)
    pygame.draw.circle(target, theme.ENEMY_LOGIC_BOMB, (cx, cy), core_r)
    pygame.draw.circle(target, theme.NEON_AMBER, (cx, cy), core_r, 1)
    # Fuse ring expands every cycle.
    ring_r = base_r + int(4 * pulse)
    pygame.draw.circle(target, (255, 200, 60), (cx, cy), ring_r, 1)


def _draw_zombie_process(
    target: pygame.Surface, rect: pygame.Rect, enemy: ZombieProcess, frame: int
) -> None:
    """Desaturated grey block; flips to corrupted-magenta after revive."""
    body = rect.inflate(-6, -6)
    if enemy.has_revived:
        color = (180, 60, 200)
        outline = theme.NEON_MAGENTA
    else:
        color = (110, 110, 130)
        outline = (160, 160, 190)
    pygame.draw.rect(target, color, body, border_radius=3)
    pygame.draw.rect(target, outline, body, width=1, border_radius=3)
    # Drifting "Z" glyph.
    drift = ((frame // 4) % 4) - 2
    pts = [
        (body.left + 4, body.top + 4 + drift),
        (body.right - 4, body.top + 4 + drift),
        (body.left + 4, body.bottom - 4 + drift),
        (body.right - 4, body.bottom - 4 + drift),
    ]
    pygame.draw.lines(target, outline, False, pts, 1)


def _draw_kernel_panic(
    target: pygame.Surface,
    rect: pygame.Rect,
    enemy: KernelPanic,
    frame: int,
    font_small: pygame.font.Font,
) -> None:
    """BSOD-style block with glitching text overlay."""
    body = rect.inflate(-2, -2)
    bg = (20, 20, 90) if not enemy.is_enraged else (140, 20, 30)
    pygame.draw.rect(target, bg, body)
    pygame.draw.rect(target, theme.ENEMY_KERNEL_PANIC, body, width=2)
    # Glitching slices of text — different snippet every few frames.
    snippets = ("0xDEADBEEF", "PANIC", "STOP", "0x00000C5")
    snippet = snippets[(frame // 5) % len(snippets)]
    text = font_small.render(snippet, True, (240, 240, 255))
    target.blit(text, text.get_rect(center=body.center))
    # Random-looking noise lines (deterministic per frame).
    for i in range(3):
        y = body.top + 4 + ((frame + i * 7) % (body.height - 8))
        x_off = ((frame * (i + 1)) % 6) - 3
        pygame.draw.line(
            target, (240, 240, 255), (body.left + 2 + x_off, y), (body.right - 2 + x_off, y), 1
        )


def _draw_segfault(
    target: pygame.Surface,
    rect: pygame.Rect,
    enemy: SegFault,
    frame: int,
    font_small: pygame.font.Font,
) -> None:
    """Half-rendered sprite that snaps to a new offset on damage."""
    body = rect.inflate(-4, -4)
    # Render two halves at slightly different offsets.
    half_w = body.width // 2
    snap = 3 if enemy.pending_teleport else 0
    left = pygame.Rect(body.left, body.top, half_w, body.height)
    right = pygame.Rect(body.left + half_w, body.top + snap, half_w, body.height)
    pygame.draw.rect(target, (60, 200, 200), left, border_radius=2)
    pygame.draw.rect(target, (220, 80, 200), right, border_radius=2)
    glyph = font_small.render("SIG", True, (240, 240, 240))
    target.blit(glyph, glyph.get_rect(center=body.center))
    # Faint scanline drift.
    y = body.top + (frame % body.height)
    pygame.draw.line(target, (255, 255, 255, 180), (body.left, y), (body.right, y), 1)


__all__ = [
    "FrameClock",
    "PlayerPalette",
    "PLAYER_PALETTES",
    "PALETTE_KERNEL",
    "PALETTE_PHOSPHOR",
    "PALETTE_AMBER",
    "PALETTE_LEAK",
    "get_player_palette",
    "draw_player_sprite",
    "draw_player_nameplate",
    "draw_enemy_sprite",
]
