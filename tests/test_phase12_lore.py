"""Phase 12.2 — Boot Briefing onboarding lore is wired."""

from __future__ import annotations

from kernelquest.data.lore_catalog import CATALOG, for_condition

ONBOARDING_CONDITIONS = (
    "onboarding_combat",
    "onboarding_cycles",
    "onboarding_ram",
    "onboarding_cache",
    "onboarding_programs",
    "onboarding_daemons",
)


def test_onboarding_entries_are_in_catalog() -> None:
    keys = {entry.key for entry in CATALOG}
    for cond in ONBOARDING_CONDITIONS:
        entry = for_condition(cond)
        assert entry is not None, f"missing lore for condition {cond!r}"
        assert entry.key in keys


def test_onboarding_voices_are_kernel_or_init() -> None:
    for cond in ONBOARDING_CONDITIONS:
        entry = for_condition(cond)
        assert entry is not None
        body = entry.body
        assert (
            "[KERNEL]" in body or "[init(0)]" in body
        ), f"{entry.key} is missing the in-universe voice tags"


def test_onboarding_titles_use_man_pattern() -> None:
    for cond in ONBOARDING_CONDITIONS:
        entry = for_condition(cond)
        assert entry is not None
        assert entry.title.startswith("man "), entry.title
