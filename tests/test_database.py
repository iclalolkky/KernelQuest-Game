"""Tests for SQLite persistence — `Database` and `ScoreRepository`."""

from __future__ import annotations

import sqlite3

import pytest

from kernelquest.data.database import Database
from kernelquest.data.repositories import ScoreRepository


@pytest.fixture
def db() -> Database:
    return Database.in_memory()


def test_migrations_create_scores_table(db: Database) -> None:
    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='scores';"
    ).fetchall()
    assert len(rows) == 1


def test_migrations_are_idempotent(db: Database) -> None:
    db.run_migrations()
    db.run_migrations()
    rows = db.connection.execute("SELECT name FROM schema_migrations ORDER BY name;").fetchall()
    assert [r["name"] for r in rows] == [
        "001_init",
        "002_runs",
        "003_meta",
        "004_phase5_backfill",
        "005_phase5_meta",
        "006_phase7_lore",
    ]


def test_score_repository_insert_and_top_n(db: Database) -> None:
    repo = ScoreRepository(db)
    a = repo.insert("alice", depth_reached=3, total_score=100, crash_cause="Out of RAM")
    b = repo.insert("bob", depth_reached=5, total_score=300, crash_cause="Logic Bomb")
    repo.insert("carol", depth_reached=2, total_score=50, crash_cause="Kernel Panic")

    assert a > 0 and b > a

    top2 = repo.top_n(2)
    assert [r.player_name for r in top2] == ["bob", "alice"]
    assert top2[0].total_score == 300
    assert top2[0].crash_cause == "Logic Bomb"


def test_score_repository_all_returns_inserted_rows(db: Database) -> None:
    repo = ScoreRepository(db)
    repo.insert("alice", 1, 10, "Out of RAM")
    repo.insert("bob", 2, 20, "Logic Bomb")
    rows = repo.all()
    assert [r.player_name for r in rows] == ["alice", "bob"]


def test_top_n_negative_raises(db: Database) -> None:
    repo = ScoreRepository(db)
    with pytest.raises(ValueError):
        repo.top_n(-1)


def test_database_context_manager_closes() -> None:
    db = Database.in_memory()
    with db:
        repo = ScoreRepository(db)
        repo.insert("z", 1, 1, "x")
    # After context exit, further queries should fail because connection closed.
    with pytest.raises(sqlite3.ProgrammingError):
        db.connection.execute("SELECT 1;")
