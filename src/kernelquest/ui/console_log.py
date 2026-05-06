"""Oyun içi konsol logu: önem derecesine göre etiketlenmiş mesajların halka tamponu."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from kernelquest.core.config import CONSOLE_LOG_CAPACITY


class LogLevel(StrEnum):
    """Konsol girişi için önem derecesi etiketi."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRIT = "CRIT"


@dataclass(frozen=True)
class LogEntry:
    """Konsol logunda tek bir satır."""

    level: LogLevel
    message: str


class ConsoleLog:
    """`LogEntry` kayıtlarının sabit boyutlu halka tamponu (en eski ilk → en yeni son)."""

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
