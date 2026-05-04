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
]
