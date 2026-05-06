"""Şema geçişleri.

Geçişler ekleme-yalnızdır ve sırayla çalışır. Her giriş, `name` `NNN_description`
kurallarını takip eden bir `(name, sql)` demetidir.
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
]
