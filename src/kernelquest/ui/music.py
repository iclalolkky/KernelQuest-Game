"""Phase 8 — adaptive stem-based music director.

Authors compose a base "bed" plus archetype-specific stems. The
``StemMixer`` decides which stems should be audible based on the
visible enemy archetypes, then crossfades targets toward 0/1 over a
fixed window (250–500 ms).

The mixer is intentionally pygame-free so unit tests can exercise the
volume math without an audio device. ``SoundManager`` owns a mixer
instance and forwards stem volumes to ``pygame.mixer`` channels when
audio is initialised.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kernelquest.entities.malware_registry import Archetype

# Mapping: archetype → stem key that should activate when any enemy of
# that archetype is visible to the player.
ARCHETYPE_STEMS: dict[Archetype, str] = {
    Archetype.SKIRMISHER: "melody_lead",
    Archetype.BRUISER: "tension_low",
    Archetype.SAPPER: "tension_lead",
    Archetype.CASTER: "melody_arp",
    Archetype.STALKER: "tension_pad",
    Archetype.SUPPORT: "melody_pad",
    Archetype.REVENANT: "tension_low",
    Archetype.BOSS: "boss",
}

ALL_STEMS: tuple[str, ...] = (
    "bed",
    "melody_lead",
    "melody_arp",
    "melody_pad",
    "tension_lead",
    "tension_low",
    "tension_pad",
    "boss",
)

#: Maximum stems active simultaneously when reduce-motion is enabled.
REDUCE_MOTION_STEM_LIMIT: int = 2

#: Per-frame fade speed (volume units per second). 4.0 = ~250 ms.
FADE_RATE_PER_SEC: float = 4.0


@dataclass
class StemMixer:
    """Crossfading mixer for a fixed pool of named stems.

    Volumes live in ``[0.0, 1.0]``. The mixer never mutates an underlying
    audio device on its own — call :py:meth:`current_volumes` after each
    update and route the result to a sink (``pygame.mixer.Channel`` in the
    real game, a fake in tests).
    """

    targets: dict[str, float] = field(default_factory=dict)
    volumes: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for stem in ALL_STEMS:
            self.targets.setdefault(stem, 0.0)
            self.volumes.setdefault(stem, 0.0)
        # Bed track is always on by default.
        self.targets["bed"] = 1.0

    def update_targets(
        self,
        archetypes: set[Archetype],
        *,
        boss_active: bool,
        reduce_motion: bool = False,
    ) -> None:
        """Recompute target volumes from the current visible archetypes."""
        new_targets = {stem: 0.0 for stem in ALL_STEMS}
        new_targets["bed"] = 1.0
        if boss_active:
            new_targets["boss"] = 1.0
        for arc in archetypes:
            stem = ARCHETYPE_STEMS.get(arc)
            if stem is not None:
                new_targets[stem] = 1.0
        if reduce_motion:
            # Keep at most ``REDUCE_MOTION_STEM_LIMIT`` non-bed stems hot.
            extras = [k for k, v in new_targets.items() if v > 0 and k != "bed"]
            if len(extras) > REDUCE_MOTION_STEM_LIMIT:
                # Stable order — boss > tension > melody.
                priority = (
                    "boss",
                    "tension_lead",
                    "tension_low",
                    "tension_pad",
                    "melody_lead",
                    "melody_arp",
                    "melody_pad",
                )
                kept = [k for k in priority if k in extras][:REDUCE_MOTION_STEM_LIMIT]
                for k in extras:
                    if k not in kept:
                        new_targets[k] = 0.0
        self.targets = new_targets

    def step(self, dt: float) -> None:
        """Crossfade ``volumes`` toward ``targets`` by ``dt`` seconds."""
        if dt <= 0.0:
            return
        delta = FADE_RATE_PER_SEC * dt
        for stem in ALL_STEMS:
            cur = self.volumes.get(stem, 0.0)
            tgt = self.targets.get(stem, 0.0)
            if cur < tgt:
                self.volumes[stem] = min(tgt, cur + delta)
            elif cur > tgt:
                self.volumes[stem] = max(tgt, cur - delta)

    def current_volumes(self) -> dict[str, float]:
        return dict(self.volumes)

    def active_stems(self, threshold: float = 0.05) -> set[str]:
        return {k for k, v in self.volumes.items() if v >= threshold}


__all__ = [
    "ARCHETYPE_STEMS",
    "ALL_STEMS",
    "FADE_RATE_PER_SEC",
    "REDUCE_MOTION_STEM_LIMIT",
    "StemMixer",
]
