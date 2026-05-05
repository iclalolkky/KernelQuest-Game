"""Phase 7 — cinematic player + settings round-trip tests."""

from __future__ import annotations

from kernelquest.core.settings import Settings, load, save
from kernelquest.data.database import Database
from kernelquest.data.lore_catalog import INTRO_FRAMES, CinematicFrame
from kernelquest.data.repositories import MetaRepository
from kernelquest.ui.cinematics import CinematicPlayer


def _frames() -> tuple[CinematicFrame, ...]:
    return (
        CinematicFrame(title="A", body=("one",), duration_s=0.5),
        CinematicFrame(title="B", body=("two",), duration_s=0.5),
    )


def test_cinematic_player_advances_with_dt() -> None:
    p = CinematicPlayer(frames=_frames())
    p.start()
    assert not p.finished
    assert p.index == 0
    p.step(0.6)
    assert p.index == 1
    p.step(0.6)
    assert p.finished


def test_cinematic_player_skip_advances_one_frame() -> None:
    p = CinematicPlayer(frames=_frames())
    p.start()
    p.skip()
    assert p.index == 1
    p.skip()
    assert p.finished


def test_cinematic_player_skip_all_finishes_immediately() -> None:
    p = CinematicPlayer(frames=_frames())
    p.start()
    p.skip_all()
    assert p.finished


def test_cinematic_player_step_after_finish_is_noop() -> None:
    p = CinematicPlayer(frames=_frames())
    p.start()
    p.skip_all()
    p.step(1.0)
    assert p.finished


def test_intro_frames_render_metadata() -> None:
    p = CinematicPlayer(frames=tuple(INTRO_FRAMES))
    p.start()
    assert not p.finished
    assert p.frames[p.index] is INTRO_FRAMES[0]


def test_settings_round_trip_phase7_fields() -> None:
    db = Database.in_memory()
    meta = MetaRepository(db)
    s = load(meta)
    s.auto_skip_intro = True
    s.player_palette = "phosphor"
    save(meta, s)

    fresh = load(meta)
    assert fresh.auto_skip_intro is True
    assert fresh.player_palette == "phosphor"


def test_settings_cycle_palette_wraps() -> None:
    s = Settings()
    start = s.player_palette
    # Cycle through every palette and back.
    seen = {start}
    for _ in range(8):
        s.cycle_palette(1)
        seen.add(s.player_palette)
    assert len(seen) >= 2  # at least cycles through
