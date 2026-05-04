"""Repositories — typed query helpers over `Database`."""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.data.database import Database


@dataclass(frozen=True)
class ScoreRecord:
    """A single row in the `scores` table."""

    id: int
    player_name: str
    depth_reached: int
    total_score: int
    crash_cause: str
    timestamp: str


class ScoreRepository:
    """CRUD for the `scores` table."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert(
        self,
        player_name: str,
        depth_reached: int,
        total_score: int,
        crash_cause: str,
    ) -> int:
        """Insert a new score row and return its `id`."""
        with self._db.connection:
            cursor = self._db.connection.execute(
                """
                INSERT INTO scores (player_name, depth_reached, total_score, crash_cause)
                VALUES (?, ?, ?, ?);
                """,
                (player_name, depth_reached, total_score, crash_cause),
            )
        score_id = cursor.lastrowid
        if score_id is None:  # pragma: no cover - SQLite always returns one here
            raise RuntimeError("INSERT did not return a lastrowid")
        return score_id

    def top_n(self, n: int) -> list[ScoreRecord]:
        """Return the top `n` rows sorted by `total_score` descending."""
        if n < 0:
            raise ValueError("n must be non-negative")
        rows = self._db.connection.execute(
            """
            SELECT id, player_name, depth_reached, total_score, crash_cause, timestamp
              FROM scores
             ORDER BY total_score DESC, depth_reached DESC, timestamp DESC
             LIMIT ?;
            """,
            (n,),
        ).fetchall()
        return [ScoreRecord(**dict(row)) for row in rows]

    def all(self) -> list[ScoreRecord]:
        rows = self._db.connection.execute("""
            SELECT id, player_name, depth_reached, total_score, crash_cause, timestamp
              FROM scores
             ORDER BY id ASC;
            """).fetchall()
        return [ScoreRecord(**dict(row)) for row in rows]
