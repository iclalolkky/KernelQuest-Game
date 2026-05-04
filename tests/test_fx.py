"""Tests for FX primitives: screen shake and particle system."""

from __future__ import annotations

import random

from kernelquest.ui.fx import ParticleSystem, ScreenShake


def test_screen_shake_decays_to_zero() -> None:
    shake = ScreenShake()
    shake.punch(8.0)
    assert shake.intensity == 8.0
    for _ in range(60):
        shake.step()
    assert shake.intensity == 0.0


def test_screen_shake_offset_zero_when_inactive() -> None:
    shake = ScreenShake()
    rng = random.Random(0)
    assert shake.offset(rng) == (0, 0)


def test_screen_shake_punch_keeps_max() -> None:
    shake = ScreenShake(intensity=5.0)
    shake.punch(2.0)
    assert shake.intensity == 5.0
    shake.punch(9.0)
    assert shake.intensity == 9.0


def test_particle_burst_adds_particles() -> None:
    system = ParticleSystem()
    rng = random.Random(0)
    system.burst((1.0, 1.0), color=(255, 0, 0), rng=rng, count=10)
    assert len(system.particles) == 10
    assert all(p.alive for p in system.particles)


def test_particle_step_kills_after_lifetime() -> None:
    system = ParticleSystem()
    rng = random.Random(0)
    system.burst((0.0, 0.0), color=(0, 255, 0), rng=rng, count=3)
    for _ in range(200):
        system.step()
    assert system.particles == []
