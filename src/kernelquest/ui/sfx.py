"""Synthesized SFX. Falls back to silent no-ops if the audio device is missing."""

from __future__ import annotations

import logging
import math
from array import array
from typing import Final

import pygame

from kernelquest.core.config import AUDIO_SAMPLE_RATE

log = logging.getLogger(__name__)

_AMPLITUDE: Final[int] = 12000


def _square_wave(frequency: float, duration_ms: int) -> bytes:
    """Render a stereo 16-bit square wave to a raw PCM buffer."""
    sample_count = int(AUDIO_SAMPLE_RATE * duration_ms / 1000)
    period = max(1, int(AUDIO_SAMPLE_RATE / max(1.0, frequency)))
    samples = array("h")
    for i in range(sample_count):
        # Linear fade-out to avoid clicks.
        envelope = max(0.0, 1.0 - i / sample_count)
        value = _AMPLITUDE if (i % period) < period // 2 else -_AMPLITUDE
        sample = int(value * envelope)
        samples.append(sample)
        samples.append(sample)
    return samples.tobytes()


def _sweep(start_hz: float, end_hz: float, duration_ms: int) -> bytes:
    sample_count = int(AUDIO_SAMPLE_RATE * duration_ms / 1000)
    samples = array("h")
    phase = 0.0
    for i in range(sample_count):
        t = i / max(1, sample_count - 1)
        freq = start_hz + (end_hz - start_hz) * t
        phase += 2 * math.pi * freq / AUDIO_SAMPLE_RATE
        envelope = max(0.0, 1.0 - i / sample_count)
        value = int(_AMPLITUDE * math.sin(phase) * envelope)
        samples.append(value)
        samples.append(value)
    return samples.tobytes()


class SoundManager:
    """Plays short procedurally-generated SFX. Silent if audio init fails."""

    def __init__(self) -> None:
        self._enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=AUDIO_SAMPLE_RATE, size=-16, channels=2)
            self._enabled = pygame.mixer.get_init() is not None
        except pygame.error as exc:  # pragma: no cover - depends on host audio
            log.info("SoundManager disabled (no audio device): %s", exc)
            self._enabled = False

        if self._enabled:
            self._sounds = {
                "move": pygame.mixer.Sound(buffer=_square_wave(440, 40)),
                "attack": pygame.mixer.Sound(buffer=_sweep(880, 220, 90)),
                "explode": pygame.mixer.Sound(buffer=_sweep(220, 60, 220)),
                "pickup": pygame.mixer.Sound(buffer=_sweep(660, 990, 80)),
                "crash": pygame.mixer.Sound(buffer=_sweep(330, 60, 600)),
                "descend": pygame.mixer.Sound(buffer=_sweep(440, 880, 220)),
            }
            for sound in self._sounds.values():
                sound.set_volume(0.25)

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        sound = self._sounds.get(name)
        if sound is None:  # pragma: no cover
            return
        try:
            sound.play()
        except pygame.error:  # pragma: no cover - device removed mid-run
            self._enabled = False
