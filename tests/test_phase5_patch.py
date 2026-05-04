"""Phase 5 — Patch Notes effects + state."""

from __future__ import annotations

from kernelquest.entities.patch import CATALOG, PatchEffects, PatchState, get_patch


def test_each_patch_in_catalog_has_unique_key() -> None:
    keys = [p.key for p in CATALOG]
    assert len(keys) == len(set(keys))
    assert len(CATALOG) >= 6


def test_glass_cannon_doubles_player_and_enemy_damage_mults() -> None:
    effects = PatchEffects()
    get_patch("glass-cannon").apply(effects)
    assert effects.player_damage_mult == 1.4
    assert effects.enemy_damage_mult == 1.4


def test_patch_state_stacks() -> None:
    state = PatchState()
    state.selected.append(get_patch("glass-cannon"))
    state.selected.append(get_patch("berserker"))
    eff = state.effects()
    # 1.4 * 1.6 = 2.24
    assert round(eff.player_damage_mult, 4) == round(1.4 * 1.6, 4)
    # berserker also halves regen.
    assert eff.ram_regen_mult == 0.5


def test_speed_demon_adds_enemy_speed() -> None:
    state = PatchState()
    state.selected.append(get_patch("speed-demon"))
    eff = state.effects()
    assert eff.enemy_speed_bonus == 1
    assert round(eff.enemy_hp_mult, 4) == 0.85


def test_overclock_grants_starting_cycles() -> None:
    state = PatchState()
    state.selected.append(get_patch("overclock"))
    eff = state.effects()
    assert eff.starting_cycles_bonus == 1
    assert round(eff.score_mult, 4) == 1.15


def test_unknown_patch_raises() -> None:
    try:
        get_patch("does-not-exist")
    except KeyError:
        return
    raise AssertionError("expected KeyError")
