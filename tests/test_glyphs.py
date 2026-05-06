"""Phase 12.12 — arrow-glyph rendering safety net.

Verifies that :mod:`kernelquest.ui.glyphs` falls back to ASCII when the active
font does not support unicode arrows, and that :func:`sanitize` leaves the
text untouched when the font does support them.
"""

from __future__ import annotations

import os

import pygame
import pytest

from kernelquest.ui import glyphs

# Run pygame headlessly so this works in CI / sandboxes.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.font.init()


@pytest.fixture
def mono_font() -> pygame.font.Font:
    return pygame.font.SysFont("monospace", 14)


def test_key_glyph_returns_unicode_when_supported(mono_font: pygame.font.Font) -> None:
    glyphs.clear_cache()
    out = glyphs.key_glyph("up", mono_font)
    # Either form is acceptable; assert it's a single visible label.
    assert out in {"↑", "[Up]"}


def test_key_glyph_without_font_returns_unicode() -> None:
    assert glyphs.key_glyph("up") == "↑"
    assert glyphs.key_glyph("right") == "→"


def test_sanitize_replaces_unsupported_glyphs() -> None:
    """Use a fake font that reports no support for the arrow codepoints."""

    class _StubFont:
        def metrics(self, ch: str) -> list[None]:
            return [None]

    stub = _StubFont()
    glyphs.clear_cache()
    out = glyphs.sanitize(stub, "[↑/↓] move")  # type: ignore[arg-type]
    assert "↑" not in out
    assert "↓" not in out
    assert "[Up]" in out and "[Dn]" in out


def test_sanitize_leaves_supported_glyphs(mono_font: pygame.font.Font) -> None:
    """If the font supports arrows, sanitize is a no-op for them."""
    glyphs.clear_cache()
    text = "[↑/↓] move"
    out = glyphs.sanitize(mono_font, text)
    # If unsupported, fallback applies; if supported, untouched. Either way
    # there must be no tofu glyph (we replaced unsupported codepoints).
    if "[Up]" in out:
        # Fallback path.
        assert "↑" not in out
    else:
        assert out == text


def test_sanitize_handles_empty_string(mono_font: pygame.font.Font) -> None:
    assert glyphs.sanitize(mono_font, "") == ""


def test_arrow_strings_in_i18n_render_safely(mono_font: pygame.font.Font) -> None:
    """Round-trip the arrow-bearing menu hint through sanitize+render."""
    from kernelquest.ui import i18n

    i18n.set_language("en")
    text = i18n.t("menu.hint")
    safe = glyphs.sanitize(mono_font, text)
    surface = mono_font.render(safe, True, (255, 255, 255))
    assert surface.get_width() > 0
