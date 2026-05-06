"""Grid'de yaşayan herhangi bir şey için temel varlık."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Entity:
    """Tek bir kareyi işgal eden bir nesne.

    Alt sınıflar davranış ekler (oyuncu, malware, itemler). Pygame **asla**
    buraya içe aktarılmaz - renderleme rendercinin işi.
    """

    position: tuple[int, int]
    name: str
