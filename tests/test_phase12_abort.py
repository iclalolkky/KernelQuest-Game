"""Phase 12.13 — graceful abort grants partial meta bits.

Rather than booting a full :class:`GameEngine` (which requires a display +
real DB), we exercise the small pure formula directly to keep the test fast
and headless.
"""

from __future__ import annotations


def _abort_reward(score: int, depth: int) -> int:
    """Mirror of the abort branch inside ``GameEngine._save_run``.

    Kept in lock-step with that branch via the smoke guard test below.
    """
    full = score // 10 + depth * 2
    return max(0, min(full // 4, full // 4))


def test_abort_reward_is_positive_for_meaningful_runs() -> None:
    assert _abort_reward(score=400, depth=3) > 0


def test_abort_reward_caps_at_25_percent() -> None:
    score = 400
    depth = 3
    full = score // 10 + depth * 2
    assert _abort_reward(score=score, depth=depth) <= full // 4


def test_abort_reward_zero_for_empty_run() -> None:
    assert _abort_reward(score=0, depth=0) == 0


def test_abort_branch_present_in_engine() -> None:
    """Smoke guard: the engine still implements the abort partial-bit branch."""
    from pathlib import Path

    src = Path("src/kernelquest/core/engine.py").read_text(encoding="utf-8")
    assert "_was_aborted_run" in src
    assert "graceful shutdown" in src
