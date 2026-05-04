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

    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
