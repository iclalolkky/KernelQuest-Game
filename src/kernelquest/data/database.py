"""SQLite I/O. This is the **only** module allowed to import `sqlite3`."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from types import TracebackType

from kernelquest.data.migrations import MIGRATIONS

log = logging.getLogger(__name__)


class Database:
    """Thin wrapper around `sqlite3.Connection` with migration support."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON;")

    # ----- factories -----

    @classmethod
    def open(cls, path: str | Path) -> Database:
        """Open (or create) a database file and run pending migrations."""
        conn = sqlite3.connect(str(path))
        db = cls(conn)
        db.run_migrations()
        return db

    @classmethod
    def in_memory(cls) -> Database:
        """In-memory database for tests."""
        conn = sqlite3.connect(":memory:")
        db = cls(conn)
        db.run_migrations()
        return db

    # ----- migrations -----

    def run_migrations(self) -> None:
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name       TEXT PRIMARY KEY,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """)
        applied: set[str] = {
            row["name"] for row in self.connection.execute("SELECT name FROM schema_migrations;")
        }
        for name, sql in MIGRATIONS:
            if name in applied:
                continue
            log.info("Applying migration %s", name)
            with self.connection:
                self.connection.executescript(sql)
                self.connection.execute("INSERT INTO schema_migrations (name) VALUES (?);", (name,))

    # ----- lifecycle -----

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
