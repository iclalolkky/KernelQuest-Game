"""Combat resolution: bump-attack, damage application, loot drops."""

from __future__ import annotations

import random
from dataclasses import dataclass

from kernelquest.core.config import (
    LOOT_DROP_CHANCE,
    PLAYER_BASE_DAMAGE,
)
from kernelquest.entities.items import ALL_ITEM_IDS
from kernelquest.entities.malware import Malware
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


def player_attack(
    world: World,
    target: Malware,
    rng: random.Random,
    damage: int = PLAYER_BASE_DAMAGE,
) -> AttackResult:
    """Resolve a player bump-attack against `target`.

    The cycle cost is the engine's responsibility - call ``player.spend_cycle()``
    before invoking this function.

    Oyuncunun düşmana saldırı hareketini çözümler ve sonucu döner.
    """
    target.take_damage(damage)
    killed = not target.is_alive
    score = target.score_value if killed else 0
    if killed:
        world.player.score += score

    loot: str | None = None
    if killed and rng.random() < LOOT_DROP_CHANCE:
        loot = rng.choice(ALL_ITEM_IDS)
        world.items[target.position] = loot

    if killed:
        msg = f"{target.name} yenildi (+{score} skor)"
        if loot is not None:
            msg += f"; {loot} düştü"
    else:
        msg = f"{target.name}'e {damage} hasar ({target.hp}/{target.max_hp})"

    return AttackResult(
        target=target,
        damage_dealt=damage,
        killed=killed,
        score_gained=score,
        loot_dropped=loot,
        log_message=msg,
    )


def enemy_attack(player: Player, attacker: Malware, damage: int | None = None) -> int:
    """Oyuncuya 'attacker'ın hasarını uygula ve crash nedenini kaydet."""
    dmg = attacker.damage if damage is None else damage
    player.take_damage(dmg, source=attacker.crash_label)
    return dmg
