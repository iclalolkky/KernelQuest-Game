"""Smoke tests that verify the package imports cleanly."""

from __future__ import annotations


def test_package_imports() -> None:
    import kernelquest

    assert kernelquest.__version__


def test_main_entrypoint_returns_zero() -> None:
    from kernelquest.main import main

    assert main() == 0
