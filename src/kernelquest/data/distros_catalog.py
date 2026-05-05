"""Phase 11 — Distro catalog (the player-facing "decks").

A *Distro* is a curated starting bundle: programs, daemons, base stats, a
vendor-tag bias, and a single signature mechanic ("joker") that shapes the
build.  The list is sequential — clearing a successful run unlocks the next
distro in the chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True)
class Distro:
    """Static metadata for a starting build."""

    key: str
    name: str
    description: str
    bonus_ram: int = 0
    bonus_cycles: int = 0
    bonus_cache: int = 0
    bonus_damage: int = 0
    starter_program_keys: tuple[str, ...] = ()
    starter_daemon_keys: tuple[str, ...] = ()
    vendor_tag_bias: tuple[str, ...] = ()
    bits_kill_multiplier: float = 1.0
    program_cycle_surcharge: int = 0
    enemies_first: bool = False
    free_move_every: int = 0  # 0 = disabled
    ram_regen_disabled: bool = False
    random_starter_daemons: int = 0
    signature: str = ""
    unlock_hint: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


# Order matters — index N + 1 unlocks after a successful run with index N.
DISTROS: Final[tuple[Distro, ...]] = (
    Distro(
        key="vanilla",
        name="Vanilla",
        description="Baseline starting kit. No bonuses, no penalties.",
        starter_program_keys=("ls", "kill", "sudo"),
        signature="No twist — the reference build.",
        unlock_hint="Always available.",
        tags=("balanced",),
    ),
    Distro(
        key="minimal",
        name="Minimal",
        description="Fewer cycles, but +50% bits from kills.",
        bonus_cycles=-2,
        bits_kill_multiplier=1.5,
        starter_program_keys=("ls", "kill"),
        signature="Lean ops: every kill banks more bits.",
        unlock_hint="Clear a run on Vanilla.",
        tags=("economy",),
    ),
    Distro(
        key="hardened",
        name="Hardened",
        description="+20 starting RAM, programs cost +1 cycle.",
        bonus_ram=20,
        program_cycle_surcharge=1,
        starter_program_keys=("ls", "kill", "kill -9"),
        signature="Defensive build: tankier but slower programs.",
        unlock_hint="Clear a run on Minimal.",
        tags=("defense",),
    ),
    Distro(
        key="realtime",
        name="Realtime",
        description="Enemies act first, but +1 free move every 5 turns.",
        enemies_first=True,
        free_move_every=5,
        starter_program_keys=("ls", "sudo", "strace"),
        signature="Reactive ops with periodic free turns.",
        unlock_hint="Clear a run on Hardened.",
        tags=("tempo",),
    ),
    Distro(
        key="bleeding_edge",
        name="Bleeding-Edge",
        description="Start with 2 random Daemons; RAM regen disabled.",
        random_starter_daemons=2,
        ram_regen_disabled=True,
        starter_program_keys=("ls", "kill", "fork"),
        signature="Two random daemons online from t=0.",
        unlock_hint="Clear a run on Realtime.",
        tags=("daemon",),
    ),
    Distro(
        key="recovery",
        name="Recovery",
        description="Built around init(0). Starts with cron + restore --from-snapshot.",
        starter_program_keys=("ls", "kill", "restore"),
        starter_daemon_keys=("cron",),
        signature="restore --from-snapshot rewinds last sector.",
        unlock_hint="Clear a run on Bleeding-Edge.",
        tags=("memory",),
    ),
)


_BY_KEY: Final[dict[str, Distro]] = {d.key: d for d in DISTROS}


def all_distros() -> tuple[Distro, ...]:
    return DISTROS


def get_distro(key: str) -> Distro:
    """Return the :class:`Distro` for ``key`` or raise ``KeyError``."""
    return _BY_KEY[key]


def maybe_get(key: str) -> Distro | None:
    return _BY_KEY.get(key)


def next_in_chain(key: str) -> Distro | None:
    """Return the distro immediately after ``key`` in the unlock chain."""
    for i, d in enumerate(DISTROS):
        if d.key == key and i + 1 < len(DISTROS):
            return DISTROS[i + 1]
    return None


def first_distro_key() -> str:
    return DISTROS[0].key
