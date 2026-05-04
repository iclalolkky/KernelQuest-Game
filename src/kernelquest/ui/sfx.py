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

# Alternative tracks. Each is a sequence of frequencies played sequentially.
_TRACK_VARIANT_A: Final[tuple[int, ...]] = (
    330,
    392,
    440,
    392,
    330,
    262,
    294,
    330,
    440,
    494,
    523,
    494,
    440,
    392,
    330,
    294,
)
_TRACK_BOSS: Final[tuple[int, ...]] = (
    110,
    110,
    165,
    110,
    147,
    110,
    196,
    110,
    110,
    110,
    165,
    110,
    220,
    165,
    147,
    110,
)
_TRACK_TUTORIAL: Final[tuple[int, ...]] = (
    262,
    330,
    392,
    440,
    392,
    330,
    262,
    196,
)


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


def _chiptune_loop() -> bytes:
    return _build_loop(_CHIPTUNE_NOTES)


def _build_loop(notes: tuple[int, ...]) -> bytes:
    """Concatenate ``notes`` into a single seamless triangle-ish loop."""
    samples = array("h")
    for freq in notes:
        sample_count = int(AUDIO_SAMPLE_RATE * _CHIPTUNE_NOTE_MS / 1000)
        period = max(1, int(AUDIO_SAMPLE_RATE / freq))
        for i in range(sample_count):
            position = i / sample_count
            envelope = min(position * 8.0, 1.0) * min((1.0 - position) * 8.0, 1.0) * 0.45
            tri = 2 * abs((i % period) / period - 0.5) - 0.5
            value = int(_AMPLITUDE * tri * envelope)
            samples.append(value)
            samples.append(value)
        # Tiny inter-note gap to mask boundary clicks.
        gap = int(AUDIO_SAMPLE_RATE * 0.01)
        for _ in range(gap):
            samples.append(0)
            samples.append(0)
    return samples.tobytes()


class SoundManager:
    """Plays short procedurally-generated SFX. Silent if audio init fails."""

    def __init__(self) -> None:
        self._enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music: pygame.mixer.Sound | None = None
        self._music_channel: pygame.mixer.Channel | None = None
        self._tracks: dict[str, pygame.mixer.Sound] = {}
        self._current_track: str | None = None
        self._volume: float = 0.25
        self._music_volume: float = 0.5
        self._sfx_volume: float = 1.0
        self._muted: bool = False
        self._music_playing: bool = False
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
                "boss_warn": pygame.mixer.Sound(buffer=_sweep(110, 880, 600)),
                "glitch": pygame.mixer.Sound(buffer=_sweep(880, 60, 350)),
            }
            try:
                self._music = pygame.mixer.Sound(buffer=_build_loop(_CHIPTUNE_NOTES))
                self._tracks = {
                    "main": self._music,
                    "variant": pygame.mixer.Sound(buffer=_build_loop(_TRACK_VARIANT_A)),
                    "boss": pygame.mixer.Sound(buffer=_build_loop(_TRACK_BOSS)),
                    "tutorial": pygame.mixer.Sound(buffer=_build_loop(_TRACK_TUTORIAL)),
                }
                self._music_channel = pygame.mixer.Channel(7)
            except pygame.error:  # pragma: no cover
                self._music = None
                self._music_channel = None
            self.set_volume(self._volume)

    # ----- volume controls -----

    def set_volume(self, volume: float) -> None:
        """Master volume (legacy). Scales both music and sfx."""
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume()

    def set_music_volume(self, volume: float) -> None:
        self._music_volume = max(0.0, min(1.0, volume))
        self._apply_volume()

    def set_sfx_volume(self, volume: float) -> None:
        self._sfx_volume = max(0.0, min(1.0, volume))
        self._apply_volume()

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self._apply_volume()

    def toggle_mute(self) -> bool:
        self._muted = not self._muted
        self._apply_volume()
        return self._muted

    def _apply_volume(self) -> None:
        if not self._enabled:
            return
        master = 0.0 if self._muted else self._volume
        for sound in self._sounds.values():
            sound.set_volume(master * self._sfx_volume)
        if self._music is not None:
            self._music.set_volume(master * self._music_volume)
        for track in self._tracks.values():
            track.set_volume(master * self._music_volume)

    def play(self, name: str) -> None:
        if not self._enabled or self._muted:
            return
        sound = self._sounds.get(name)
        if sound is None:  # pragma: no cover
            return
        try:
            sound.play()
        except pygame.error:  # pragma: no cover
            self._enabled = False

    def start_music(self, track: str = "main") -> None:
        if not self._enabled or self._music_channel is None:
            return
        sound = self._tracks.get(track)
        if sound is None:
            return
        if self._music_playing and self._current_track == track:
            return
        try:
            self._music_channel.stop()
            self._music_channel.play(sound, loops=-1)
            self._music_playing = True
            self._current_track = track
        except pygame.error:  # pragma: no cover
            self._music_playing = False

    def stop_music(self) -> None:
        if self._music_channel is not None and self._music_playing:
            self._music_channel.stop()
            self._music_playing = False
            self._current_track = None
