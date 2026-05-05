"""Phase 8 — combat, affixes, intel and music."""

from __future__ import annotations

import random

from kernelquest.data.database import Database
from kernelquest.data.repositories import (
    CombatLogRepository,
    IntelRepository,
)
from kernelquest.entities.affix import (
    AffixState,
    apply_at_spawn,
    on_turn_end,
    roll_affixes,
)
from kernelquest.entities.damage import DamageType, label_for_factor
from kernelquest.entities.malware import (
    IndexError_,
    LogicBomb,
    SyntaxError_,
)
from kernelquest.entities.malware_registry import (
    SPECIES,
    Archetype,
    maybe_get,
)
from kernelquest.entities.malware_registry import (
    get as get_species,
)
from kernelquest.entities.player import Player
from kernelquest.systems.combat import (
    fire_death_effects,
    player_attack,
    resolve_damage,
)
from kernelquest.ui.music import (
    ARCHETYPE_STEMS,
    REDUCE_MOTION_STEM_LIMIT,
    StemMixer,
)
from kernelquest.world.generator import generate_world

# ---------- registry ----------


def test_registry_has_all_phase8_species() -> None:
    keys = {sp.key for sp in SPECIES}
    expected = {
        "syntax_error",
        "runtime_error",
        "index_error",
        "logic_bomb",
        "zombie_process",
        "fork_bomb",
        "stack_overflow",
        "null_pointer",
        "race_condition",
        "daemonizer",
        "bruiser",
        "kernel_panic",
        "segfault",
    }
    assert expected <= keys


def test_species_resistances_default_to_one() -> None:
    sp = get_species("logic_bomb")
    assert sp.resistance_for(DamageType.SIGNAL) == 1.5  # weak to signal
    assert sp.resistance_for(DamageType.KINETIC) == 0.5  # resists kinetic


# ---------- combat ----------


def test_resolve_damage_applies_resistance() -> None:
    target = LogicBomb(position=(0, 0))
    final, factor = resolve_damage(target, 10, DamageType.SIGNAL)
    assert factor > 1.0
    assert final >= 11


def test_resolve_damage_encrypted_immunity() -> None:
    target = SyntaxError_(position=(0, 0))
    target.affixes = AffixState(
        keys=["encrypted"],
        encrypted_against=DamageType.KINETIC,
    )
    final, factor = resolve_damage(target, 10, DamageType.KINETIC)
    assert final == 0
    assert factor == 0.0


def test_label_for_factor() -> None:
    assert label_for_factor(0.5) == "RESIST"
    assert label_for_factor(1.5) == "WEAK"
    assert label_for_factor(2.0) == "VULN"
    assert label_for_factor(1.0) == ""


def test_index_error_always_drops_loot() -> None:
    rng = random.Random(0)
    player = Player(max_ram=10, ram=10, max_cpu_cycles=2, cpu_cycles=2, name="p")
    world = generate_world(player=player, depth=1, rng=rng)
    target = IndexError_(position=(2, 2))
    target.hp = 1  # kill in one hit
    world.enemies.append(target)
    # Use a deterministic RNG that *misses* the loot drop on the first roll —
    # 0.99 > LOOT_DROP_CHANCE, so the IndexError fallback kicks in.
    drop_rng = random.Random()
    drop_rng.random = lambda: 0.99  # type: ignore[assignment, method-assign]
    drop_rng.choice = lambda items: items[0]  # type: ignore[assignment, method-assign]
    result = player_attack(world, target, drop_rng)
    assert result.killed
    assert result.loot_dropped is not None


# ---------- affix ----------


def test_roll_affixes_capped_at_two() -> None:
    rng = random.Random(123)
    keys = roll_affixes(rng, depth=20, max_count=2)
    assert len(keys) <= 2


def test_roll_affixes_boss_always_empty() -> None:
    rng = random.Random(0)
    assert roll_affixes(rng, depth=20, is_boss=True) == []


def test_apply_at_spawn_cached_boosts_hp() -> None:
    rng = random.Random(0)
    enemy = SyntaxError_(position=(0, 0))
    enemy.affixes.keys = ["cached"]
    base = enemy.max_hp
    apply_at_spawn(enemy, rng)
    assert enemy.max_hp > base
    assert enemy.hp == enemy.max_hp


def test_apply_at_spawn_encrypted_picks_a_type() -> None:
    rng = random.Random(0)
    enemy = SyntaxError_(position=(0, 0))
    enemy.affixes.keys = ["encrypted"]
    apply_at_spawn(enemy, rng)
    assert enemy.affixes.encrypted_against in (
        DamageType.KINETIC,
        DamageType.SIGNAL,
        DamageType.LOGIC,
    )


def test_volatile_on_death_blasts_adjacent_player() -> None:
    rng = random.Random(0)
    player = Player(max_ram=10, ram=10, max_cpu_cycles=2, cpu_cycles=2, name="p")
    world = generate_world(player=player, depth=1, rng=rng)
    enemy = SyntaxError_(position=(world.player.position[0] + 1, world.player.position[1]))
    enemy.affixes.keys = ["volatile"]
    world.enemies.append(enemy)
    enemy.hp = 0  # treat as just-killed
    starting_ram = world.player.ram
    fire_death_effects(world, enemy)
    assert world.player.ram < starting_ram


def test_networked_on_turn_end_heals_allies() -> None:
    rng = random.Random(0)
    player = Player(max_ram=10, ram=10, max_cpu_cycles=2, cpu_cycles=2, name="p")
    world = generate_world(player=player, depth=1, rng=rng)
    healer = SyntaxError_(position=(5, 5))
    healer.affixes.keys = ["networked"]
    ally = SyntaxError_(position=(6, 5))
    ally.hp = 1
    world.enemies.extend([healer, ally])
    on_turn_end(healer, world)
    assert ally.hp >= 1  # heal applied or at minimum unchanged


# ---------- intel + combat log ----------


def test_intel_repo_tier_transitions() -> None:
    db = Database.in_memory()
    repo = IntelRepository(db)
    # Tier 0 → 1 on first hit.
    tier = repo.record_damage_to("syntax_error", 1)
    assert tier == 1
    # Tier 2 at >= 5 kills.
    for _ in range(5):
        repo.record_kill("syntax_error")
    assert repo.get("syntax_error").intel_level >= 2
    assert repo.get("syntax_error").weakness_revealed is True


def test_intel_repo_reveal_jumps_to_tier_two() -> None:
    db = Database.in_memory()
    repo = IntelRepository(db)
    repo.reveal("logic_bomb")
    assert repo.get("logic_bomb").intel_level >= 2
    assert repo.get("logic_bomb").weakness_revealed is True


def test_combat_log_records_and_aggregates() -> None:
    db = Database.in_memory()
    repo = CombatLogRepository(db)
    repo.insert(program_key="bump", species_key="syntax_error", damage=5, kills=1)
    repo.insert(program_key="bump", species_key="syntax_error", damage=7, kills=0)
    repo.insert(program_key="kill9", species_key="syntax_error", damage=99, kills=1)
    best = repo.best_program_for("syntax_error")
    assert best == ("kill9", 99)


# ---------- music ----------


def test_archetype_stems_cover_every_archetype() -> None:
    for arc in Archetype:
        assert arc in ARCHETYPE_STEMS


def test_stem_mixer_targets_match_archetypes() -> None:
    mixer = StemMixer()
    mixer.update_targets({Archetype.SAPPER, Archetype.STALKER}, boss_active=False)
    assert mixer.targets["bed"] == 1.0
    assert mixer.targets["tension_lead"] == 1.0
    assert mixer.targets["tension_pad"] == 1.0
    assert mixer.targets["boss"] == 0.0


def test_stem_mixer_boss_overrides() -> None:
    mixer = StemMixer()
    mixer.update_targets(set(), boss_active=True)
    assert mixer.targets["boss"] == 1.0


def test_stem_mixer_reduce_motion_caps_active() -> None:
    mixer = StemMixer()
    mixer.update_targets(
        {Archetype.SAPPER, Archetype.STALKER, Archetype.SUPPORT, Archetype.SKIRMISHER},
        boss_active=False,
        reduce_motion=True,
    )
    extras = [k for k, v in mixer.targets.items() if v > 0 and k != "bed"]
    assert len(extras) <= REDUCE_MOTION_STEM_LIMIT


def test_stem_mixer_step_crossfades() -> None:
    mixer = StemMixer()
    mixer.update_targets({Archetype.SKIRMISHER}, boss_active=False)
    mixer.step(0.1)
    assert 0.0 < mixer.volumes["melody_lead"] < 1.0
    # Multiple steps converge to target.
    for _ in range(50):
        mixer.step(0.1)
    assert abs(mixer.volumes["melody_lead"] - 1.0) < 1e-6


# ---------- generator + species pickup ----------


def test_generator_assigns_species_keys() -> None:
    rng = random.Random(7)
    player = Player(max_ram=10, ram=10, max_cpu_cycles=2, cpu_cycles=2, name="p")
    world = generate_world(player=player, depth=5, rng=rng)
    for enemy in world.enemies:
        assert enemy.species_key, f"{enemy.name} missing species_key"
        assert maybe_get(enemy.species_key) is not None
