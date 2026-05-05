"""Phase 7 — narrative lore catalog.

Single source of truth for every codex entry, story beat, intro/ending
script, and the named-voice console tags. UI / data layers consume this.

Entries are unlocked by `unlock_condition` strings interpreted by
`engine._unlock_lore_for(event)`:

- ``first_boot``       — first launch, fired during the intro cutscene
- ``first_kill``       — first malware terminated
- ``first_boss``       — first boss defeated
- ``first_pickup``     — first item picked up
- ``first_descent``    — first sector cleared (depth >= 2)
- ``first_crash``      — first run that ended in a core dump
- ``sector_5``         — reaches sector 0x05
- ``sector_10``        — reaches sector 0x0A
- ``sector_15``        — reaches sector 0x0F
- ``cause_<crash>``    — game-over with a specific crash_cause label
- ``true_ending``      — successful run (per Phase 11 success criteria)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class LoreEntry:
    """A single codex entry."""

    key: str
    title: str
    body: str
    unlock_condition: str


CATALOG: Final[tuple[LoreEntry, ...]] = (
    LoreEntry(
        key="boot_sequence",
        title="0x00 — Boot Sequence",
        body=(
            "The kernel forked one last process from the snapshot.\n"
            "Its name is init(0). Its job is to reach /proc/1 before the leak\n"
            "consumes the last megabyte of free RAM."
        ),
        unlock_condition="first_boot",
    ),
    LoreEntry(
        key="first_contact",
        title="0x01 — First Contact",
        body=(
            "The first malware did not look hostile.\n"
            "It looked like leftover heap that had forgotten how to die.\n"
            "init(0) terminated it without ceremony."
        ),
        unlock_condition="first_kill",
    ),
    LoreEntry(
        key="first_pickup",
        title="0x02 — Salvage",
        body=(
            "Garbage collectors are still running, just slower than the leak.\n"
            "Every recovered packet buys init(0) another handful of cycles."
        ),
        unlock_condition="first_pickup",
    ),
    LoreEntry(
        key="first_descent",
        title="0x03 — Descent",
        body=(
            "Each sector is a deeper page in the address space.\n"
            "The deeper you go, the older the memory — and the more "
            "fragmented the leak's grip on it."
        ),
        unlock_condition="first_descent",
    ),
    LoreEntry(
        key="first_boss",
        title="0x04 — A Process with Privileges",
        body=(
            "Some processes refuse SIGTERM. They demand SIGKILL.\n"
            "init(0) learned this the hard way."
        ),
        unlock_condition="first_boss",
    ),
    LoreEntry(
        key="first_crash",
        title="0x05 — Core Dump",
        body=(
            "init(0) was reforked from the snapshot.\n"
            "The leak does not get a snapshot. That is the only edge we have."
        ),
        unlock_condition="first_crash",
    ),
    LoreEntry(
        key="sector_5",
        title="0x06 — User Space",
        body=(
            "Past sector 0x05 the addresses stop looking familiar.\n"
            "Whatever ran here last was not a daemon."
        ),
        unlock_condition="sector_5",
    ),
    LoreEntry(
        key="sector_10",
        title="0x07 — Kernel Space",
        body=(
            "The walls are made of dirty pages and old kmalloc tags.\n"
            "Something is breathing in the swap."
        ),
        unlock_condition="sector_10",
    ),
    LoreEntry(
        key="sector_15",
        title="0x08 — Edge of /proc",
        body=("init(0) can see the heartbeat of /proc/1 from here.\n" "So can THE_LEAK."),
        unlock_condition="sector_15",
    ),
    LoreEntry(
        key="cause_logic_bomb",
        title="0x09 — On Logic Bombs",
        body=(
            "Stand adjacent. Detonate. The blast radius is exactly one tile\n"
            "wider than your nerve."
        ),
        unlock_condition="cause_Logic Bomb",
    ),
    LoreEntry(
        key="cause_kernel_panic",
        title="0x0A — On Kernel Panics",
        body=("A KernelPanic is not malware. It is the kernel begging to die.\n" "Help it."),
        unlock_condition="cause_Kernel Panic",
    ),
    LoreEntry(
        key="cause_segfault",
        title="0x0B — On Segmentation Faults",
        body=("SegFault does not aim. SegFault arrives.\n" "Track the address, not the sprite."),
        unlock_condition="cause_SegFault",
    ),
    LoreEntry(
        key="true_ending",
        title="0xFF — End of File",
        body=(
            "init(0) reached /proc/1. The leak was freed back to the heap.\n"
            "Uptime restored. Snapshot updated.\n"
            "The kernel slept, for the first time in 50 000 cycles."
        ),
        unlock_condition="true_ending",
    ),
)


_BY_KEY: Final[dict[str, LoreEntry]] = {entry.key: entry for entry in CATALOG}
_BY_CONDITION: Final[dict[str, LoreEntry]] = {entry.unlock_condition: entry for entry in CATALOG}


def get(key: str) -> LoreEntry:
    """Return the entry with that key, or raise `KeyError`."""
    return _BY_KEY[key]


def for_condition(condition: str) -> LoreEntry | None:
    """Return the entry that maps to ``condition``, or ``None``."""
    return _BY_CONDITION.get(condition)


def all_keys() -> tuple[str, ...]:
    return tuple(entry.key for entry in CATALOG)


# ----- Cinematic scripts -----


@dataclass(frozen=True)
class CinematicFrame:
    """A single frame in a cutscene."""

    title: str
    body: tuple[str, ...]
    duration_s: float = 3.0


INTRO_FRAMES: Final[tuple[CinematicFrame, ...]] = (
    CinematicFrame(
        title="[BIOS]",
        body=("POST: ok", "memtest: 1 error (ignored)", "loading kernel..."),
        duration_s=2.0,
    ),
    CinematicFrame(
        title="[KERNEL]",
        body=(
            "scheduler online",
            "daemons: cron ok / sshd ok / oom-killer ok",
            "uptime: 49 999 998 ms",
        ),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[KERNEL]",
        body=(
            "malloc(): pid 0 — never returned",
            "malloc(): pid 0 — never returned",
            "malloc(): pid 0 — never returned ...",
        ),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[!! PANIC !!]",
        body=(
            "free RAM:  0.4 MB",
            "leak rate: +1 MB / cycle",
            "forking last-known-good snapshot ...",
        ),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[init(0)]",
        body=("> spawned", "> mission: reach /proc/1", "> do not become the next leak"),
        duration_s=2.5,
    ),
)

ENDING_FRAMES: Final[tuple[CinematicFrame, ...]] = (
    CinematicFrame(
        title="[init(0)]",
        body=("/proc/1 reached", "leak located: pid 0xFFFF...FFFE", "issuing free()..."),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[THE_LEAK]",
        body=("0xFFFF... CAN_NOT...", "0xFFFF... WILL_NOT...", "0xFFFF... ()"),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[KERNEL]",
        body=("heap consolidated", "uptime: restored", "snapshot: updated"),
        duration_s=2.5,
    ),
    CinematicFrame(
        title="[init(0)]",
        body=("> mission complete", "> shutting down recovery context", "> goodnight, kernel"),
        duration_s=3.0,
    ),
)


# ----- Stack-trace interstitials (between sectors) -----

STACK_TRACE_LINES: Final[tuple[tuple[str, str], ...]] = (
    ("[init]", "another page consumed. the leak still grows."),
    ("[KERNEL]", "sector mapped. proceed with caution."),
    ("[CRON]", "every 10 cycles I restore 5 RAM. you're welcome."),
    ("[init]", "i can hear /proc/1 from here. faintly."),
    ("[KERNEL]", "fragmentation rising. defragment via combat."),
    ("[THE_LEAK]", "0xFFFF... HEAP_GROWS."),
    ("[init]", "if i become the next leak, snapshot the kernel anyway."),
    ("[KERNEL]", "OOM-killer is offline. you're on your own."),
    ("[CRON]", "tip: bump-attack from full cycles for clean kills."),
    ("[init]", "i was forked five seconds ago and i am tired."),
)


__all__ = [
    "LoreEntry",
    "CinematicFrame",
    "CATALOG",
    "INTRO_FRAMES",
    "ENDING_FRAMES",
    "STACK_TRACE_LINES",
    "get",
    "for_condition",
    "all_keys",
]
