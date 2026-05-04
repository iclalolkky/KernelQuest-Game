"""Player-tunable settings (volume, difficulty, theme, a11y), persisted via `MetaRepository`.

Difficulty multiplies enemy damage and inversely scales player damage so that
HARD makes runs noticeably more punishing without changing structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kernelquest.data.repositories import MetaRepository


class Difficulty(StrEnum):
    EASY = "EASY"
    NORMAL = "NORMAL"
    HARD = "HARD"


_KEY_VOLUME = "settings.volume"
_KEY_MUSIC_VOLUME = "settings.music_volume"
_KEY_SFX_VOLUME = "settings.sfx_volume"
_KEY_MUTED = "settings.muted"
_KEY_DIFFICULTY = "settings.difficulty"
_KEY_THEME = "settings.theme"
_KEY_FULLSCREEN = "settings.fullscreen"
_KEY_UI_SCALE = "settings.ui_scale"
_KEY_REDUCE_MOTION = "settings.reduce_motion"
_KEY_CRT_EFFECT = "settings.crt_effect"
_KEY_LARGE_TEXT = "settings.large_text"
_KEY_TUTORIAL_DONE = "meta.tutorial_done"

_DIFFICULTY_ORDER: tuple[Difficulty, ...] = (Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD)


@dataclass
class Settings:
    """In-memory snapshot of user settings."""

    volume: float = 0.25
    music_volume: float = 0.5
    sfx_volume: float = 1.0
    muted: bool = False
    difficulty: Difficulty = Difficulty.NORMAL
    theme: str = "kernel"
    fullscreen: bool = False
    ui_scale: float = 1.0
    reduce_motion: bool = False
    crt_effect: bool = True
    large_text: bool = False

    # ----- difficulty modifiers -----

    @property
    def player_damage_multiplier(self) -> float:
        return {
            Difficulty.EASY: 1.25,
            Difficulty.NORMAL: 1.0,
            Difficulty.HARD: 0.85,
        }[self.difficulty]

    @property
    def enemy_damage_multiplier(self) -> float:
        return {
            Difficulty.EASY: 0.75,
            Difficulty.NORMAL: 1.0,
            Difficulty.HARD: 1.35,
        }[self.difficulty]

    # ----- mutation helpers -----

    def cycle_difficulty(self) -> None:
        idx = _DIFFICULTY_ORDER.index(self.difficulty)
        self.difficulty = _DIFFICULTY_ORDER[(idx + 1) % len(_DIFFICULTY_ORDER)]

    def adjust_volume(self, delta: float) -> None:
        self.volume = max(0.0, min(1.0, self.volume + delta))

    def adjust_music_volume(self, delta: float) -> None:
        self.music_volume = max(0.0, min(1.0, self.music_volume + delta))

    def adjust_sfx_volume(self, delta: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + delta))

    def adjust_ui_scale(self, delta: float) -> None:
        self.ui_scale = max(0.75, min(1.5, round(self.ui_scale + delta, 2)))

    def toggle_mute(self) -> None:
        self.muted = not self.muted

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    def toggle_reduce_motion(self) -> None:
        self.reduce_motion = not self.reduce_motion

    def toggle_crt(self) -> None:
        self.crt_effect = not self.crt_effect

    def toggle_large_text(self) -> None:
        self.large_text = not self.large_text


def _bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _float(raw: str | None, default: float, *, lo: float = 0.0, hi: float = 1.0) -> float:
    if raw is None:
        return default
    try:
        return max(lo, min(hi, float(raw)))
    except ValueError:
        return default


def load(meta: MetaRepository) -> Settings:
    raw_diff = meta.get(_KEY_DIFFICULTY) or Difficulty.NORMAL.value
    try:
        difficulty = Difficulty(raw_diff)
    except ValueError:
        difficulty = Difficulty.NORMAL
    return Settings(
        volume=_float(meta.get(_KEY_VOLUME), 0.25),
        music_volume=_float(meta.get(_KEY_MUSIC_VOLUME), 0.5),
        sfx_volume=_float(meta.get(_KEY_SFX_VOLUME), 1.0),
        muted=_bool(meta.get(_KEY_MUTED), False),
        difficulty=difficulty,
        theme=meta.get(_KEY_THEME) or "kernel",
        fullscreen=_bool(meta.get(_KEY_FULLSCREEN), False),
        ui_scale=_float(meta.get(_KEY_UI_SCALE), 1.0, lo=0.75, hi=1.5),
        reduce_motion=_bool(meta.get(_KEY_REDUCE_MOTION), False),
        crt_effect=_bool(meta.get(_KEY_CRT_EFFECT), True),
        large_text=_bool(meta.get(_KEY_LARGE_TEXT), False),
    )


def save(meta: MetaRepository, settings: Settings) -> None:
    meta.set(_KEY_VOLUME, f"{settings.volume:.3f}")
    meta.set(_KEY_MUSIC_VOLUME, f"{settings.music_volume:.3f}")
    meta.set(_KEY_SFX_VOLUME, f"{settings.sfx_volume:.3f}")
    meta.set(_KEY_MUTED, "1" if settings.muted else "0")
    meta.set(_KEY_DIFFICULTY, settings.difficulty.value)
    meta.set(_KEY_THEME, settings.theme)
    meta.set(_KEY_FULLSCREEN, "1" if settings.fullscreen else "0")
    meta.set(_KEY_UI_SCALE, f"{settings.ui_scale:.2f}")
    meta.set(_KEY_REDUCE_MOTION, "1" if settings.reduce_motion else "0")
    meta.set(_KEY_CRT_EFFECT, "1" if settings.crt_effect else "0")
    meta.set(_KEY_LARGE_TEXT, "1" if settings.large_text else "0")


def is_tutorial_done(meta: MetaRepository) -> bool:
    return _bool(meta.get(_KEY_TUTORIAL_DONE), False)


def mark_tutorial_done(meta: MetaRepository) -> None:
    meta.set(_KEY_TUTORIAL_DONE, "1")
