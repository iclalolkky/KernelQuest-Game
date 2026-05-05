"""Phase 11 — run structure: 8 Releases × 3 Milestones with target scores.

The structure is purely advisory bookkeeping; the underlying world generation
still happens per-sector.  ``RunProgress`` lives on :class:`GameEngine` and is
queried by HUD / vendor / milestone screens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

# Tunables — kept here so test_phase11 can import without circular deps.
TOTAL_RELEASES: Final[int] = 8
MILESTONES_PER_RELEASE: Final[int] = 3
BASE_TARGET_SCORE: Final[int] = 100
TARGET_GROWTH: Final[float] = 1.45  # release-over-release scaling


class MilestoneKind(Enum):
    """A Release's three milestones: two "regular" sectors then a Boss."""

    SECTOR_A = "sector_a"
    SECTOR_B = "sector_b"
    BOSS = "boss"


_KIND_BY_INDEX: Final[tuple[MilestoneKind, ...]] = (
    MilestoneKind.SECTOR_A,
    MilestoneKind.SECTOR_B,
    MilestoneKind.BOSS,
)


def kind_for_milestone(milestone_index: int) -> MilestoneKind:
    """Return the milestone kind for a 0-indexed slot inside a release."""
    if not 0 <= milestone_index < MILESTONES_PER_RELEASE:
        raise ValueError(milestone_index)
    return _KIND_BY_INDEX[milestone_index]


def target_score_for(release_index: int, milestone_index: int) -> int:
    """Score the player must reach in this milestone to clear it.

    Formula: ``BASE * GROWTH ** release_index * (1.0 + 0.25 * milestone_index)``.
    Boss milestones (index 2) demand the most, sector A the least.
    """
    if not 0 <= release_index < TOTAL_RELEASES:
        raise ValueError(release_index)
    base = BASE_TARGET_SCORE * (TARGET_GROWTH**release_index)
    bump = 1.0 + 0.25 * milestone_index
    return int(round(base * bump))


@dataclass
class MilestoneRecord:
    """Result of a single milestone — populated as the run progresses."""

    release_index: int
    milestone_index: int
    target_score: int
    kind: MilestoneKind
    reached_score: int = 0
    was_skipped: bool = False
    was_cleared: bool = False


@dataclass
class SkipTagInstance:
    """A one-shot bonus the player won by skipping a milestone."""

    key: str
    used: bool = False


@dataclass
class RunProgress:
    """Live, in-memory bookkeeping for the active run."""

    distro_key: str = ""
    release_index: int = 0  # 0..TOTAL_RELEASES-1
    milestone_index: int = 0  # 0..MILESTONES_PER_RELEASE-1
    score_at_milestone_start: int = 0
    records: list[MilestoneRecord] = field(default_factory=list)
    skip_tags: list[SkipTagInstance] = field(default_factory=list)
    consumed_skip_tags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    @property
    def current_kind(self) -> MilestoneKind:
        return kind_for_milestone(self.milestone_index)

    @property
    def current_target(self) -> int:
        return target_score_for(self.release_index, self.milestone_index)

    @property
    def is_run_complete(self) -> bool:
        """True iff every release has been cleared (8 × 3 milestones done)."""
        return self.release_index >= TOTAL_RELEASES

    @property
    def releases_cleared(self) -> int:
        """Number of fully completed Releases (all 3 milestones each)."""
        return sum(
            1
            for i in range(TOTAL_RELEASES)
            if all(
                any(
                    r.release_index == i
                    and r.milestone_index == m
                    and (r.was_cleared or r.was_skipped)
                    for r in self.records
                )
                for m in range(MILESTONES_PER_RELEASE)
            )
        )

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def begin_milestone(self, current_total_score: int) -> None:
        """Record the score baseline so we can measure milestone-only score."""
        self.score_at_milestone_start = current_total_score

    def milestone_score(self, current_total_score: int) -> int:
        return max(0, current_total_score - self.score_at_milestone_start)

    def finish_current(
        self, *, reached_score: int, was_skipped: bool, was_cleared: bool
    ) -> MilestoneRecord:
        rec = MilestoneRecord(
            release_index=self.release_index,
            milestone_index=self.milestone_index,
            target_score=self.current_target,
            kind=self.current_kind,
            reached_score=reached_score,
            was_skipped=was_skipped,
            was_cleared=was_cleared,
        )
        self.records.append(rec)
        return rec

    def advance(self) -> None:
        """Move the cursor to the next milestone (and next release if needed)."""
        self.milestone_index += 1
        if self.milestone_index >= MILESTONES_PER_RELEASE:
            self.milestone_index = 0
            self.release_index += 1

    def grant_skip_tag(self, key: str) -> SkipTagInstance:
        tag = SkipTagInstance(key=key)
        self.skip_tags.append(tag)
        return tag

    def consume_skip_tag(self, key: str) -> bool:
        for tag in self.skip_tags:
            if tag.key == key and not tag.used:
                tag.used = True
                self.consumed_skip_tags.append(key)
                return True
        return False
