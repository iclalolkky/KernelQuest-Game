"""Repositories - typed query helpers over `Database`."""

from __future__ import annotations

from dataclasses import dataclass

from kernelquest.data.database import Database
from kernelquest.data.upgrades_catalog import CATALOG, get_upgrade


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


@dataclass(frozen=True)
class RunRecord:
    """A single row in the `runs` table."""

    id: int
    player_name: str
    seed: int
    depth_reached: int
    total_score: int
    crash_cause: str
    duration_ms: int
    timestamp: str


class RunRepository:
    """CRUD + aggregations for the `runs` table."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert(
        self,
        player_name: str,
        seed: int,
        depth_reached: int,
        total_score: int,
        crash_cause: str,
        duration_ms: int,
    ) -> int:
        with self._db.connection:
            cursor = self._db.connection.execute(
                """
                INSERT INTO runs
                    (player_name, seed, depth_reached, total_score, crash_cause, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (player_name, seed, depth_reached, total_score, crash_cause, duration_ms),
            )
        run_id = cursor.lastrowid
        if run_id is None:  # pragma: no cover
            raise RuntimeError("INSERT did not return a lastrowid")
        return run_id

    def all(self) -> list[RunRecord]:
        rows = self._db.connection.execute("""
            SELECT id, player_name, seed, depth_reached, total_score, crash_cause,
                   duration_ms, timestamp
              FROM runs
             ORDER BY id DESC;
            """).fetchall()
        return [RunRecord(**dict(row)) for row in rows]

    def deaths_by_cause(self) -> dict[str, int]:
        rows = self._db.connection.execute("""
            SELECT crash_cause, COUNT(*) AS deaths
              FROM runs
             GROUP BY crash_cause
             ORDER BY deaths DESC;
            """).fetchall()
        return {row["crash_cause"]: row["deaths"] for row in rows}

    def average_depth(self) -> float:
        row = self._db.connection.execute(
            "SELECT AVG(depth_reached) AS avg_depth FROM runs;"
        ).fetchone()
        if row is None or row["avg_depth"] is None:
            return 0.0
        return float(row["avg_depth"])

    def best(self) -> RunRecord | None:
        row = self._db.connection.execute("""
            SELECT id, player_name, seed, depth_reached, total_score, crash_cause,
                   duration_ms, timestamp
              FROM runs
             ORDER BY total_score DESC, depth_reached DESC, timestamp DESC
             LIMIT 1;
            """).fetchone()
        if row is None:
            return None
        return RunRecord(**dict(row))


class MetaRepository:
    """Generic key/value store for cross-run state (e.g. `bits`, settings)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, key: str, default: str | None = None) -> str | None:
        row = self._db.connection.execute(
            "SELECT value FROM meta_state WHERE key = ?;", (key,)
        ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set(self, key: str, value: str) -> None:
        with self._db.connection:
            self._db.connection.execute(
                """
                INSERT INTO meta_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )

    def get_int(self, key: str, default: int = 0) -> int:
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:  # pragma: no cover
            return default

    def set_int(self, key: str, value: int) -> None:
        self.set(key, str(value))


class UpgradeRepository:
    """Per-key meta-progression upgrade levels."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def get_level(self, key: str) -> int:
        get_upgrade(key)  # validates key
        row = self._db.connection.execute(
            "SELECT level FROM upgrades WHERE key = ?;", (key,)
        ).fetchone()
        return int(row["level"]) if row is not None else 0

    def set_level(self, key: str, level: int) -> None:
        upgrade = get_upgrade(key)
        if level < 0 or level > upgrade.max_level:
            raise ValueError(f"level {level} out of range for upgrade {key!r}")
        with self._db.connection:
            self._db.connection.execute(
                """
                INSERT INTO upgrades (key, level) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET level = excluded.level;
                """,
                (key, level),
            )

    def all_levels(self) -> dict[str, int]:
        rows = self._db.connection.execute("SELECT key, level FROM upgrades;").fetchall()
        levels = {row["key"]: int(row["level"]) for row in rows}
        # Backfill any catalog keys not yet in the DB with level 0.
        for upgrade in CATALOG:
            levels.setdefault(upgrade.key, 0)
        return levels
