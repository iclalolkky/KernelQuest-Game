"""Phase 5 — DaemonRepository, DailyRunRepository, RunRepository fallback."""

from __future__ import annotations

import pytest

from kernelquest.data.database import Database
from kernelquest.data.repositories import (
    DaemonRepository,
    DailyRunRepository,
    RunRepository,
    ScoreRepository,
)


@pytest.fixture
def db() -> Database:
    database = Database.open(":memory:")
    database.run_migrations()
    return database


def test_daemon_repository_grant_and_equip(db: Database) -> None:
    repo = DaemonRepository(db)
    assert repo.owned() == set()
    repo.grant("cron")
    repo.grant("oom_killer")
    repo.grant("cron")  # idempotent
    assert repo.owned() == {"cron", "oom_killer"}

    assert repo.equipped() == []
    repo.set_equipped(["cron", "oom_killer"])
    assert repo.equipped() == ["cron", "oom_killer"]
    repo.set_equipped(["oom_killer"])
    assert repo.equipped() == ["oom_killer"]


def test_daily_run_repository(db: Database) -> None:
    repo = DailyRunRepository(db)
    assert repo.top_for_date("2025-01-01") == []
    assert repo.has_played("2025-01-01", "alice") is False

    repo.insert(
        run_date="2025-01-01",
        player_name="alice",
        seed=42,
        depth_reached=5,
        total_score=900,
        crash_cause="Stack overflow",
        duration_ms=12000,
    )
    repo.insert(
        run_date="2025-01-01",
        player_name="bob",
        seed=42,
        depth_reached=4,
        total_score=1500,
        crash_cause="Kernel Panic",
        duration_ms=22000,
    )
    repo.insert(
        run_date="2025-01-02",
        player_name="alice",
        seed=99,
        depth_reached=2,
        total_score=200,
        crash_cause="bad sector",
        duration_ms=4000,
    )

    top = repo.top_for_date("2025-01-01")
    assert [r.player_name for r in top] == ["bob", "alice"]
    assert repo.has_played("2025-01-01", "alice") is True
    assert repo.has_played("2025-01-01", "carol") is False
    assert repo.top_for_date("2025-01-01", n=1)[0].player_name == "bob"


def test_run_repository_fallback_uses_scores(db: Database) -> None:
    runs = RunRepository(db)
    scores = ScoreRepository(db)
    # No runs at all → still None.
    assert runs.best_with_score_fallback(scores) is None

    scores.insert(
        player_name="legacy", depth_reached=9, total_score=1853, crash_cause="kernel panic"
    )
    fallback = runs.best_with_score_fallback(scores)
    assert fallback is not None
    assert fallback.total_score == 1853
    assert fallback.player_name == "legacy"
    assert fallback.id == -1

    # When a real run exists with higher score, prefer the run.
    runs.insert(
        player_name="hero",
        seed=7,
        depth_reached=10,
        total_score=2000,
        crash_cause="manual shutdown",
        duration_ms=1000,
    )
    best = runs.best_with_score_fallback(scores)
    assert best is not None
    assert best.player_name == "hero"
    assert best.total_score == 2000
