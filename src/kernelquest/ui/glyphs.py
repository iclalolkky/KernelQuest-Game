"""Phase 12.12 — key-glyph rendering helper.

The bundled monospace fonts on some macOS / Linux setups don't ship the unicode
arrow glyphs (``↑↓←→``), which renders as 'tofu' rectangles in the HUD.  This
module centralises the rendering decision: ask :func:`key_glyph` for the
canonical key label and it returns the fancy unicode form when the active font
supports it, falling back to a readable ASCII form otherwise.

Two public APIs:

* :func:`key_glyph` — return a single key label (``"↑"`` or ``"[Up]"``).
* :func:`sanitize` — scrub a free-form string, replacing every unicode key
  glyph the font can't render with its ASCII counterpart.  Cheap to call per
  frame; results are cached per ``(font_id, codepoint)``.
"""

from __future__ import annotations

from typing import Final

import pygame

# Canonical mapping. Keep keys in lowercase + ``up/down/left/right`` shorthand.
_UNICODE_FORMS: Final[dict[str, str]] = {
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→",
}

_ASCII_FORMS: Final[dict[str, str]] = {
    "up": "[Up]",
    "down": "[Dn]",
    "left": "[Lf]",
    "right": "[Rt]",
}

# Reverse map for sanitize(): unicode codepoint → ASCII fallback.
_FALLBACKS: Final[dict[str, str]] = {
    "↑": "[Up]",
    "↓": "[Dn]",
    "←": "[Lf]",
    "→": "[Rt]",
}

# Cached per-font glyph-support results: ``id(font) → {codepoint → bool}``.
_SUPPORT_CACHE: dict[int, dict[str, bool]] = {}


def _supports(font: pygame.font.Font, codepoint: str) -> bool:
    """Return True iff *font* can render *codepoint*.

    pygame's ``font.metrics()`` returns ``[None]`` for unsupported glyphs.
    We cache by ``id(font)`` because :class:`pygame.font.Font` is not hashable
    and font identity is stable for the lifetime of a renderer.
    """
    cache = _SUPPORT_CACHE.setdefault(id(font), {})
    cached = cache.get(codepoint)
    if cached is not None:
        return cached
    try:
        metrics = font.metrics(codepoint)
    except Exception:  # pragma: no cover — defensive
        metrics = []
    ok = bool(metrics) and metrics[0] is not None
    cache[codepoint] = ok
    return ok


def key_glyph(direction: str, font: pygame.font.Font | None = None) -> str:
    """Return the best label for an arrow key.

    When *font* is given and lacks the unicode arrow glyph, an ASCII fallback
    such as ``"[Up]"`` is returned instead.
    """
    direction = direction.lower()
    unicode_form = _UNICODE_FORMS.get(direction)
    if unicode_form is None:
        return direction
    if font is None or _supports(font, unicode_form):
        return unicode_form
    return _ASCII_FORMS[direction]


def sanitize(font: pygame.font.Font, text: str) -> str:
    """Replace any unsupported unicode key-glyph in *text* with an ASCII form."""
    if not text:
        return text
    out_chars: list[str] = []
    for ch in text:
        fallback = _FALLBACKS.get(ch)
        if fallback is not None and not _supports(font, ch):
            out_chars.append(fallback)
        else:
            out_chars.append(ch)
    return "".join(out_chars)


def clear_cache() -> None:
    """Drop the per-font support cache (useful in tests)."""
    _SUPPORT_CACHE.clear()
