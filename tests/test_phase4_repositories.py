"""Tests for the Phase-4 repositories: runs, meta-state, upgrades."""

from __future__ import annotations

import pytest

from kernelquest.data.database import Database
from kernelquest.data.repositories import (
    MetaRepository,
    RunRepository,
    UpgradeRepository,
)
from kernelquest.data.upgrades_catalog import CATALOG


@pytest.fixture()
def db() -> Database:
    database = Database.in_memory()
    database.run_migrations()
    return database


def test_run_repository_insert_and_aggregate(db: Database) -> None:
    repo = RunRepository(db)
    repo.insert(
        "alice",
        seed=1,
        depth_reached=3,
        total_score=100,
        crash_cause="Out of RAM",
        duration_ms=2500,
    )
    repo.insert(
        "bob",
        seed=2,
        depth_reached=5,
        total_score=300,
        crash_cause="Logic Bomb",
        duration_ms=4000,
    )
    repo.insert(
        "carol",
        seed=3,
        depth_reached=2,
        total_score=50,
        crash_cause="Out of RAM",
        duration_ms=1000,
    )

    rows = repo.all()
    assert len(rows) == 3
    # Newest first.
    assert rows[0].player_name == "carol"

    deaths = repo.deaths_by_cause()
    assert deaths == {"Out of RAM": 2, "Logic Bomb": 1}

    assert repo.average_depth() == pytest.approx((3 + 5 + 2) / 3)

    best = repo.best()
    assert best is not None
    assert best.player_name == "bob"
    assert best.total_score == 300


def test_run_repository_empty_aggregates(db: Database) -> None:
    repo = RunRepository(db)
    assert repo.all() == []
    assert repo.deaths_by_cause() == {}
    assert repo.average_depth() == 0.0
    assert repo.best() is None


def test_meta_repository_set_get_upsert(db: Database) -> None:
    repo = MetaRepository(db)
    assert repo.get("missing") is None
    assert repo.get("missing", default="fallback") == "fallback"

    repo.set("settings.volume", "0.5")
    assert repo.get("settings.volume") == "0.5"

    # UPSERT path overwrites.
    repo.set("settings.volume", "0.8")
    assert repo.get("settings.volume") == "0.8"


def test_meta_repository_int_helpers(db: Database) -> None:
    repo = MetaRepository(db)
    assert repo.get_int("bits") == 0
    assert repo.get_int("bits", default=42) == 42
    repo.set_int("bits", 17)
    assert repo.get_int("bits") == 17


def test_upgrade_repository_default_and_set(db: Database) -> None:
    repo = UpgradeRepository(db)
    upgrade = CATALOG[0]
    assert repo.get_level(upgrade.key) == 0

    repo.set_level(upgrade.key, 2)
    assert repo.get_level(upgrade.key) == 2

    levels = repo.all_levels()
    # Backfills every catalog key.
    for entry in CATALOG:
        assert entry.key in levels
    assert levels[upgrade.key] == 2


def test_upgrade_repository_validates(db: Database) -> None:
    repo = UpgradeRepository(db)
    with pytest.raises(KeyError):
        repo.get_level("does_not_exist")

    upgrade = CATALOG[0]
    with pytest.raises(ValueError):
        repo.set_level(upgrade.key, upgrade.max_level + 1)
    with pytest.raises(ValueError):
        repo.set_level(upgrade.key, -1)
