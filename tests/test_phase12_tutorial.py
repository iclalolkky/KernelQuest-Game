"""Phase 12.1 — Tutorial Range parity with shipped systems."""

from __future__ import annotations

from kernelquest.entities.daemon import CATALOG as DAEMON_CATALOG
from kernelquest.entities.items import ALL_ITEM_IDS
from kernelquest.entities.malware_registry import SPECIES
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.program import CATALOG as PROGRAM_CATALOG
from kernelquest.ui.explain import explain
from kernelquest.world.tutorial_range import (
    CURRICULUM,
    lesson_examples,
    load_range_arena,
)


def test_curriculum_rooms_exist_in_arena_json() -> None:
    arena = load_range_arena()
    room_keys = {r.key for r in arena.rooms}
    for lesson in CURRICULUM:
        assert (
            lesson.room in room_keys
        ), f"Lesson {lesson.key!r} references missing room {lesson.room!r}"


def test_lesson_examples_resolve_against_catalogs() -> None:
    catalog_keys = {
        "program": {p.key for p in PROGRAM_CATALOG},
        "daemon": {d.key for d in DAEMON_CATALOG},
        "patch": {p.key for p in PATCH_CATALOG},
        "item": set(ALL_ITEM_IDS),
    }
    seen_any = False
    for lesson in CURRICULUM:
        rows = lesson_examples(lesson.key)
        if not rows:
            continue
        seen_any = True
        for kind, _label, blurb in rows:
            # Every row must round-trip through explain() to ensure the
            # catalog still exposes that key.
            assert kind in catalog_keys, kind
            assert blurb, f"{lesson.key} produced empty blurb"
    assert seen_any, "lesson_examples should yield at least one row across L3-L6"


def test_tutorial_range_only_references_shipped_species() -> None:
    species_keys = {s.key for s in SPECIES}
    # The arena spawns SyntaxError + KernelPanic — both must be in the registry.
    for required in ("syntax_error", "kernel_panic"):
        assert required in species_keys, f"tutorial range requires species {required!r}"


def test_explain_resolves_all_program_and_daemon_keys() -> None:
    for prog in PROGRAM_CATALOG:
        assert explain("program", prog.key)
    for daemon in DAEMON_CATALOG:
        assert explain("daemon", daemon.key)
