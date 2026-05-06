"""Phase 12.11 — dialogue scenes for narrative LORE moments.

This module owns:

* Pure-data :class:`DialogueLine` and :class:`DialogueScene` records.
* The five canonical scenes (``intro``, ``first_kill``, ``first_boss``,
  ``first_distro_success``, ``ending``).
* A small renderer entry point (``render_dialogue``) on :class:`UIManager` that
  draws a portrait, nameplate, and typewritten dialogue body.

Portraits are programmatically drawn 48×48 sprites — keyed by ``portrait``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class DialogueLine:
    """A single spoken line inside a :class:`DialogueScene`."""

    speaker: str
    portrait: str
    text: str


@dataclass(frozen=True)
class DialogueScene:
    """An ordered sequence of dialogue lines for one narrative beat."""

    key: str
    title: str
    lines: tuple[DialogueLine, ...]


# Canonical scene keys. Keep in sync with ``SCENES`` below.
INTRO: Final[str] = "intro"
FIRST_KILL: Final[str] = "first_kill"
FIRST_BOSS: Final[str] = "first_boss"
FIRST_DISTRO_SUCCESS: Final[str] = "first_distro_success"
ENDING: Final[str] = "ending"


SCENES: dict[str, DialogueScene] = {
    INTRO: DialogueScene(
        key=INTRO,
        title="// boot dialogue",
        lines=(
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="init(0): you have woken up. The system is bleeding memory.",
            ),
            DialogueLine(
                speaker="init(0)",
                portrait="init",
                text="Where am I? Is this the heap?",
            ),
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="Sector 0x00. Walk, fight, learn. The leak grows by the cycle.",
            ),
        ),
    ),
    FIRST_KILL: DialogueScene(
        key=FIRST_KILL,
        title="// first SIGKILL",
        lines=(
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="A process terminated. Its pages return to the free list.",
            ),
            DialogueLine(
                speaker="init(0)",
                portrait="init",
                text="That was easier than I expected.",
            ),
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="They get heavier. Stay sharp.",
            ),
        ),
    ),
    FIRST_BOSS: DialogueScene(
        key=FIRST_BOSS,
        title="// boss process detected",
        lines=(
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="Phase shift detected. A privileged process is on the line.",
            ),
            DialogueLine(
                speaker="init(0)",
                portrait="init",
                text="Then I'll send a signal it can't ignore.",
            ),
        ),
    ),
    FIRST_DISTRO_SUCCESS: DialogueScene(
        key=FIRST_DISTRO_SUCCESS,
        title="// distro cleared",
        lines=(
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="Distro cleared. New userland modules are now available.",
            ),
            DialogueLine(
                speaker="init(0)",
                portrait="init",
                text="One down. The leak is still growing.",
            ),
        ),
    ),
    ENDING: DialogueScene(
        key=ENDING,
        title="// shutdown -h now",
        lines=(
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="The leak is sealed. The heap is quiet again.",
            ),
            DialogueLine(
                speaker="init(0)",
                portrait="init",
                text="Then it's time to halt. Goodbye, kernel.",
            ),
            DialogueLine(
                speaker="kernel",
                portrait="kernel",
                text="Goodbye, init(0). You were a good process.",
            ),
        ),
    ),
}


def get_scene(key: str) -> DialogueScene:
    """Return the canonical scene for ``key`` or raise ``KeyError``."""
    return SCENES[key]
