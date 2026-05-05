"""Phase 8 — damage types & resistance profile.

Combat resolves damage by multiplying by a per-species ``resistance_for(kind)``
factor (0.5×–2.0×). Programs declare their `DamageType`; melee bumps default
to ``KINETIC``.
"""

from __future__ import annotations

from enum import StrEnum


class DamageType(StrEnum):
    """The three damage families. Stored as strings for trivial serialization."""

    KINETIC = "kinetic"
    """Melee bumps and physical impacts. Default for un-typed attacks."""

    SIGNAL = "signal"
    """Most programs and signal-based daemons (e.g. ``kill -9``)."""

    LOGIC = "logic"
    """Special items, debuggers, exploits."""


# Effectiveness factor → human label for floating-damage HUD coloring.
EFFECTIVENESS_LABELS: dict[float, str] = {
    0.5: "RESIST",
    1.0: "",
    1.5: "WEAK",
    2.0: "VULN",
}


def label_for_factor(factor: float) -> str:
    """Return a short label for the floating-damage popup."""
    if factor <= 0.6:
        return "RESIST"
    if factor >= 1.9:
        return "VULN"
    if factor >= 1.4:
        return "WEAK"
    return ""
