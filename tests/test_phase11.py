"""Phase 11 — Distros, structured runs, skip tags, vendor, i18n."""

from __future__ import annotations

import pytest

from kernelquest.core import run_progress as rp
from kernelquest.core.run_progress import (
    MILESTONES_PER_RELEASE,
    TOTAL_RELEASES,
    MilestoneKind,
    RunProgress,
    target_score_for,
)
from kernelquest.core.settings import Settings
from kernelquest.data.database import Database
from kernelquest.data.distros_catalog import (
    DISTROS,
    first_distro_key,
    next_in_chain,
)
from kernelquest.data.repositories import (
    DistroRepository,
    MilestoneRepository,
    RunRepository,
    SkipTagRepository,
)
from kernelquest.entities.skip_tag import CATALOG as SKIP_TAGS
from kernelquest.entities.skip_tag import get_tag, maybe_get
from kernelquest.ui import i18n

# ---------------------------------------------------------------------------
# Run progression / target curve
# ---------------------------------------------------------------------------


def test_target_score_curve_release_zero() -> None:
    assert target_score_for(0, 0) == rp.BASE_TARGET_SCORE
    assert target_score_for(0, 2) > target_score_for(0, 0)


def test_target_score_curve_grows_per_release() -> None:
    earlier = target_score_for(0, 2)
    later = target_score_for(7, 2)
    assert later > earlier * 5  # 1.45**7 ≈ 13.5


def test_run_progress_advance_wraps_release() -> None:
    p = RunProgress(distro_key="vanilla")
    for _ in range(MILESTONES_PER_RELEASE):
        p.advance()
    assert p.release_index == 1
    assert p.milestone_index == 0


def test_run_progress_completes_after_all_releases() -> None:
    p = RunProgress(distro_key="vanilla")
    for _ in range(TOTAL_RELEASES * MILESTONES_PER_RELEASE):
        p.advance()
    assert p.is_run_complete


def test_run_progress_skip_tag_grant_and_consume() -> None:
    p = RunProgress(distro_key="vanilla")
    p.grant_skip_tag("free_vendor")
    assert p.consume_skip_tag("free_vendor") is True
    assert p.consume_skip_tag("free_vendor") is False


def test_milestone_score_window_baseline() -> None:
    p = RunProgress(distro_key="vanilla")
    p.begin_milestone(50)
    assert p.milestone_score(120) == 70
    assert p.milestone_score(40) == 0  # never negative


def test_current_kind_and_target_match_index() -> None:
    p = RunProgress(distro_key="vanilla")
    assert p.current_kind is MilestoneKind.SECTOR_A
    p.advance()
    assert p.current_kind is MilestoneKind.SECTOR_B
    p.advance()
    assert p.current_kind is MilestoneKind.BOSS


# ---------------------------------------------------------------------------
# Distros catalog
# ---------------------------------------------------------------------------


def test_distros_catalog_has_six_in_unlock_order() -> None:
    keys = [d.key for d in DISTROS]
    assert keys == [
        "vanilla",
        "minimal",
        "hardened",
        "realtime",
        "bleeding_edge",
        "recovery",
    ]
    assert first_distro_key() == "vanilla"
    assert next_in_chain("vanilla").key == "minimal"
    assert next_in_chain("recovery") is None


# ---------------------------------------------------------------------------
# Distro repository
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Database:
    return Database.in_memory()


def test_distros_repo_seeds_only_first_distro_unlocked(db: Database) -> None:
    repo = DistroRepository(db)
    keys = [d.key for d in DISTROS]
    repo.ensure_seeded(keys, first_unlocked="vanilla")
    assert repo.is_unlocked("vanilla")
    assert not repo.is_unlocked("minimal")
    assert repo.unlocked_keys() == {"vanilla"}


def test_distros_repo_unlock_idempotent(db: Database) -> None:
    repo = DistroRepository(db)
    repo.ensure_seeded(["vanilla", "minimal"], first_unlocked="vanilla")
    assert repo.unlock("minimal") is True
    assert repo.unlock("minimal") is False


# ---------------------------------------------------------------------------
# Run / Milestone / SkipTag persistence
# ---------------------------------------------------------------------------


def test_run_repository_insert_with_distro_and_success_columns(db: Database) -> None:
    runs = RunRepository(db)
    run_id = runs.insert(
        player_name="alpha",
        seed=42,
        depth_reached=3,
        total_score=200,
        crash_cause="run_complete",
        duration_ms=1234,
        distro_key="vanilla",
        is_successful=True,
    )
    row = db.connection.execute(
        "SELECT distro_key, is_successful FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
    assert row["distro_key"] == "vanilla"
    assert int(row["is_successful"]) == 1


def test_milestone_repository_round_trip(db: Database) -> None:
    runs = RunRepository(db)
    rid = runs.insert(
        player_name="beta",
        seed=1,
        depth_reached=1,
        total_score=10,
        crash_cause="x",
        duration_ms=0,
        distro_key="vanilla",
        is_successful=False,
    )
    repo = MilestoneRepository(db)
    repo.insert_many(
        rid,
        [
            (0, 0, "sector_a", 100, 120, False, True),
            (0, 1, "sector_b", 125, 50, True, False),
        ],
    )
    rows = repo.for_run(rid)
    assert len(rows) == 2
    assert rows[0]["was_cleared"] == 1
    assert rows[1]["was_skipped"] == 1


def test_skip_tag_repository_round_trip(db: Database) -> None:
    runs = RunRepository(db)
    rid = runs.insert(
        player_name="gamma",
        seed=2,
        depth_reached=1,
        total_score=10,
        crash_cause="x",
        duration_ms=0,
        distro_key="vanilla",
        is_successful=False,
    )
    repo = SkipTagRepository(db)
    repo.insert(rid, "free_vendor", used=False)
    repo.insert(rid, "double_bits", used=True)
    rows = repo.for_run(rid)
    assert sorted(rows) == sorted([("free_vendor", False), ("double_bits", True)])


# ---------------------------------------------------------------------------
# Skip tag catalog
# ---------------------------------------------------------------------------


def test_skip_tag_catalog_has_four_known_keys() -> None:
    keys = {t.key for t in SKIP_TAGS}
    assert {"free_vendor", "double_bits", "extra_daemon", "bonus_score"} <= keys
    assert get_tag("free_vendor").effect_type == "free_vendor"
    assert maybe_get("nope") is None


# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------


def test_i18n_translates_known_keys_and_falls_back() -> None:
    i18n.set_language("tr")
    assert i18n.t("menu.new_run") == "Yeni Çalıştırma"
    # Unknown key returns key.
    assert i18n.t("does.not.exist") == "does.not.exist"
    i18n.set_language("en")
    assert i18n.t("menu.new_run") == "New Run"


def test_i18n_format_kwargs() -> None:
    i18n.set_language("en")
    assert "5" in i18n.t("vendor.bits", bits=5)


def test_settings_cycle_language_persists_and_changes_active_locale(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "settings.json"
    monkeypatch.setattr("kernelquest.core.settings._SETTINGS_PATH", cfg, raising=False)
    s = Settings()
    s.language = "en"
    s.cycle_language(1)
    assert s.language == "tr"
    assert i18n.get_language() == "tr"
    s.cycle_language(1)
    assert s.language == "en"
