"""Visual juice: screen shake and short-lived particles.

Pure data + math; the renderer is responsible for drawing.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from kernelquest.core.config import (
    PARTICLE_LIFETIME_FRAMES,
    SCREEN_SHAKE_DECAY,
)


@dataclass
class ScreenShake:
    """Decays toward zero each frame; sample with `offset(rng)`."""

    intensity: float = 0.0

    def punch(self, intensity: float) -> None:
        self.intensity = max(self.intensity, float(intensity))

    def step(self) -> None:
        if self.intensity <= 0.05:
            self.intensity = 0.0
            return
        self.intensity *= SCREEN_SHAKE_DECAY

    def offset(self, rng: random.Random) -> tuple[int, int]:
        if self.intensity <= 0:
            return (0, 0)
        amp = self.intensity
        return (
            int(round(rng.uniform(-amp, amp))),
            int(round(rng.uniform(-amp, amp))),
        )


@dataclass
class Particle:
    """A single short-lived visual sprite."""

    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    life: int = PARTICLE_LIFETIME_FRAMES
    max_life: int = PARTICLE_LIFETIME_FRAMES

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def alpha(self) -> int:
        return max(0, int(255 * (self.life / max(1, self.max_life))))


@dataclass
class ParticleSystem:
    """Spawns and steps clouds of particles."""

    particles: list[Particle] = field(default_factory=list)

    def step(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.92
            p.vy *= 0.92
            p.life -= 1
        self.particles = [p for p in self.particles if p.alive]

    def burst(
        self,
        position: tuple[float, float],
        color: tuple[int, int, int],
        rng: random.Random,
        count: int = 12,
        speed: float = 2.5,
    ) -> None:
        x, y = position
        for _ in range(count):
            angle = rng.uniform(0, math.tau)
            mag = rng.uniform(0.5, speed)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * mag,
                    vy=math.sin(angle) * mag,
                    color=color,
                )
            )

    def clear(self) -> None:
        self.particles.clear()
