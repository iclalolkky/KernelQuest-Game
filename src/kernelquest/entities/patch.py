"""Patch Notes — run-modifier cards offered between sectors.

Each `Patch` stacks with the previous ones via additive modifiers stored in
`PatchEffects`. The engine consults these effects when computing damage,
loot, and starting cycles.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class PatchEffects:
    """Accumulator for patch modifiers active during the current run."""

    player_damage_mult: float = 1.0
    enemy_damage_mult: float = 1.0
    enemy_hp_mult: float = 1.0
    enemy_speed_bonus: int = 0  # extra random move per turn at +1
    item_drop_mult: float = 1.0
    ram_regen_mult: float = 1.0
    score_mult: float = 1.0
    starting_cycles_bonus: int = 0


@dataclass(frozen=True)
class Patch:
    """A patch-note card the player can pick to modify the current run."""

    key: str
    label: str
    description: str
    apply: Callable[[PatchEffects], None]


def _glass_cannon(effects: PatchEffects) -> None:
    effects.player_damage_mult *= 1.4
    effects.enemy_damage_mult *= 1.4


def _speed_demon(effects: PatchEffects) -> None:
    effects.enemy_hp_mult *= 0.85
    effects.enemy_speed_bonus += 1


def _hoarder(effects: PatchEffects) -> None:
    effects.item_drop_mult *= 2.0
    effects.ram_regen_mult *= 0.5


def _overclock(effects: PatchEffects) -> None:
    effects.starting_cycles_bonus += 1
    effects.score_mult *= 1.15


def _shielded(effects: PatchEffects) -> None:
    effects.enemy_damage_mult *= 0.75
    effects.score_mult *= 0.9


def _berserker(effects: PatchEffects) -> None:
    effects.player_damage_mult *= 1.6
    effects.ram_regen_mult *= 0.5


CATALOG: tuple[Patch, ...] = (
    Patch(
        key="glass-cannon",
        label="Glass Cannon",
        description="+40% player damage, +40% enemy damage.",
        apply=_glass_cannon,
    ),
    Patch(
        key="speed-demon",
        label="Speed Demon",
        description="Enemies have -15% HP but move +1 extra per turn.",
        apply=_speed_demon,
    ),
    Patch(
        key="hoarder",
        label="Hoarder",
        description="2× item drops, but RAM regen halved.",
        apply=_hoarder,
    ),
    Patch(
        key="overclock",
        label="Overclock",
        description="+1 starting cycle and +15% score per kill.",
        apply=_overclock,
    ),
    Patch(
        key="shielded",
        label="Shielded",
        description="-25% enemy damage, but score gain reduced 10%.",
        apply=_shielded,
    ),
    Patch(
        key="berserker",
        label="Berserker",
        description="+60% player damage, -50% RAM regen.",
        apply=_berserker,
    ),
)


def get_patch(key: str) -> Patch:
    for patch in CATALOG:
        if patch.key == key:
            return patch
    raise KeyError(f"unknown patch: {key!r}")


@dataclass
class PatchState:
    """Run-scoped collection of selected patches."""

    selected: list[Patch] = field(default_factory=list)

    def add(self, patch: Patch) -> None:
        self.selected.append(patch)

    def effects(self) -> PatchEffects:
        out = PatchEffects()
        for patch in self.selected:
            patch.apply(out)
        return out


__all__ = ["CATALOG", "Patch", "PatchEffects", "PatchState", "get_patch"]
