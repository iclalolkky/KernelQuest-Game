"""Phase 10 — Interactive Tutorial Range tests.

Covers the curriculum predicates, range arena loader, lesson auto-completion,
the Polygon spawn helpers, and the ``explain()`` single-source-of-truth.
"""

from __future__ import annotations

from kernelquest.entities.daemon import CATALOG as DAEMON_CATALOG
from kernelquest.entities.items import ALL_ITEM_IDS
from kernelquest.entities.malware_registry import SPECIES, factory_for
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.player import Player
from kernelquest.entities.program import CATALOG as PROGRAM_CATALOG
from kernelquest.ui.explain import explain, label, list_keys
from kernelquest.world.tile import TileType
from kernelquest.world.tutorial_range import (
    CURRICULUM,
    Lesson,
    LessonProgress,
    build_range_world,
    lesson_by_key,
    load_range_arena,
)

# ---------------------------------------------------------------------------
# 10.1 Range arena
# ---------------------------------------------------------------------------


def test_range_arena_has_six_rooms() -> None:
    arena = load_range_arena()
    keys = {r.key for r in arena.rooms}
    assert keys == {"movement", "combat", "items", "programs", "daemons", "boss"}


def test_range_arena_spawn_and_exit_are_walkable() -> None:
    arena = load_range_arena()
    sx, sy = arena.spawn
    assert arena.grid.get(sx, sy) is TileType.EMPTY
    ex, ey = arena.exit_pos
    assert arena.grid.get(ex, ey) is TileType.EXIT


def test_range_world_places_player_at_spawn() -> None:
    arena = load_range_arena()
    player = Player(position=(0, 0), max_ram=10, ram=10)
    world = build_range_world(player, arena)
    assert world.player.position == arena.spawn
    assert world.depth == 0


def test_range_rooms_contain_member_positions() -> None:
    arena = load_range_arena()
    movement = next(r for r in arena.rooms if r.key == "movement")
    assert movement.contains((movement.x, movement.y))
    assert not movement.contains((movement.x + movement.w + 5, movement.y))


# ---------------------------------------------------------------------------
# 10.2 Curriculum predicates
# ---------------------------------------------------------------------------


def test_curriculum_has_eight_lessons_in_order() -> None:
    keys = [lesson.key for lesson in CURRICULUM]
    assert keys == [
        "L1_boot",
        "L2_combat",
        "L3_items",
        "L4_programs",
        "L5_daemons",
        "L6_patches",
        "L7_recognition",
        "L8_boss_drill",
    ]


def test_lesson_completion_via_progress_field() -> None:
    progress = LessonProgress()
    l1 = lesson_by_key("L1_boot")
    assert not l1.is_complete(progress)
    progress.moved_steps = l1.goal_target
    assert l1.is_complete(progress)


def test_lesson_programs_fired_aggregates_across_keys() -> None:
    progress = LessonProgress()
    l4 = lesson_by_key("L4_programs")
    progress.programs_fired["sudo"] = 1
    assert l4.is_complete(progress)


def test_lesson_progress_reset_clears_all_counters() -> None:
    progress = LessonProgress(
        moved_steps=5,
        enemies_killed=2,
        items_collected=3,
        daemons_swapped=1,
        patches_picked=1,
        inspect_opened=1,
        boss_phases_seen=2,
    )
    progress.programs_fired["fork"] = 4
    progress.reset()
    assert progress.moved_steps == 0
    assert progress.programs_fired == {}
    assert progress.boss_phases_seen == 0


def test_lesson_dataclass_immutable() -> None:
    l1 = CURRICULUM[0]
    assert isinstance(l1, Lesson)
    try:
        l1.goal_target = 999  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Lesson should be frozen")


# ---------------------------------------------------------------------------
# 10.4 explain() single source of truth
# ---------------------------------------------------------------------------


def test_explain_program_matches_catalog_description() -> None:
    for prog in PROGRAM_CATALOG:
        assert explain("program", prog.key) == prog.description


def test_explain_daemon_matches_catalog_description() -> None:
    for daemon in DAEMON_CATALOG:
        assert explain("daemon", daemon.key) == daemon.description


def test_explain_patch_matches_catalog_description() -> None:
    for patch in PATCH_CATALOG:
        assert explain("patch", patch.key) == patch.description


def test_explain_item_returns_non_empty_string() -> None:
    for item_id in ALL_ITEM_IDS:
        text = explain("item", item_id)
        assert isinstance(text, str) and text


def test_explain_unknown_kind_raises() -> None:
    try:
        explain("vegetable", "carrot")
    except KeyError:
        return
    raise AssertionError("unknown kind should raise KeyError")


def test_label_round_trips_for_every_kind() -> None:
    for kind in ("program", "daemon", "item", "patch"):
        for key in list_keys(kind):
            assert label(kind, key)


# ---------------------------------------------------------------------------
# 10.3 Polygon helpers
# ---------------------------------------------------------------------------


def test_factory_for_known_species_returns_class() -> None:
    cls = factory_for("syntax_error")
    assert cls is not None
    instance = cls(position=(1, 1))
    assert instance.species_key == "syntax_error"


def test_factory_for_unknown_species_returns_none() -> None:
    assert factory_for("not_a_real_species") is None


def test_every_polygon_kind_has_at_least_one_entry() -> None:
    assert len(SPECIES) > 0
    assert len(ALL_ITEM_IDS) > 0
    assert len(PROGRAM_CATALOG) > 0
    assert len(DAEMON_CATALOG) > 0
    assert len(PATCH_CATALOG) > 0


# ---------------------------------------------------------------------------
# 10.5 Range smoke — never persists, all entities spawnable
# ---------------------------------------------------------------------------


def test_range_smoke_spawns_one_of_every_factory_class() -> None:
    arena = load_range_arena()
    player = Player(position=arena.spawn, max_ram=80, ram=80)
    world = build_range_world(player, arena)
    spawned = 0
    for sp in SPECIES:
        cls = factory_for(sp.key)
        if cls is None:
            continue
        # Find any walkable empty tile for the spawn.
        placed = False
        for x in range(world.grid.width):
            if placed:
                break
            for y in range(world.grid.height):
                pos = (x, y)
                if pos == player.position:
                    continue
                if world.grid.is_walkable(x, y) and world.enemy_at(pos) is None:
                    world.enemies.append(cls(position=pos))
                    spawned += 1
                    placed = True
                    break
    assert spawned == len([sp for sp in SPECIES if factory_for(sp.key) is not None])
    # Sanity: no exception when computing FoV with all the spawns.
    world.recompute_fov()


def test_range_arena_loader_is_idempotent() -> None:
    a1 = load_range_arena()
    a2 = load_range_arena()
    assert a1.rooms == a2.rooms
    assert a1.spawn == a2.spawn
    assert a1.exit_pos == a2.exit_pos
