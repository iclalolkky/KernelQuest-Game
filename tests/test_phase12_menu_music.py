"""Phase 12.15 — synthesized menu theme."""

from __future__ import annotations

from kernelquest.ui.sfx import _build_menu_loop


def test_menu_loop_is_nonempty() -> None:
    pcm = _build_menu_loop()
    assert isinstance(pcm, bytes | bytearray)
    # 4 bars * 3000 ms at 44_100 Hz stereo int16 ≈ 2.1 MB; require at least 1 MB.
    assert len(pcm) > 1_000_000


def test_menu_loop_is_stereo_16bit_aligned() -> None:
    pcm = _build_menu_loop()
    # int16 stereo → 4 bytes per frame.
    assert len(pcm) % 4 == 0


def test_menu_loop_has_signal_energy() -> None:
    """A pure-zero buffer would mean the synth produced no audio."""
    pcm = _build_menu_loop()
    # Sum the absolute value of a sample of bytes — empty/silent track would
    # yield zero. We only inspect the middle of the loop to skip envelope tails.
    mid = pcm[len(pcm) // 3 : len(pcm) // 3 + 4096]
    assert any(b != 0 for b in mid)
