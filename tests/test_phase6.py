"""Phase 6 — themes, settings, tutorial, boss flow."""

from __future__ import annotations

import random

import pytest

from kernelquest.core.settings import (
    Difficulty,
    Settings,
    is_tutorial_done,
    load,
    mark_tutorial_done,
    save,
)
from kernelquest.data.database import Database
from kernelquest.data.repositories import MetaRepository
from kernelquest.entities.malware import KernelPanic, SegFault
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.patch import PatchEffects, PatchState, get_patch
from kernelquest.entities.player import Player
from kernelquest.ui import theme as theme_mod
from kernelquest.ui import themes
from kernelquest.world.generator import generate_world


@pytest.fixture()
def meta() -> MetaRepository:
    db = Database.in_memory()
    db.run_migrations()
    return MetaRepository(db)


# ----- Themes -----


def test_apply_theme_mutates_palette() -> None:
    themes.apply_theme("kernel")
    kernel_bg = theme_mod.BACKGROUND
    themes.apply_theme("phosphor")
    assert kernel_bg != theme_mod.BACKGROUND
    themes.apply_theme("kernel")  # restore


def test_get_theme_unknown_falls_back() -> None:
    assert themes.get_theme("does-not-exist") is themes.THEME_KERNEL


def test_catalog_size() -> None:
    assert len(themes.CATALOG) >= 4


# ----- Settings round-trip -----


def test_extended_settings_round_trip(meta: MetaRepository) -> None:
    s = Settings(
        volume=0.4,
        music_volume=0.3,
        sfx_volume=0.7,
        muted=True,
        difficulty=Difficulty.HARD,
        theme="phosphor",
        fullscreen=True,
        ui_scale=1.25,
        reduce_motion=True,
        crt_effect=False,
        large_text=True,
    )
    save(meta, s)
    loaded = load(meta)
    assert loaded.muted is True
    assert loaded.theme == "phosphor"
    assert loaded.fullscreen is True
    assert loaded.ui_scale == pytest.approx(1.25)
    assert loaded.reduce_motion is True
    assert loaded.crt_effect is False
    assert loaded.large_text is True
    assert loaded.music_volume == pytest.approx(0.3)
    assert loaded.sfx_volume == pytest.approx(0.7)


def test_tutorial_marker(meta: MetaRepository) -> None:
    assert not is_tutorial_done(meta)
    mark_tutorial_done(meta)
    assert is_tutorial_done(meta)


# ----- Patch catalog growth -----


def test_patch_catalog_has_at_least_15_entries() -> None:
    assert len(PATCH_CATALOG) >= 15


def test_each_patch_has_unique_key() -> None:
    keys = [p.key for p in PATCH_CATALOG]
    assert len(set(keys)) == len(keys)


def test_boss_damage_mult_only_applies_when_present() -> None:
    state = PatchState()
    base = state.effects()
    assert base.boss_damage_mult == 1.0


def test_kernel_bypass_buffs_boss_damage() -> None:
    p = get_patch("kernel-bypass")
    eff = PatchEffects()
    p.apply(eff)
    assert eff.boss_damage_mult > 1.0


def test_starting_ram_bonus_field_default() -> None:
    assert PatchEffects().starting_ram_bonus == 0


# ----- Boss flow -----


def test_boss_flag_on_kernel_panic() -> None:
    boss = KernelPanic(position=(0, 0))
    assert boss.is_boss is True


def test_boss_flag_on_segfault() -> None:
    boss = SegFault(position=(0, 0))
    assert boss.is_boss is True


def test_world_living_boss_helper() -> None:
    rng = random.Random(7)
    player = Player()
    # KERNEL_PANIC_DEPTH is 5, SEGFAULT_DEPTH is 10 — depth 5 spawns KernelPanic.
    world = generate_world(player=player, depth=5, rng=rng)
    assert world.has_living_boss
    boss = world.living_boss()
    assert boss is not None and boss.is_boss


def test_no_boss_at_depth_one() -> None:
    rng = random.Random(7)
    player = Player()
    world = generate_world(player=player, depth=1, rng=rng)
    assert not world.has_living_boss


def test_extra_enemies_per_sector_increases_count() -> None:
    rng_a = random.Random(123)
    rng_b = random.Random(123)
    a = generate_world(player=Player(), depth=2, rng=rng_a, extra_enemies=0)
    b = generate_world(player=Player(), depth=2, rng=rng_b, extra_enemies=3)
    assert len(b.enemies) >= len(a.enemies) + 1
