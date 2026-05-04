"""Entry point for Kernel Quest.

Run with:

    python -m kernelquest.main
"""

from __future__ import annotations

import logging
import sys


def main() -> int:
    """Bootstrap the game.

    Returns:
        Process exit code.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger(__name__)
    log.info("Kernel Quest booting…")

    # TODO(agent): instantiate GameEngine and run the main loop (Phase 1).
    log.info("GameEngine not yet implemented — exiting cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
