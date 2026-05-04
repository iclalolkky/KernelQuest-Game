"""Tests for the settings module."""

from __future__ import annotations

import pytest

from kernelquest.core.settings import Difficulty, Settings, load, save
from kernelquest.data.database import Database
from kernelquest.data.repositories import MetaRepository


@pytest.fixture()
def meta() -> MetaRepository:
    db = Database.in_memory()
    db.run_migrations()
    return MetaRepository(db)


def test_default_load(meta: MetaRepository) -> None:
    settings = load(meta)
    assert settings.difficulty is Difficulty.NORMAL
    assert 0.0 <= settings.volume <= 1.0


def test_round_trip(meta: MetaRepository) -> None:
    settings = Settings(volume=0.6, difficulty=Difficulty.HARD)
    save(meta, settings)
    loaded = load(meta)
    assert loaded.difficulty is Difficulty.HARD
    assert loaded.volume == pytest.approx(0.6)


def test_difficulty_multipliers() -> None:
    s = Settings(difficulty=Difficulty.EASY)
    assert s.player_damage_multiplier > 1.0
    assert s.enemy_damage_multiplier < 1.0

    s.difficulty = Difficulty.HARD
    assert s.player_damage_multiplier < 1.0
    assert s.enemy_damage_multiplier > 1.0


def test_cycle_difficulty() -> None:
    s = Settings()
    s.cycle_difficulty()
    assert s.difficulty is Difficulty.HARD
    s.cycle_difficulty()
    assert s.difficulty is Difficulty.EASY
    s.cycle_difficulty()
    assert s.difficulty is Difficulty.NORMAL


def test_adjust_volume_clamps() -> None:
    s = Settings(volume=0.9)
    s.adjust_volume(0.5)
    assert s.volume == 1.0
    s.adjust_volume(-2.0)
    assert s.volume == 0.0


def test_load_handles_garbage(meta: MetaRepository) -> None:
    meta.set("settings.volume", "not-a-number")
    meta.set("settings.difficulty", "INSANE")
    settings = load(meta)
    assert settings.difficulty is Difficulty.NORMAL
    assert settings.volume == 0.25
