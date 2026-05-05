"""Combat resolution: bump-attack, damage application, loot drops."""

from __future__ import annotations

import random
from dataclasses import dataclass

from kernelquest.core.config import (
    LOOT_DROP_CHANCE,
    PLAYER_BASE_DAMAGE,
)
from kernelquest.entities.affix import on_death as _affix_on_death
from kernelquest.entities.boss_phases import BossPhase, phase_for_hp, phases_for
from kernelquest.entities.damage import DamageType, label_for_factor
from kernelquest.entities.items import ALL_ITEM_IDS
from kernelquest.entities.malware import DeadlockTwin, Malware, RootkitHydra, TheLeak
from kernelquest.entities.malware_registry import maybe_get as get_species
from kernelquest.entities.player import Player
from kernelquest.world.world import World


@dataclass
class AttackResult:
    """Outcome of a single bump-attack."""

    target: Malware
    damage_dealt: int
    killed: bool
    score_gained: int = 0
    loot_dropped: str | None = None
    log_message: str = ""
    damage_type: DamageType = DamageType.KINETIC
    effectiveness: float = 1.0
    program_key: str = "bump"
    phase_advanced: BossPhase | None = None
    """Phase 9 — set when this hit pushed the boss into a new phase."""


def resolve_damage(target: Malware, raw_damage: int, kind: DamageType) -> tuple[int, float]:
    """Compute final damage after species resistance + affix immunity.

    Returns ``(final_damage, effectiveness_multiplier)``. Effectiveness is the
    multiplier we used (post-immunity), so ``0.0`` means fully immune.
    """
    # Encrypted affix → fully immune to one type until decrypted by `grep`.
    if target.affixes.encrypted_against == kind:
        return 0, 0.0
    species = get_species(target.species_key)
    factor = species.resistance_for(kind) if species is not None else 1.0
    final = max(1 if factor > 0 else 0, int(round(raw_damage * factor)))
    if factor == 0:
        return 0, 0.0
    return final, factor


def player_attack(
    world: World,
    target: Malware,
    rng: random.Random,
    damage: int = PLAYER_BASE_DAMAGE,
    *,
    damage_type: DamageType = DamageType.KINETIC,
    program_key: str = "bump",
) -> AttackResult:
    """Resolve a player bump-attack against `target`.

    The cycle cost is the engine's responsibility — call ``player.spend_cycle()``
    before invoking this function.
    """
    final, factor = resolve_damage(target, damage, damage_type)
    target.take_damage(final)
    if isinstance(target, TheLeak) and final > 0:
        target.last_damaged_turn = world.turn_counter
    # Phase 9 — DeadlockTwin healing: damaging one twin heals its partner
    # unless the partner was also hit this same turn.
    if isinstance(target, DeadlockTwin) and final > 0:
        target.attacked_this_turn = True
        for other in world.enemies:
            if (
                isinstance(other, DeadlockTwin)
                and other is not target
                and other.is_alive
                and not other.attacked_this_turn
            ):
                other.hp = min(other.max_hp, other.hp + final)
    # Phase 9 — RootkitHydra split: non-signal kill grows another head.
    if isinstance(target, RootkitHydra) and not target.is_alive:
        if damage_type is DamageType.SIGNAL:
            target.heads_remaining = max(0, target.heads_remaining - 1)
        else:
            target.heads_remaining += 1
        if target.heads_remaining > 0:
            target.hp = max(1, target.max_hp // 2)
    killed = not target.is_alive
    # Phase 9 — boss-phase advancement.
    phase_advanced: BossPhase | None = None
    phases = phases_for(target.species_key)
    if phases:
        new_idx = phase_for_hp(phases, target.hp, target.max_hp)
        if new_idx > target.phase_index:
            target.phase_index = new_idx
            phase_advanced = phases[new_idx]
    score = target.score_value if killed else 0
    if killed:
        # Apply affix score multiplier so tougher mobs award more.
        score = max(1, int(round(score * target.affixes.score_multiplier())))
        world.player.score += score

    loot: str | None = None
    if killed and rng.random() < LOOT_DROP_CHANCE:
        loot = rng.choice(ALL_ITEM_IDS)
        world.items[target.position] = loot
    # IndexError variant always drops loot (one extra roll).
    if killed and target.species_key == "index_error" and loot is None:
        loot = rng.choice(ALL_ITEM_IDS)
        world.items[target.position] = loot

    if killed:
        msg = f"Defeated {target.name} (+{score} score)"
        if loot is not None:
            msg += f"; dropped {loot}"
    else:
        eff = label_for_factor(factor)
        suffix = f" [{eff}]" if eff else ""
        if final == 0:
            msg = f"{target.name} is encrypted — {damage_type.value} blocked"
        else:
            msg = f"Hit {target.name} for {final}{suffix} ({target.hp}/{target.max_hp})"

    return AttackResult(
        target=target,
        damage_dealt=final,
        killed=killed,
        score_gained=score,
        loot_dropped=loot,
        log_message=msg,
        damage_type=damage_type,
        effectiveness=factor,
        program_key=program_key,
        phase_advanced=phase_advanced,
    )


def enemy_attack(player: Player, attacker: Malware, damage: int | None = None) -> int:
    """Apply `attacker`'s damage to the player, recording the crash cause."""
    dmg = attacker.damage if damage is None else damage
    player.take_damage(dmg, source=attacker.crash_label)
    return dmg


def fire_death_effects(world: World, target: Malware) -> list[str]:
    """Trigger affix/species-specific on-death side-effects.

    Called by the engine *after* the renderer has marked the kill.
    """
    return _affix_on_death(target, world)
