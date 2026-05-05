"""In-game console log: ring-buffer of severity-tagged messages."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from kernelquest.core.config import CONSOLE_LOG_CAPACITY


class LogLevel(StrEnum):
    """Severity tag for a console entry."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRIT = "CRIT"


@dataclass(frozen=True)
class LogEntry:
    """A single line in the console log."""

    level: LogLevel
    message: str


class ConsoleLog:
    """Fixed-size ring buffer of `LogEntry` records (oldest first → newest last)."""

    def __init__(self, capacity: int = CONSOLE_LOG_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._entries: deque[LogEntry] = deque(maxlen=capacity)
        self._capacity = capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    def push(self, level: LogLevel, message: str) -> None:
        self._entries.append(LogEntry(level=level, message=message))

    def info(self, message: str) -> None:
        self.push(LogLevel.INFO, message)

    def warn(self, message: str) -> None:
        self.push(LogLevel.WARN, message)

    def error(self, message: str) -> None:
        self.push(LogLevel.ERROR, message)

    def crit(self, message: str) -> None:
        self.push(LogLevel.CRIT, message)

    # ----- Phase 7 — named voice helpers -----

    def voice(self, speaker: str, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Push a message tagged with an in-world speaker (e.g. ``KERNEL``).

        The speaker tag is preserved verbatim (case-sensitive) so lower-case
        voices like ``init`` render distinctly from upper-case system voices.
        """
        self.push(level, f"[{speaker.strip()}] {message}")

    def kernel(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.voice("KERNEL", message, level)

    def init(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.voice("init", message, level)

    def leak(self, message: str, level: LogLevel = LogLevel.CRIT) -> None:
        self.voice("THE_LEAK", message, level)

    def vendor(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.voice("VENDOR", message, level)

    def cron(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.voice("CRON", message, level)

    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
