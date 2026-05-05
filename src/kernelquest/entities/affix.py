"""Phase 8 — power affixes ("modifier" layer).

Every spawned `Malware` may carry up to two affixes. Affixes are applied at
spawn time (`apply_at_spawn`), can hook into per-turn updates, and may fire
death effects. They are also responsible for the score multiplier and visual
badge displayed by the renderer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from kernelquest.entities.damage import DamageType

if TYPE_CHECKING:  # pragma: no cover
    from kernelquest.entities.malware import Malware
    from kernelquest.world.world import World


@dataclass(frozen=True)
class Affix:
    """A single affix definition.

    ``score_mult`` stacks multiplicatively across affixes when computing the
    bits / score reward for killing the enemy.
    """

    key: str
    label: str
    badge: str  # 1–2 char glyph rendered next to the sprite
    description: str
    score_mult: float = 1.0


CACHED: Final[Affix] = Affix(
    key="cached",
    label="Cached",
    badge="C",
    description="+25% HP — pages stayed warm.",
    score_mult=1.25,
)
OVERCLOCKED: Final[Affix] = Affix(
    key="overclocked",
    label="Overclocked",
    badge="O",
    description="+1 speed — acts twice every other turn.",
    score_mult=1.35,
)
ENCRYPTED: Final[Affix] = Affix(
    key="encrypted",
    label="Encrypted",
    badge="E",
    description="Immune to one damage type until decrypted by `grep`.",
    score_mult=1.4,
)
NETWORKED: Final[Affix] = Affix(
    key="networked",
    label="Networked",
    badge="N",
    description="Heals nearby allies for 1 HP / turn.",
    score_mult=1.3,
)
VOLATILE: Final[Affix] = Affix(
    key="volatile",
    label="Volatile",
    badge="V",
    description="Explodes for half-damage on death.",
    score_mult=1.2,
)


AFFIX_POOL: Final[tuple[Affix, ...]] = (
    CACHED,
    OVERCLOCKED,
    ENCRYPTED,
    NETWORKED,
    VOLATILE,
)

_BY_KEY: Final[dict[str, Affix]] = {a.key: a for a in AFFIX_POOL}


def get(key: str) -> Affix:
    """Return the affix with that key, or raise `KeyError`."""
    return _BY_KEY[key]


@dataclass
class AffixState:
    """Runtime state attached to a malware instance for its rolled affixes."""

    keys: list[str] = field(default_factory=list)
    encrypted_against: DamageType | None = None
    overclock_extra_turn: bool = False

    def has(self, key: str) -> bool:
        return key in self.keys

    def score_multiplier(self) -> float:
        mult = 1.0
        for key in self.keys:
            try:
                mult *= _BY_KEY[key].score_mult
            except KeyError:  # pragma: no cover - defensive
                continue
        return mult

    def badges(self) -> list[str]:
        return [_BY_KEY[k].badge for k in self.keys if k in _BY_KEY]


def roll_affixes(
    rng: random.Random,
    *,
    depth: int,
    max_count: int = 2,
    is_boss: bool = False,
) -> list[str]:
    """Return 0–``max_count`` affix keys.

    Bosses never carry affixes (they have boss-script abilities instead).
    Probability ramps with sector depth: 5%/affix at depth 1, +5% per depth,
    capped at 60%.
    """
    if is_boss:
        return []
    chance = min(0.6, 0.05 + 0.05 * max(0, depth - 1))
    chosen: list[str] = []
    pool = list(AFFIX_POOL)
    rng.shuffle(pool)
    for affix in pool:
        if len(chosen) >= max_count:
            break
        if rng.random() < chance:
            chosen.append(affix.key)
    return chosen


def apply_at_spawn(enemy: Malware, rng: random.Random) -> None:
    """Apply spawn-time stat changes for ``enemy.affixes``.

    - ``Cached`` → +25% HP / max_hp
    - ``Encrypted`` → pick a random damage type to be immune to
    """
    if not enemy.affixes.keys:
        return
    if enemy.affixes.has("cached"):
        bonus = max(1, enemy.max_hp // 4)
        enemy.max_hp += bonus
        enemy.hp += bonus
    if enemy.affixes.has("encrypted") and enemy.affixes.encrypted_against is None:
        enemy.affixes.encrypted_against = rng.choice(list(DamageType))


def on_turn_end(enemy: Malware, world: World) -> list[str]:
    """Per-turn passive effects for affixed enemies."""
    log: list[str] = []
    if enemy.affixes.has("networked"):
        from kernelquest.systems.pathfinding import chebyshev_distance

        for ally in world.enemies:
            if ally is enemy or not ally.is_alive:
                continue
            if chebyshev_distance(enemy.position, ally.position) <= 2 and ally.hp < ally.max_hp:
                ally.hp = min(ally.max_hp, ally.hp + 1)
    return log


def on_death(enemy: Malware, world: World) -> list[str]:
    """Death-time effects (called *after* ``hp`` reaches 0)."""
    log: list[str] = []
    if enemy.affixes.has("volatile"):
        from kernelquest.systems.pathfinding import chebyshev_distance

        blast = max(1, enemy.damage // 2)
        if chebyshev_distance(enemy.position, world.player.position) <= 1:
            world.player.take_damage(blast, source=f"{enemy.name} (volatile)")
            log.append(f"{enemy.name} bursts on death (-{blast} RAM)")
    return log
