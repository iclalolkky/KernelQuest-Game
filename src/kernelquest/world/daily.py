"""Daily-seed helpers — deterministic seed derived from the calendar date."""

from __future__ import annotations

import datetime as _dt
import hashlib


def today_iso() -> str:
    """ISO-8601 date string in UTC, e.g. ``'2026-05-05'``."""
    return _dt.datetime.now(tz=_dt.UTC).date().isoformat()


def seed_for_date(date_iso: str) -> int:
    """Deterministic 31-bit seed derived from an ISO date string."""
    digest = hashlib.sha256(date_iso.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def today_seed() -> int:
    return seed_for_date(today_iso())


__all__ = ["seed_for_date", "today_iso", "today_seed"]
