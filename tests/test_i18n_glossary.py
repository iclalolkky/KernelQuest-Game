"""Phase 12.3 — i18n glossary guard.

Make sure non-English locales never translate OS / kernel terminology.
The terms in :data:`kernelquest.ui.i18n.GLOSSARY` are part of the player's
mental model and must round-trip verbatim through every locale.
"""

from __future__ import annotations

import re

import pytest

from kernelquest.ui import i18n


def _strings_for(locale: str) -> dict[str, str]:
    table = i18n._TABLES[locale]  # type: ignore[attr-defined]
    return dict(table)


def test_glossary_terms_are_non_empty() -> None:
    """Sanity: glossary is not accidentally cleared."""
    assert i18n.GLOSSARY, "GLOSSARY must not be empty"
    assert "RAM" in i18n.GLOSSARY
    assert "run" in i18n.GLOSSARY


@pytest.mark.parametrize("locale", ["tr"])
def test_no_forbidden_translation_appears_in_locale(locale: str) -> None:
    """No translated form of a glossary term may appear in non-English copy."""
    table = _strings_for(locale)
    offenders: list[tuple[str, str, str]] = []
    for key, value in table.items():
        lower = value.lower()
        for bad, canonical in i18n.FORBIDDEN_TRANSLATIONS.items():
            # Word-ish boundary: avoid false positives inside larger Turkish
            # words that happen to share a substring.
            if re.search(rf"(?<![\w]){re.escape(bad)}(?![\w])", lower):
                offenders.append((key, value, f"{bad!r} → use {canonical!r}"))
    assert not offenders, (
        "Locale '"
        + locale
        + "' contains forbidden translations of glossary terms:\n"
        + "\n".join(f"  - [{k}] {v!r}  ({hint})" for k, v, hint in offenders)
    )


def test_supported_languages_have_tables() -> None:
    for code in i18n.SUPPORTED_LANGUAGES:
        assert code in i18n._TABLES  # type: ignore[attr-defined]


def test_set_language_round_trip() -> None:
    original = i18n.get_language()
    try:
        i18n.set_language("tr")
        assert i18n.t("menu.new_run") == "Yeni Run"
        i18n.set_language("en")
        assert i18n.t("menu.new_run") == "New Run"
    finally:
        i18n.set_language(original)
