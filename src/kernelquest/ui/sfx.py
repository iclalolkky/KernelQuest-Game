"""Sentezlenmiş SFX. Ses cihazı eksikse sessiz no-op'lara geri döner."""

from __future__ import annotations

import logging
import math
from array import array
from typing import Final

import pygame

from kernelquest.core.config import AUDIO_SAMPLE_RATE

log = logging.getLogger(__name__)

_AMPLITUDE: Final[int] = 12000
_CHIPTUNE_NOTES: Final[tuple[int, ...]] = (
    220,
    277,
    330,
    277,
    220,
    196,
    247,
    277,
    330,
    392,
    440,
    392,
    330,
    277,
    220,
    247,
)
_CHIPTUNE_NOTE_MS: Final[int] = 180


def _square_wave(frequency: float, duration_ms: int) -> bytes:
    """Ham PCM tamponuna stereo 16-bit kare dalga renderla."""
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


def _chiptune_loop() -> bytes:
    """`_CHIPTUNE_NOTES`'u tek bir kesintisiz üçgen benzeri döngüde birleştir."""
    samples = array("h")
    for freq in _CHIPTUNE_NOTES:
        sample_count = int(AUDIO_SAMPLE_RATE * _CHIPTUNE_NOTE_MS / 1000)
        period = max(1, int(AUDIO_SAMPLE_RATE / freq))
        for i in range(sample_count):
            position = i / sample_count
            envelope = min(position * 8.0, 1.0) * min((1.0 - position) * 8.0, 1.0) * 0.45
            # Daha yumuşak bir chiptune hissi için üçgen benzeri dalga.
            tri = 2 * abs((i % period) / period - 0.5) - 0.5
            value = int(_AMPLITUDE * tri * envelope)
            samples.append(value)
            samples.append(value)
        # Kenar tıklamalarını maskelemek için notlar arası küçük boşluk.
        gap = int(AUDIO_SAMPLE_RATE * 0.01)
        for _ in range(gap):
            samples.append(0)
            samples.append(0)
    return samples.tobytes()


class SoundManager:
    """Kısa prosedürel olarak üretilen SFX'leri çalar. Ses başlatma başarısızsa sessizdir."""

    def __init__(self) -> None:
        self._enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music: pygame.mixer.Sound | None = None
        self._music_channel: pygame.mixer.Channel | None = None
        self._volume: float = 0.25
        self._music_playing: bool = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=AUDIO_SAMPLE_RATE, size=-16, channels=2)
            self._enabled = pygame.mixer.get_init() is not None
        except pygame.error as exc:  # pragma: no cover - depends on host audio
            log.info("SoundManager devre dışı bırakıldı (ses cihazı yok): %s", exc)
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
            try:
                self._music = pygame.mixer.Sound(buffer=_chiptune_loop())
                self._music_channel = pygame.mixer.Channel(7)
            except pygame.error:  # pragma: no cover
                self._music = None
                self._music_channel = None
            self.set_volume(self._volume)

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        if not self._enabled:
            return
        for sound in self._sounds.values():
            sound.set_volume(self._volume)
        if self._music is not None:
            self._music.set_volume(self._volume * 0.5)

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        sound = self._sounds.get(name)
        if sound is None:  # pragma: no cover
            return
        try:
            sound.play()
        except pygame.error:  # pragma: no cover
            self._enabled = False

    def start_music(self) -> None:
        if not self._enabled or self._music is None or self._music_channel is None:
            return
        if self._music_playing:
            return
        try:
            self._music_channel.play(self._music, loops=-1)
            self._music_playing = True
        except pygame.error:  # pragma: no cover
            self._music_playing = False

    def stop_music(self) -> None:
        if self._music_channel is not None and self._music_playing:
            self._music_channel.stop()
            self._music_playing = False
