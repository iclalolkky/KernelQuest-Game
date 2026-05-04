"""Daemons — passive modifiers (the OS-flavored "Joker" slot).

Daemons buff the player while equipped. Effects are pure functions invoked
by hooks in `kernelquest.systems.daemons`. Synergies trigger when 2+ equipped
daemons share a tag.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tags used for synergy detection.
TAG_ARITHMETIC = "arithmetic"
TAG_IO = "io"
TAG_NETWORK = "network"
TAG_MEMORY = "memory"
TAG_SIGNAL = "signal"


@dataclass(frozen=True)
class Daemon:
    """Static definition of a passive daemon."""

    key: str
    label: str
    description: str
    tags: tuple[str, ...]


DAEMON_CRON = Daemon(
    key="cron",
    label="cron",
    description="+5 RAM every 10 turns.",
    tags=(TAG_SIGNAL,),
)

DAEMON_SWAPD = Daemon(
    key="swapd",
    label="swapd",
    description="Pickups give bonus score equal to current combo.",
    tags=(TAG_MEMORY, TAG_IO),
)

DAEMON_OOM_KILLER = Daemon(
    key="oom-killer",
    label="oom-killer",
    description="When RAM is critical, kills deal +50% damage.",
    tags=(TAG_MEMORY, TAG_SIGNAL),
)

DAEMON_TCPDUMP = Daemon(
    key="tcpdump",
    label="tcpdump",
    description="See enemies through fog of war.",
    tags=(TAG_NETWORK, TAG_IO),
)

DAEMON_NICED = Daemon(
    key="niced",
    label="niced",
    description="+1 cycle each turn while no enemy is in sight.",
    tags=(TAG_ARITHMETIC,),
)


CATALOG: tuple[Daemon, ...] = (
    DAEMON_CRON,
    DAEMON_SWAPD,
    DAEMON_OOM_KILLER,
    DAEMON_TCPDUMP,
    DAEMON_NICED,
)


def get_daemon(key: str) -> Daemon:
    for daemon in CATALOG:
        if daemon.key == key:
            return daemon
    raise KeyError(f"unknown daemon: {key!r}")


def starter_daemon() -> Daemon:
    """The single daemon every player owns from their first run."""
    return DAEMON_CRON


def synergy_count(equipped: list[Daemon]) -> dict[str, int]:
    """Return a tag → count of equipped daemons that share that tag."""
    counts: dict[str, int] = {}
    for daemon in equipped:
        for tag in daemon.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return {tag: c for tag, c in counts.items() if c >= 2}


__all__ = [
    "CATALOG",
    "Daemon",
    "TAG_ARITHMETIC",
    "TAG_IO",
    "TAG_MEMORY",
    "TAG_NETWORK",
    "TAG_SIGNAL",
    "get_daemon",
    "starter_daemon",
    "synergy_count",
]
