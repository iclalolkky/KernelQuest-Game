"""Repositories — typed query helpers over `Database`."""

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
        distro_key: str | None = None,
        is_successful: bool = False,
    ) -> int:
        with self._db.connection:
            cursor = self._db.connection.execute(
                """
                INSERT INTO runs
                    (player_name, seed, depth_reached, total_score, crash_cause,
                     duration_ms, distro_key, is_successful)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    player_name,
                    seed,
                    depth_reached,
                    total_score,
                    crash_cause,
                    duration_ms,
                    distro_key,
                    1 if is_successful else 0,
                ),
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

    def best_with_score_fallback(self, scores: ScoreRepository) -> RunRecord | None:
        """Best run; if `runs` is empty, synthesize from the top score row."""
        existing = self.best()
        if existing is not None:
            return existing
        top = scores.top_n(1)
        if not top:
            return None
        s = top[0]
        return RunRecord(
            id=-1,
            player_name=s.player_name,
            seed=0,
            depth_reached=s.depth_reached,
            total_score=s.total_score,
            crash_cause=s.crash_cause,
            duration_ms=0,
            timestamp=s.timestamp,
        )


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


class DaemonRepository:
    """Owned + equipped daemons persisted across runs."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def owned(self) -> set[str]:
        rows = self._db.connection.execute("SELECT key FROM owned_daemons;").fetchall()
        return {row["key"] for row in rows}

    def grant(self, key: str) -> None:
        with self._db.connection:
            self._db.connection.execute(
                "INSERT OR IGNORE INTO owned_daemons (key) VALUES (?);", (key,)
            )

    def equipped(self) -> list[str]:
        rows = self._db.connection.execute(
            "SELECT key FROM equipped_daemons ORDER BY slot ASC;"
        ).fetchall()
        return [row["key"] for row in rows]

    def set_equipped(self, keys: list[str]) -> None:
        with self._db.connection:
            self._db.connection.execute("DELETE FROM equipped_daemons;")
            for slot, key in enumerate(keys):
                self._db.connection.execute(
                    "INSERT INTO equipped_daemons (slot, key) VALUES (?, ?);",
                    (slot, key),
                )


@dataclass(frozen=True)
class DailyRunRecord:
    """A row in the `daily_runs` table."""

    id: int
    run_date: str
    player_name: str
    seed: int
    depth_reached: int
    total_score: int
    crash_cause: str
    duration_ms: int
    timestamp: str


class DailyRunRepository:
    """CRUD for the date-locked daily challenge runs."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert(
        self,
        run_date: str,
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
                INSERT INTO daily_runs
                    (run_date, player_name, seed, depth_reached,
                     total_score, crash_cause, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_date,
                    player_name,
                    seed,
                    depth_reached,
                    total_score,
                    crash_cause,
                    duration_ms,
                ),
            )
        rowid = cursor.lastrowid
        if rowid is None:  # pragma: no cover
            raise RuntimeError("INSERT did not return a lastrowid")
        return rowid

    def top_for_date(self, run_date: str, n: int = 10) -> list[DailyRunRecord]:
        if n < 0:
            raise ValueError("n must be non-negative")
        rows = self._db.connection.execute(
            """
            SELECT id, run_date, player_name, seed, depth_reached, total_score,
                   crash_cause, duration_ms, timestamp
              FROM daily_runs
             WHERE run_date = ?
             ORDER BY total_score DESC, depth_reached DESC, timestamp ASC
             LIMIT ?;
            """,
            (run_date, n),
        ).fetchall()
        return [DailyRunRecord(**dict(row)) for row in rows]

    def has_played(self, run_date: str, player_name: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM daily_runs WHERE run_date = ? AND player_name = ? LIMIT 1;",
            (run_date, player_name),
        ).fetchone()
        return row is not None


class LoreRepository:
    """Phase 7 — persistent codex-unlock tracking.

    A lore key is "unlocked" exactly once; subsequent ``unlock`` calls are
    no-ops and return ``False`` so callers can detect the first-time event
    and route a `[KERNEL]`/`[init]` console line + Codex toast.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    def unlocked_keys(self) -> set[str]:
        rows = self._db.connection.execute("SELECT key FROM lore_unlocked;").fetchall()
        return {row["key"] for row in rows}

    def is_unlocked(self, key: str) -> bool:
        row = self._db.connection.execute(
            "SELECT 1 FROM lore_unlocked WHERE key = ? LIMIT 1;", (key,)
        ).fetchone()
        return row is not None

    def unlock(self, key: str) -> bool:
        """Insert ``key`` into the unlock set.

        Returns ``True`` if this call performed the unlock (i.e. it is the
        first time the player has seen this entry), ``False`` if it was
        already unlocked.
        """
        with self._db.connection:
            cursor = self._db.connection.execute(
                "INSERT OR IGNORE INTO lore_unlocked (key) VALUES (?);", (key,)
            )
        return cursor.rowcount > 0


@dataclass(frozen=True)
class IntelRow:
    """A single ``enemy_intel`` row."""

    species_key: str
    kills: int
    damage_dealt_to: int
    damage_received: int
    intel_level: int
    weakness_revealed: bool


class IntelRepository:
    """Phase 8 — per-species recognition / Bestiary tracking.

    Tier transitions:
    - 1 kill or 1 hit → intel_level >= 1
    - 5 kills OR 20 damage_dealt_to → intel_level >= 2 (weakness revealed)
    - 15 kills OR 60 damage_dealt_to → intel_level >= 3 (full info)
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    def _ensure_row(self, species_key: str) -> None:
        with self._db.connection:
            self._db.connection.execute(
                "INSERT OR IGNORE INTO enemy_intel (species_key) VALUES (?);",
                (species_key,),
            )

    def get(self, species_key: str) -> IntelRow:
        self._ensure_row(species_key)
        row = self._db.connection.execute(
            "SELECT species_key, kills, damage_dealt_to, damage_received,"
            " intel_level, weakness_revealed FROM enemy_intel WHERE species_key = ?;",
            (species_key,),
        ).fetchone()
        return IntelRow(
            species_key=row["species_key"],
            kills=row["kills"],
            damage_dealt_to=row["damage_dealt_to"],
            damage_received=row["damage_received"],
            intel_level=row["intel_level"],
            weakness_revealed=bool(row["weakness_revealed"]),
        )

    def all(self) -> list[IntelRow]:
        rows = self._db.connection.execute(
            "SELECT species_key, kills, damage_dealt_to, damage_received,"
            " intel_level, weakness_revealed FROM enemy_intel;"
        ).fetchall()
        return [
            IntelRow(
                species_key=r["species_key"],
                kills=r["kills"],
                damage_dealt_to=r["damage_dealt_to"],
                damage_received=r["damage_received"],
                intel_level=r["intel_level"],
                weakness_revealed=bool(r["weakness_revealed"]),
            )
            for r in rows
        ]

    @staticmethod
    def _tier_for(kills: int, damage_dealt_to: int) -> int:
        if kills >= 15 or damage_dealt_to >= 60:
            return 3
        if kills >= 5 or damage_dealt_to >= 20:
            return 2
        if kills >= 1 or damage_dealt_to >= 1:
            return 1
        return 0

    def _bump(
        self,
        species_key: str,
        *,
        kills_delta: int = 0,
        dmg_dealt_delta: int = 0,
        dmg_recv_delta: int = 0,
    ) -> int:
        self._ensure_row(species_key)
        with self._db.connection:
            self._db.connection.execute(
                "UPDATE enemy_intel SET kills = kills + ?,"
                " damage_dealt_to = damage_dealt_to + ?,"
                " damage_received = damage_received + ?"
                " WHERE species_key = ?;",
                (kills_delta, dmg_dealt_delta, dmg_recv_delta, species_key),
            )
            row = self._db.connection.execute(
                "SELECT kills, damage_dealt_to, intel_level FROM enemy_intel"
                " WHERE species_key = ?;",
                (species_key,),
            ).fetchone()
            new_tier = self._tier_for(row["kills"], row["damage_dealt_to"])
            if new_tier > row["intel_level"]:
                self._db.connection.execute(
                    "UPDATE enemy_intel SET intel_level = ?,"
                    " weakness_revealed = ? WHERE species_key = ?;",
                    (new_tier, 1 if new_tier >= 2 else 0, species_key),
                )
                return new_tier
            return int(row["intel_level"])

    def record_damage_to(self, species_key: str, damage: int) -> int:
        if not species_key or damage <= 0:
            return 0
        return self._bump(species_key, dmg_dealt_delta=damage)

    def record_damage_from(self, species_key: str, damage: int) -> int:
        if not species_key or damage <= 0:
            return 0
        return self._bump(species_key, dmg_recv_delta=damage)

    def record_kill(self, species_key: str) -> int:
        if not species_key:
            return 0
        return self._bump(species_key, kills_delta=1)

    def reveal(self, species_key: str) -> int:
        """Forcefully bump intel to tier 2 (used by `tcpdump`/`grep` daemons)."""
        if not species_key:
            return 0
        self._ensure_row(species_key)
        with self._db.connection:
            self._db.connection.execute(
                "UPDATE enemy_intel SET intel_level = MAX(intel_level, 2),"
                " weakness_revealed = 1 WHERE species_key = ?;",
                (species_key,),
            )
        return self.get(species_key).intel_level


class CombatLogRepository:
    """Phase 8 — lifetime per-(program, species) damage records."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert(
        self,
        *,
        program_key: str,
        species_key: str,
        damage: int,
        kills: int,
    ) -> None:
        with self._db.connection:
            self._db.connection.execute(
                "INSERT INTO combat_log (program_key, species_key, damage, kills)"
                " VALUES (?, ?, ?, ?);",
                (program_key, species_key, damage, kills),
            )

    def best_program_for(self, species_key: str) -> tuple[str, int] | None:
        row = self._db.connection.execute(
            "SELECT program_key, SUM(damage) AS total FROM combat_log"
            " WHERE species_key = ? GROUP BY program_key"
            " ORDER BY total DESC LIMIT 1;",
            (species_key,),
        ).fetchone()
        if row is None or row["total"] is None:
            return None
        return (row["program_key"], int(row["total"]))


# ---------------------------------------------------------------------------
# Phase 11 — distros, run milestones, skip tags
# ---------------------------------------------------------------------------


class DistroRepository:
    """Per-key unlock state for the Distro selection screen."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def ensure_seeded(self, distro_keys: list[str], first_unlocked: str) -> None:
        """Insert any missing distro rows; mark ``first_unlocked`` as unlocked."""
        with self._db.connection:
            for key in distro_keys:
                self._db.connection.execute(
                    "INSERT OR IGNORE INTO distros (key, name) VALUES (?, ?);",
                    (key, key),
                )
            self._db.connection.execute(
                "UPDATE distros SET unlocked_at = COALESCE(unlocked_at, CURRENT_TIMESTAMP)"
                " WHERE key = ?;",
                (first_unlocked,),
            )

    def is_unlocked(self, key: str) -> bool:
        row = self._db.connection.execute(
            "SELECT unlocked_at FROM distros WHERE key = ?;", (key,)
        ).fetchone()
        return bool(row and row["unlocked_at"])

    def unlocked_keys(self) -> set[str]:
        rows = self._db.connection.execute(
            "SELECT key FROM distros WHERE unlocked_at IS NOT NULL;"
        ).fetchall()
        return {str(row["key"]) for row in rows}

    def unlock(self, key: str) -> bool:
        """Mark ``key`` as unlocked; returns True iff this transitioned 0→1."""
        with self._db.connection:
            cursor = self._db.connection.execute(
                "UPDATE distros SET unlocked_at = CURRENT_TIMESTAMP"
                " WHERE key = ? AND unlocked_at IS NULL;",
                (key,),
            )
        return cursor.rowcount > 0


class MilestoneRepository:
    """Persists per-milestone results from a finished run."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert_many(
        self,
        run_id: int,
        rows: list[tuple[int, int, str, int, int, bool, bool]],
    ) -> None:
        """``rows`` = (release_index, milestone_index, kind, target, reached, skipped, cleared)."""
        if not rows:
            return
        with self._db.connection:
            self._db.connection.executemany(
                "INSERT INTO run_milestones"
                " (run_id, release_index, milestone_index, kind, target_score,"
                "  reached_score, was_skipped, was_cleared)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                [
                    (
                        run_id,
                        release_index,
                        milestone_index,
                        kind,
                        target,
                        reached,
                        1 if skipped else 0,
                        1 if cleared else 0,
                    )
                    for (
                        release_index,
                        milestone_index,
                        kind,
                        target,
                        reached,
                        skipped,
                        cleared,
                    ) in rows
                ],
            )

    def for_run(self, run_id: int) -> list[dict[str, object]]:
        rows = self._db.connection.execute(
            "SELECT release_index, milestone_index, kind, target_score, reached_score,"
            " was_skipped, was_cleared FROM run_milestones WHERE run_id = ?"
            " ORDER BY release_index, milestone_index;",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]


class SkipTagRepository:
    """Persists Skip Tags awarded during a run."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def insert(self, run_id: int, tag_key: str, used: bool) -> None:
        with self._db.connection:
            self._db.connection.execute(
                "INSERT INTO skip_tags (run_id, tag_key, used) VALUES (?, ?, ?);",
                (run_id, tag_key, 1 if used else 0),
            )

    def for_run(self, run_id: int) -> list[tuple[str, bool]]:
        rows = self._db.connection.execute(
            "SELECT tag_key, used FROM skip_tags WHERE run_id = ?;",
            (run_id,),
        ).fetchall()
        return [(str(row["tag_key"]), bool(row["used"])) for row in rows]
