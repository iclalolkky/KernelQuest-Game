"""State Pattern handlers for `GameEngine`.

`GameEngine` delegates per-frame event handling and rendering to a
`GameStateHandler` instance selected by the current :class:`GameState`.

The handlers themselves are stateless singletons; they hold no game data and
read/write everything through the engine they are passed. This keeps the
``GameEngine`` as the single source of truth for game state while removing the
giant ``if/elif`` dispatch chains that previously lived in
``engine._handle_events`` and ``engine._render``.
"""

from kernelquest.core.states.base import GameStateHandler
from kernelquest.core.states.registry import build_state_registry, get_state_handler

__all__ = [
    "GameStateHandler",
    "build_state_registry",
    "get_state_handler",
]
