"""Phase 9 — boss phase scripting framework.

Each boss declares an immutable tuple of :class:`BossPhase` thresholds. As
the boss takes damage, :func:`phase_for_hp` reports the current phase index;
when it advances the engine fires telegraph copy, screen-flash, and a music
overlay. Phases are deterministic given run seed → player damage sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class BossPhase:
    """One step in a boss script.

    Attributes:
        name: Internal name (e.g. ``"panic"``); also used in console log.
        hp_ratio: Phase activates when ``hp/max_hp <= hp_ratio``. Must be in
            descending order across the phase tuple.
        telegraph: Console copy emitted on entry.
        music_overlay: Optional stem key activated for this phase.
        damage_scale: Multiplier applied to outgoing boss damage.
    """

    name: str
    hp_ratio: float
    telegraph: str = ""
    music_overlay: str = ""
    damage_scale: float = 1.0


def phase_for_hp(phases: tuple[BossPhase, ...], hp: int, max_hp: int) -> int:
    """Return the current phase index for the given HP."""
    if max_hp <= 0 or not phases:
        return 0
    ratio = hp / max_hp
    idx = 0
    for i, ph in enumerate(phases):
        if ratio <= ph.hp_ratio:
            idx = i
    return idx


KERNEL_PANIC_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="boot", hp_ratio=1.0, telegraph="kernel: warming up..."),
    BossPhase(
        name="oops",
        hp_ratio=0.66,
        telegraph="kernel: Oops detected. page tables blink.",
        music_overlay="boss",
    ),
    BossPhase(
        name="panic",
        hp_ratio=0.33,
        telegraph="!! KERNEL PANIC !! pid 1 is thrashing.",
        music_overlay="boss",
        damage_scale=1.4,
    ),
)

SEGFAULT_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="trace", hp_ratio=1.0, telegraph="segfault: address sampled."),
    BossPhase(
        name="dump",
        hp_ratio=0.5,
        telegraph="segfault: core dumping...",
        music_overlay="boss",
        damage_scale=1.25,
    ),
)

THE_LEAK_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="seep", hp_ratio=1.0, telegraph="the leak: bytes seep through."),
    BossPhase(
        name="bleed",
        hp_ratio=0.66,
        telegraph="the leak: arena corruption accelerates.",
        music_overlay="boss",
    ),
    BossPhase(
        name="flood",
        hp_ratio=0.33,
        telegraph="the leak: free() forgot. flooding.",
        music_overlay="boss",
        damage_scale=1.5,
    ),
)

DEADLOCK_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="wait", hp_ratio=1.0, telegraph="deadlock: each twin waits."),
    BossPhase(
        name="spin",
        hp_ratio=0.5,
        telegraph="deadlock: spin contention!",
        music_overlay="boss",
        damage_scale=1.2,
    ),
)

HYDRA_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="probe", hp_ratio=1.0, telegraph="hydra: probing privilege rings."),
    BossPhase(
        name="root",
        hp_ratio=0.66,
        telegraph="hydra: root acquired.",
        music_overlay="boss",
    ),
    BossPhase(
        name="kernel",
        hp_ratio=0.33,
        telegraph="hydra: kernel-mode!",
        music_overlay="boss",
        damage_scale=1.3,
    ),
)

BUFFER_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="fill", hp_ratio=1.0, telegraph="buffer: writing past EOF."),
    BossPhase(
        name="overflow",
        hp_ratio=0.5,
        telegraph="buffer: stack smashed!",
        music_overlay="boss",
        damage_scale=1.3,
    ),
)

ZERO_DAY_PHASES: Final[tuple[BossPhase, ...]] = (
    BossPhase(name="cve_pending", hp_ratio=1.0, telegraph="zero-day: CVE pending."),
    BossPhase(
        name="exploit",
        hp_ratio=0.66,
        telegraph="zero-day: exploit chained.",
        music_overlay="boss",
    ),
    BossPhase(
        name="patch_too_late",
        hp_ratio=0.33,
        telegraph="zero-day: patch too late.",
        music_overlay="boss",
        damage_scale=1.6,
    ),
)


PHASES_BY_SPECIES: Final[dict[str, tuple[BossPhase, ...]]] = {
    "kernel_panic": KERNEL_PANIC_PHASES,
    "segfault": SEGFAULT_PHASES,
    "the_leak": THE_LEAK_PHASES,
    "deadlock_twin": DEADLOCK_PHASES,
    "rootkit_hydra": HYDRA_PHASES,
    "buffer_overflow": BUFFER_PHASES,
    "zero_day": ZERO_DAY_PHASES,
}


def phases_for(species_key: str) -> tuple[BossPhase, ...]:
    return PHASES_BY_SPECIES.get(species_key, ())


__all__ = [
    "BossPhase",
    "phase_for_hp",
    "phases_for",
    "KERNEL_PANIC_PHASES",
    "SEGFAULT_PHASES",
    "THE_LEAK_PHASES",
    "DEADLOCK_PHASES",
    "HYDRA_PHASES",
    "BUFFER_PHASES",
    "ZERO_DAY_PHASES",
    "PHASES_BY_SPECIES",
]
