
from __future__ import annotations

import logging
import sys

from kernelquest.core.engine import GameEngine


def main() -> int:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger(__name__)
    log.info("Kernel Quest booting…")
    GameEngine().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
