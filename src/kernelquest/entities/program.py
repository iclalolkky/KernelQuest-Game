"""Programs — active, card-like abilities the player can fire mid-run.

A `Program` is data; runtime instances live as `ProgramSlot` objects on the
player so they can carry per-run state (cooldowns, charges). Effects are
resolved by `kernelquest.systems.programs.execute_program`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Program:
    """Static definition of a program / active ability."""

    key: str
    label: str
    description: str
    cycle_cost: int
    cooldown: int
    max_charges: int


@dataclass
class ProgramSlot:
    """A program owned by the player, with its mutable per-run state."""

    program: Program
    charges: int
    cooldown_remaining: int = 0

    @property
    def ready(self) -> bool:
        return self.charges > 0 and self.cooldown_remaining == 0

    def consume(self) -> None:
        self.charges = max(0, self.charges - 1)
        self.cooldown_remaining = self.program.cooldown

    def tick(self) -> None:
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1


PROGRAM_FORK = Program(
    key="fork",
    label="fork()",
    description="Spawn a 1-turn decoy that draws the nearest enemy.",
    cycle_cost=2,
    cooldown=4,
    max_charges=2,
)

PROGRAM_KILL_DASH9 = Program(
    key="kill9",
    label="kill -9",
    description="Instakill an adjacent non-boss enemy. Heavy cost.",
    cycle_cost=3,
    cooldown=5,
    max_charges=1,
)

PROGRAM_SUDO = Program(
    key="sudo",
    label="sudo",
    description="Your next attack deals triple damage.",
    cycle_cost=1,
    cooldown=3,
    max_charges=2,
)

PROGRAM_GREP = Program(
    key="grep",
    label="grep",
    description="Reveal the entire sector for one turn.",
    cycle_cost=1,
    cooldown=4,
    max_charges=2,
)

PROGRAM_NICE = Program(
    key="nice",
    label="nice",
    description="All enemies skip their next two turns.",
    cycle_cost=2,
    cooldown=6,
    max_charges=1,
)


CATALOG: tuple[Program, ...] = (
    PROGRAM_FORK,
    PROGRAM_KILL_DASH9,
    PROGRAM_SUDO,
    PROGRAM_GREP,
    PROGRAM_NICE,
)


def get_program(key: str) -> Program:
    for program in CATALOG:
        if program.key == key:
            return program
    raise KeyError(f"unknown program: {key!r}")


def starter_loadout() -> list[ProgramSlot]:
    """Return the default 3-slot loadout for a fresh run."""
    keys = ("kill9", "sudo", "grep")
    return [ProgramSlot(program=get_program(k), charges=get_program(k).max_charges) for k in keys]


__all__ = [
    "CATALOG",
    "Program",
    "ProgramSlot",
    "get_program",
    "starter_loadout",
]
