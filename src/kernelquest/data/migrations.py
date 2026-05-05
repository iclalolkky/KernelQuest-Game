"""Schema migrations.

Migrations are append-only and run in order. Each entry is a `(name, sql)`
tuple where `name` follows the `NNN_description` convention.
"""

from __future__ import annotations

from typing import Final

MIGRATIONS: Final[list[tuple[str, str]]] = [
    (
        "001_init",
        """
        CREATE TABLE IF NOT EXISTS scores (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name   TEXT     NOT NULL,
            depth_reached INTEGER  NOT NULL,
            total_score   INTEGER  NOT NULL,
            crash_cause   TEXT     NOT NULL,
            timestamp     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_scores_total_score
            ON scores (total_score DESC);
        """,
    ),
    (
        "002_runs",
        """
        CREATE TABLE IF NOT EXISTS runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name   TEXT     NOT NULL,
            seed          INTEGER  NOT NULL,
            depth_reached INTEGER  NOT NULL,
            total_score   INTEGER  NOT NULL,
            crash_cause   TEXT     NOT NULL,
            duration_ms   INTEGER  NOT NULL,
            timestamp     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_runs_total_score
            ON runs (total_score DESC);
        """,
    ),
    (
        "003_meta",
        """
        CREATE TABLE IF NOT EXISTS meta_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS upgrades (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            key   TEXT    NOT NULL UNIQUE,
            level INTEGER NOT NULL DEFAULT 0
        );
        """,
    ),
    (
        "004_phase5_backfill",
        """
        -- Backfill `runs` from any pre-Phase-4 `scores` rows so the Stats screen
        -- doesn't undercount the player's history.
        INSERT INTO runs
            (player_name, seed, depth_reached, total_score, crash_cause, duration_ms, timestamp)
        SELECT s.player_name, 0, s.depth_reached, s.total_score, s.crash_cause, 0, s.timestamp
          FROM scores s
         WHERE NOT EXISTS (
             SELECT 1 FROM runs r
              WHERE r.player_name   = s.player_name
                AND r.depth_reached = s.depth_reached
                AND r.total_score   = s.total_score
                AND r.crash_cause   = s.crash_cause
                AND r.timestamp     = s.timestamp
         );
        """,
    ),
    (
        "005_phase5_meta",
        """
        CREATE TABLE IF NOT EXISTS owned_daemons (
            key TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS equipped_daemons (
            slot INTEGER PRIMARY KEY,
            key  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date      TEXT     NOT NULL,
            player_name   TEXT     NOT NULL,
            seed          INTEGER  NOT NULL,
            depth_reached INTEGER  NOT NULL,
            total_score   INTEGER  NOT NULL,
            crash_cause   TEXT     NOT NULL,
            duration_ms   INTEGER  NOT NULL,
            timestamp     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_daily_runs_date_score
            ON daily_runs (run_date, total_score DESC);
        """,
    ),
    (
        "006_phase7_lore",
        """
        -- Phase 7 — narrative codex unlocks. Append-only tracking of which
        -- lore entries the player has discovered, with a timestamp for the
        -- "first unlocked" UX (e.g. NEW! badge in the Codex screen).
        CREATE TABLE IF NOT EXISTS lore_unlocked (
            key          TEXT PRIMARY KEY,
            unlocked_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
]
