"""Phase 9 — boss spectacle, phase scripts, audio, safe-zone music."""

from __future__ import annotations

import random

import pytest

from kernelquest.entities.boss_phases import (
    BUFFER_PHASES,
    HYDRA_PHASES,
    KERNEL_PANIC_PHASES,
    THE_LEAK_PHASES,
    BossPhase,
    phase_for_hp,
    phases_for,
)
from kernelquest.entities.damage import DamageType
from kernelquest.entities.malware import (
    BufferOverflowBoss,
    DeadlockTwin,
    KernelPanic,
    RootkitHydra,
    TheLeak,
    ZeroDayBoss,
)
from kernelquest.entities.malware_registry import maybe_get
from kernelquest.entities.player import Player
from kernelquest.systems.ai import run_enemy_turn
from kernelquest.systems.combat import player_attack
from kernelquest.ui.music import StemMixer
from kernelquest.world.boss_arenas import load_arena
from kernelquest.world.generator import _which_boss, generate_world
from kernelquest.world.tile import TileType

# ---------------------------------------------------------------------------
# 9.1 / 9.3 phase scripting
# ---------------------------------------------------------------------------


def test_phase_for_hp_advances_through_thresholds() -> None:
    phs = KERNEL_PANIC_PHASES
    assert phase_for_hp(phs, 100, 100) == 0
    assert phase_for_hp(phs, 65, 100) == 1
    assert phase_for_hp(phs, 30, 100) == 2
    assert phase_for_hp(phs, 0, 100) == 2


def test_phase_for_hp_handles_empty_max() -> None:
    assert phase_for_hp(KERNEL_PANIC_PHASES, 0, 0) == 0
    assert phase_for_hp((), 5, 10) == 0


def test_phases_for_known_species() -> None:
    assert phases_for("kernel_panic") == KERNEL_PANIC_PHASES
    assert phases_for("the_leak") == THE_LEAK_PHASES
    assert phases_for("rootkit_hydra") == HYDRA_PHASES
    assert phases_for("buffer_overflow") == BUFFER_PHASES
    assert phases_for("unknown_species") == ()


def test_phase_advance_emits_in_attack_result() -> None:
    rng = random.Random(0)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    boss = KernelPanic(position=(2, 2))
    world.enemies.append(boss)

    # First small hit — still phase 0.
    boss.hp = boss.max_hp
    r1 = player_attack(world, boss, rng, damage=1)
    assert r1.phase_advanced is None

    # Drop HP just above the phase-1 threshold (0.66) then deliver a real swing.
    boss.hp = int(boss.max_hp * 0.67)
    boss.phase_index = 0
    # Damage scaled with effectiveness, so use a larger swing to guarantee advance.
    r2 = player_attack(world, boss, rng, damage=10)
    assert r2.phase_advanced is not None
    assert r2.phase_advanced.name == "oops"


# ---------------------------------------------------------------------------
# 9.1 boss arenas
# ---------------------------------------------------------------------------


def test_arena_loader_returns_grid_for_the_leak() -> None:
    arena = load_arena("the_leak")
    assert arena is not None
    assert arena.grid.width > 0
    assert arena.grid.height > 0
    # Spawn must lie on a walkable tile.
    sx, sy = arena.player_spawn
    assert arena.grid.get(sx, sy) is TileType.EMPTY


def test_arena_loader_missing_returns_none(tmp_path) -> None:
    assert load_arena("definitely_not_a_boss") is None


def test_boss_wheel_assigns_one_boss_per_floor() -> None:
    seen = []
    for d in range(5, 35, 5):
        seen.append(_which_boss(d))
    assert seen == [
        "kernel_panic",
        "segfault",
        "buffer_overflow",
        "rootkit_hydra",
        "deadlock_twin",
        "the_leak",
    ]


def test_arena_world_replaces_grid_at_boss_depth() -> None:
    rng = random.Random(7)
    player = Player(position=(0, 0), max_ram=10, ram=10)
    world = generate_world(player=player, depth=5, rng=rng)
    bosses = [e for e in world.enemies if e.is_boss]
    assert len(bosses) == 1
    assert isinstance(bosses[0], KernelPanic)
    # Arena grid is smaller than the procedural default.
    assert world.grid.width < 20


# ---------------------------------------------------------------------------
# 9.2 boss-specific mechanics
# ---------------------------------------------------------------------------


def test_deadlock_twins_heal_each_other_when_solo_hit() -> None:
    rng = random.Random(0)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    twin_a = DeadlockTwin(position=(5, 5), twin_id=0)
    twin_b = DeadlockTwin(position=(5, 7), twin_id=1)
    twin_b.hp = 5  # below max
    world.enemies.extend([twin_a, twin_b])
    player_attack(world, twin_a, rng, damage=3)
    # twin_b healed by 3 (capped at max_hp) because twin_a was hit alone.
    assert twin_b.hp == 8


def test_deadlock_twins_no_heal_when_both_attacked_same_turn() -> None:
    rng = random.Random(0)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    twin_a = DeadlockTwin(position=(5, 5), twin_id=0)
    twin_b = DeadlockTwin(position=(5, 7), twin_id=1)
    twin_b.hp = 5
    world.enemies.extend([twin_a, twin_b])
    # Hit B first then A: when A is hit, B was already attacked → no heal.
    player_attack(world, twin_b, rng, damage=2)
    assert twin_b.hp == 3
    player_attack(world, twin_a, rng, damage=2)
    assert twin_b.hp == 3  # not healed by A's hit


def test_rootkit_hydra_grows_a_head_on_non_signal_kill() -> None:
    rng = random.Random(0)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    hydra = RootkitHydra(position=(4, 4))
    world.enemies.append(hydra)
    starting_heads = hydra.heads_remaining
    # Lethal kinetic hit — should NOT actually kill, heads grow.
    player_attack(world, hydra, rng, damage=hydra.max_hp + 99)
    assert hydra.is_alive
    assert hydra.heads_remaining == starting_heads + 1


def test_rootkit_hydra_loses_head_on_signal_kill() -> None:
    rng = random.Random(0)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    hydra = RootkitHydra(position=(4, 4))
    hydra.heads_remaining = 1  # last head
    world.enemies.append(hydra)
    player_attack(world, hydra, rng, damage=hydra.max_hp + 99, damage_type=DamageType.SIGNAL)
    assert not hydra.is_alive
    assert hydra.heads_remaining == 0


def test_the_leak_corrupts_tiles_when_not_damaged() -> None:
    rng = random.Random(123)
    player = Player(position=(1, 1), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    leak = TheLeak(position=(4, 4))
    leak.last_damaged_turn = -100
    world.enemies = [leak]
    bad_before = sum(
        1
        for x in range(world.grid.width)
        for y in range(world.grid.height)
        if world.grid.get(x, y) is TileType.BAD_SECTOR
    )
    run_enemy_turn(world, rng)
    bad_after = sum(
        1
        for x in range(world.grid.width)
        for y in range(world.grid.height)
        if world.grid.get(x, y) is TileType.BAD_SECTOR
    )
    assert bad_after >= bad_before + 1


def test_buffer_overflow_writes_blocks_every_three_turns() -> None:
    rng = random.Random(7)
    player = Player(position=(5, 5), max_ram=10, ram=10)
    world = generate_world(player=player, depth=1, rng=rng)
    px, py = world.player.position
    # Place boss far enough to not reach player; only the projectile pattern triggers.
    far_x = px + 8 if px + 8 < world.grid.width else px - 5
    far_y = py + 8 if py + 8 < world.grid.height else py - 5
    buf = BufferOverflowBoss(position=(far_x, far_y))
    world.enemies = [buf]
    # Make sure the four diagonals around the player are EMPTY first.
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        if 0 <= px + dx < world.grid.width and 0 <= py + dy < world.grid.height:
            world.grid.set(px + dx, py + dy, TileType.EMPTY)
    # Run two turns — counter goes to 1, 2: no projectiles yet.
    for _ in range(2):
        run_enemy_turn(world, rng)
    # Third turn — counter hits 3, projectiles drop.
    run_enemy_turn(world, rng)
    bad_diag = 0
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        if (
            0 <= px + dx < world.grid.width
            and 0 <= py + dy < world.grid.height
            and world.grid.get(px + dx, py + dy) is TileType.BAD_SECTOR
        ):
            bad_diag += 1
    assert bad_diag >= 1


def test_zero_day_boss_lives_in_registry() -> None:
    sp = maybe_get("zero_day")
    assert sp is not None
    assert sp.is_boss


def test_zero_day_boss_can_attack(monkeypatch) -> None:
    rng = random.Random(0)
    player = Player(position=(5, 5), max_ram=20, ram=20)
    world = generate_world(player=player, depth=1, rng=rng)
    px, py = world.player.position
    boss = ZeroDayBoss(position=(px + 1, py))
    # Make sure the tile is walkable.
    world.grid.set(px + 1, py, TileType.EMPTY)
    world.enemies = [boss]
    log = run_enemy_turn(world, rng)
    assert any("0-day" in line.lower() or "zeroday" in line.lower() for line in log)


# ---------------------------------------------------------------------------
# 9.4 Audio + safe-zone music
# ---------------------------------------------------------------------------


def test_stem_mixer_safe_zone_swaps_to_safe_stem() -> None:
    mx = StemMixer()
    mx.update_targets(set(), boss_active=False, safe_zone=True)
    assert mx.targets["safe"] == 1.0
    assert mx.targets["boss"] == 0.0
    # Bed dimmed but still audible so transition isn't jarring.
    assert 0.0 < mx.targets["bed"] < 1.0


def test_stem_mixer_safe_zone_yields_to_boss() -> None:
    mx = StemMixer()
    mx.update_targets(set(), boss_active=True, safe_zone=True)
    assert mx.targets["boss"] == 1.0
    assert mx.targets["safe"] == 0.0


def test_stem_mixer_normal_targets_unchanged() -> None:
    from kernelquest.entities.malware_registry import Archetype

    mx = StemMixer()
    mx.update_targets({Archetype.SKIRMISHER}, boss_active=False, safe_zone=False)
    assert mx.targets["safe"] == 0.0
    assert mx.targets["bed"] == 1.0


# ---------------------------------------------------------------------------
# 9.6 Phase script snapshot
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "species,expected_phases",
    [
        ("kernel_panic", 3),
        ("segfault", 2),
        ("the_leak", 3),
        ("deadlock_twin", 2),
        ("rootkit_hydra", 3),
        ("buffer_overflow", 2),
        ("zero_day", 3),
    ],
)
def test_phase_count_per_species(species: str, expected_phases: int) -> None:
    assert len(phases_for(species)) == expected_phases


def test_phase_telegraphs_are_unique() -> None:
    seen: set[str] = set()
    for phs in (
        KERNEL_PANIC_PHASES,
        THE_LEAK_PHASES,
        HYDRA_PHASES,
        BUFFER_PHASES,
    ):
        for ph in phs:
            assert ph.telegraph not in seen
            seen.add(ph.telegraph)


def test_boss_phase_dataclass_fields_default() -> None:
    bp = BossPhase(name="x", hp_ratio=0.5)
    assert bp.telegraph == ""
    assert bp.music_overlay == ""
    assert bp.damage_scale == 1.0
