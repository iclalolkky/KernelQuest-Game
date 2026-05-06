"""Phase 12.10 — Vendor visual redesign smoke checks."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from kernelquest.core.config import WINDOW_HEIGHT, WINDOW_WIDTH
from kernelquest.ui.renderer import UIManager


def _make_ui() -> UIManager:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.HIDDEN)
    return UIManager(screen)


def test_vendor_renders_three_shelves_without_crash() -> None:
    ui = _make_ui()
    stock: list[dict[str, object]] = [
        {"kind": "program", "key": "p1", "label": "fork", "description": "spawn child", "cost": 5},
        {"kind": "program", "key": "p2", "label": "kill9", "description": "force kill", "cost": 5},
        {"kind": "daemon", "key": "d1", "label": "cron", "description": "schedules", "cost": 8},
        {"kind": "daemon", "key": "d2", "label": "tcpdump", "description": "sniff", "cost": 8},
        {"kind": "patch", "key": "pa", "label": "armor", "description": "+armor", "cost": 6},
        {
            "kind": "reroll",
            "key": "reroll",
            "label": "kill -HUP vendor",
            "description": "reseed",
            "cost": 3,
        },
        {
            "kind": "leave",
            "key": "leave",
            "label": "exit /var/run/vendor",
            "description": "step away",
            "cost": 0,
        },
    ]
    ui.render_vendor(bits=42, stock=stock, selected=0, message=None, free=False)
    pygame.display.flip()


def test_vendor_renders_free_state() -> None:
    ui = _make_ui()
    stock: list[dict[str, object]] = [
        {"kind": "program", "key": "p1", "label": "fork", "description": "spawn", "cost": 5},
        {"kind": "leave", "key": "leave", "label": "exit", "description": "go", "cost": 0},
    ]
    ui.render_vendor(bits=0, stock=stock, selected=1, message="hello", free=True)
    pygame.display.flip()
