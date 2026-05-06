"""Phase 12.11 — dialogue scenes for narrative LORE moments."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from kernelquest.core.config import WINDOW_HEIGHT, WINDOW_WIDTH
from kernelquest.ui.dialogue import (
    ENDING,
    FIRST_BOSS,
    FIRST_DISTRO_SUCCESS,
    FIRST_KILL,
    INTRO,
    SCENES,
    DialogueLine,
    DialogueScene,
    get_scene,
)
from kernelquest.ui.renderer import UIManager


def test_all_five_scenes_present() -> None:
    for key in (INTRO, FIRST_KILL, FIRST_BOSS, FIRST_DISTRO_SUCCESS, ENDING):
        scene = get_scene(key)
        assert isinstance(scene, DialogueScene)
        assert scene.lines, f"scene {key} has no lines"


def test_every_line_has_speaker_and_portrait() -> None:
    for scene in SCENES.values():
        for line in scene.lines:
            assert isinstance(line, DialogueLine)
            assert line.speaker
            assert line.portrait in {"kernel", "init"}
            assert line.text


def test_render_dialogue_does_not_crash() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.HIDDEN)
    ui = UIManager(screen)
    scene = get_scene(INTRO)
    for i in range(len(scene.lines)):
        ui.render_dialogue(scene, i, elapsed_ms=2000)
    pygame.display.flip()
