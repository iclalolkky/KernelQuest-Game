"""Player-tunable settings (volume, difficulty), persisted via `MetaRepository`.

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
_KEY_DIFFICULTY = "settings.difficulty"

_DIFFICULTY_ORDER: tuple[Difficulty, ...] = (Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD)


@dataclass
class Settings:
    """In-memory snapshot of user settings."""

    volume: float = 0.25
    difficulty: Difficulty = Difficulty.NORMAL

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


def load(meta: MetaRepository) -> Settings:
    raw_volume = meta.get(_KEY_VOLUME)
    try:
        volume = float(raw_volume) if raw_volume is not None else 0.25
    except ValueError:
        volume = 0.25
    raw_diff = meta.get(_KEY_DIFFICULTY) or Difficulty.NORMAL.value
    try:
        difficulty = Difficulty(raw_diff)
    except ValueError:
        difficulty = Difficulty.NORMAL
    return Settings(volume=max(0.0, min(1.0, volume)), difficulty=difficulty)


def save(meta: MetaRepository, settings: Settings) -> None:
    meta.set(_KEY_VOLUME, f"{settings.volume:.3f}")
    meta.set(_KEY_DIFFICULTY, settings.difficulty.value)
