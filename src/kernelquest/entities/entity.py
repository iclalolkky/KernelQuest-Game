"""Base entity for anything that lives on the grid."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Entity:
    """An object that occupies a single tile.

    Subclasses add behavior (player, malware, items). Pygame is **never**
    imported here - rendering is the renderer's job.
    """

    position: tuple[int, int]
    name: str
