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
    # Phase 5++: extended modifier surface for richer Patch variety.
    fov_radius_bonus: int = 0
    extra_enemies_per_sector: int = 0
    pickup_score_mult: float = 1.0
    ram_per_action: int = 0  # self-damage every action
    starting_ram_bonus: int = 0
    cycle_refund_on_pickup: int = 0
    combo_decay_bonus: int = 0  # extra idle turns before combo breaks
    boss_damage_mult: float = 1.0  # specifically vs KernelPanic / SegFault


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


def _dark_mode(effects: PatchEffects) -> None:
    effects.fov_radius_bonus -= 2
    effects.score_mult *= 1.5


def _fragmented(effects: PatchEffects) -> None:
    effects.extra_enemies_per_sector += 2
    effects.item_drop_mult *= 1.5
    effects.score_mult *= 1.2


def _noatime(effects: PatchEffects) -> None:
    effects.cycle_refund_on_pickup += 1
    effects.pickup_score_mult *= 1.5


def _thermal_throttle(effects: PatchEffects) -> None:
    effects.enemy_damage_mult *= 0.7
    effects.player_damage_mult *= 0.85


def _kernel_bypass(effects: PatchEffects) -> None:
    effects.starting_cycles_bonus += 2
    effects.boss_damage_mult *= 1.5


def _lazy_eval(effects: PatchEffects) -> None:
    effects.combo_decay_bonus += 3
    effects.score_mult *= 1.1


def _page_fault(effects: PatchEffects) -> None:
    effects.player_damage_mult *= 1.5
    effects.ram_per_action += 1


def _swap_thrash(effects: PatchEffects) -> None:
    effects.ram_regen_mult *= 2.0
    effects.player_damage_mult *= 0.85


def _stack_trace(effects: PatchEffects) -> None:
    effects.fov_radius_bonus += 2
    effects.player_damage_mult *= 1.1
    effects.item_drop_mult *= 0.85


def _root_kit(effects: PatchEffects) -> None:
    effects.boss_damage_mult *= 2.0
    effects.enemy_damage_mult *= 1.25


def _heap_spray(effects: PatchEffects) -> None:
    effects.item_drop_mult *= 2.5
    effects.enemy_hp_mult *= 1.15


def _zero_copy(effects: PatchEffects) -> None:
    effects.cycle_refund_on_pickup += 1
    effects.starting_cycles_bonus += 1
    effects.score_mult *= 0.9


def _opportunistic(effects: PatchEffects) -> None:
    effects.pickup_score_mult *= 2.0
    effects.combo_decay_bonus += 2


def _ddos(effects: PatchEffects) -> None:
    effects.extra_enemies_per_sector += 4
    effects.score_mult *= 1.6
    effects.starting_ram_bonus += 25


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
    Patch(
        key="dark-mode",
        label="Dark Mode",
        description="-2 FoV radius, but +50% score gain.",
        apply=_dark_mode,
    ),
    Patch(
        key="fragmented",
        label="Fragmented Disk",
        description="+2 enemies per sector, +50% item drops, +20% score.",
        apply=_fragmented,
    ),
    Patch(
        key="noatime",
        label="noatime",
        description="Pickups refund 1 cycle and grant +50% score.",
        apply=_noatime,
    ),
    Patch(
        key="thermal-throttle",
        label="Thermal Throttle",
        description="-30% enemy damage, but -15% player damage.",
        apply=_thermal_throttle,
    ),
    Patch(
        key="kernel-bypass",
        label="Kernel Bypass",
        description="+2 starting cycles and +50% damage to bosses.",
        apply=_kernel_bypass,
    ),
    Patch(
        key="lazy-eval",
        label="Lazy Evaluation",
        description="Combo holds for +3 extra idle turns; +10% score.",
        apply=_lazy_eval,
    ),
    Patch(
        key="page-fault",
        label="Page Fault",
        description="+50% damage, but every action costs 1 RAM.",
        apply=_page_fault,
    ),
    Patch(
        key="swap-thrash",
        label="Swap Thrash",
        description="2× RAM regen, but -15% damage.",
        apply=_swap_thrash,
    ),
    Patch(
        key="stack-trace",
        label="Stack Trace",
        description="+2 FoV, +10% damage, -15% item drops.",
        apply=_stack_trace,
    ),
    Patch(
        key="root-kit",
        label="Root Kit",
        description="2× boss damage, but +25% enemy damage.",
        apply=_root_kit,
    ),
    Patch(
        key="heap-spray",
        label="Heap Spray",
        description="2.5× item drops, but enemies +15% HP.",
        apply=_heap_spray,
    ),
    Patch(
        key="zero-copy",
        label="Zero Copy",
        description="+1 starting cycle, pickups refund cycles, -10% score.",
        apply=_zero_copy,
    ),
    Patch(
        key="opportunistic",
        label="Opportunistic Locking",
        description="2× pickup score, combo holds +2 turns.",
        apply=_opportunistic,
    ),
    Patch(
        key="ddos",
        label="DDoS Storm",
        description="+4 enemies/sector and +60% score, +25 starting RAM.",
        apply=_ddos,
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
