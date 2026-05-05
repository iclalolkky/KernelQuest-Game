"""Phase 11 — skip-tag catalog.

Skip Tags are one-shot bonuses awarded for skipping a non-boss Milestone.  The
catalog stays small and focused: each tag has a key, a localized label, a
short description, and a single ``effect_type`` understood by the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class SkipTag:
    key: str
    label: str
    description: str
    effect_type: str  # "free_vendor" | "double_bits" | "extra_daemon_slot" | "bonus_score"
    magnitude: int = 0


CATALOG: Final[tuple[SkipTag, ...]] = (
    SkipTag(
        key="free_vendor",
        label="Free Vendor",
        description="Next vendor: every item costs 0 bits.",
        effect_type="free_vendor",
    ),
    SkipTag(
        key="double_bits",
        label="Double Bits",
        description="Double bits earned on the next milestone.",
        effect_type="double_bits",
        magnitude=2,
    ),
    SkipTag(
        key="extra_daemon",
        label="+1 Daemon Slot",
        description="+1 daemon slot for the next sector.",
        effect_type="extra_daemon_slot",
        magnitude=1,
    ),
    SkipTag(
        key="bonus_score",
        label="Score Boost",
        description="+50 starting score on the next milestone.",
        effect_type="bonus_score",
        magnitude=50,
    ),
)


_BY_KEY: Final[dict[str, SkipTag]] = {t.key: t for t in CATALOG}


def all_tags() -> tuple[SkipTag, ...]:
    return CATALOG


def get_tag(key: str) -> SkipTag:
    return _BY_KEY[key]


def maybe_get(key: str) -> SkipTag | None:
    return _BY_KEY.get(key)
