"""Phase 10 — single source of truth for explain() strings.

Every Program / Daemon / Item / Patch already has a ``description`` field on
its dataclass (or, for items, an ``apply()`` returning a verb-oriented
sentence). This module wraps them in a uniform ``explain(kind, key)``
function so the Tutorial Range, tooltips, and Codex never drift from the
runtime behaviour.
"""

from __future__ import annotations

from typing import Final

from kernelquest.entities.daemon import CATALOG as DAEMON_CATALOG
from kernelquest.entities.items import (
    GARBAGE_COLLECTOR,
    OPTIMIZATION,
    SCAN_BOOST,
    Item,
)
from kernelquest.entities.patch import CATALOG as PATCH_CATALOG
from kernelquest.entities.program import CATALOG as PROGRAM_CATALOG

_ITEM_DESCRIPTIONS: Final[dict[str, str]] = {
    GARBAGE_COLLECTOR.id: "Restore RAM. Eats one cache slot. Use it before you faint.",
    OPTIMIZATION.id: "Grant +cycles. The map is patient; you don't have to be.",
    SCAN_BOOST.id: "Extends your line-of-sight for several turns.",
}


def explain(kind: str, key: str) -> str:
    """Return the canonical, single-line explanation for a runtime entity.

    ``kind`` is one of ``program``, ``daemon``, ``item``, ``patch``.
    Raises :class:`KeyError` if the key is unknown.
    """
    kind = kind.lower()
    if kind == "program":
        for prog in PROGRAM_CATALOG:
            if prog.key == key:
                return prog.description
        raise KeyError(f"unknown program: {key!r}")
    if kind == "daemon":
        for daemon in DAEMON_CATALOG:
            if daemon.key == key:
                return daemon.description
        raise KeyError(f"unknown daemon: {key!r}")
    if kind == "item":
        if key in _ITEM_DESCRIPTIONS:
            return _ITEM_DESCRIPTIONS[key]
        raise KeyError(f"unknown item: {key!r}")
    if kind == "patch":
        for patch in PATCH_CATALOG:
            if patch.key == key:
                return patch.description
        raise KeyError(f"unknown patch: {key!r}")
    raise KeyError(f"unknown kind: {kind!r}")


def list_keys(kind: str) -> tuple[str, ...]:
    """Return all valid keys for a given entity ``kind``."""
    kind = kind.lower()
    if kind == "program":
        return tuple(p.key for p in PROGRAM_CATALOG)
    if kind == "daemon":
        return tuple(d.key for d in DAEMON_CATALOG)
    if kind == "item":
        return tuple(_ITEM_DESCRIPTIONS.keys())
    if kind == "patch":
        return tuple(p.key for p in PATCH_CATALOG)
    raise KeyError(f"unknown kind: {kind!r}")


def label(kind: str, key: str) -> str:
    """Return the user-facing label for a runtime entity."""
    kind = kind.lower()
    if kind == "program":
        for prog in PROGRAM_CATALOG:
            if prog.key == key:
                return prog.label
    elif kind == "daemon":
        for daemon in DAEMON_CATALOG:
            if daemon.key == key:
                return daemon.label
    elif kind == "item":
        item: Item | None = {
            GARBAGE_COLLECTOR.id: GARBAGE_COLLECTOR,
            OPTIMIZATION.id: OPTIMIZATION,
            SCAN_BOOST.id: SCAN_BOOST,
        }.get(key)
        if item is not None:
            return item.label
    elif kind == "patch":
        for patch in PATCH_CATALOG:
            if patch.key == key:
                return patch.label
    raise KeyError(f"unknown {kind}: {key!r}")


__all__ = ["explain", "label", "list_keys"]
