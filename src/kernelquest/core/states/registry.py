"""`GameState -> GameStateHandler` registry."""

from __future__ import annotations

from kernelquest.core.state import GameState
from kernelquest.core.states.base import GameStateHandler
from kernelquest.core.states.cinematic_states import (
    CodexStateHandler,
    EndingStateHandler,
    IntroStateHandler,
)
from kernelquest.core.states.game_over_state import (
    GameOverStateHandler,
    RunSummaryStateHandler,
)
from kernelquest.core.states.menu_states import (
    DailyBoardStateHandler,
    DistroSelectStateHandler,
    HighScoresStateHandler,
    HowToPlayStateHandler,
    MenuStateHandler,
    SettingsStateHandler,
    StatsStateHandler,
)
from kernelquest.core.states.playing_states import (
    BestiaryStateHandler,
    InspectStateHandler,
    MilestoneResultStateHandler,
    PatchPickStateHandler,
    PlayingStateHandler,
    StackTraceStateHandler,
    VendorStateHandler,
)
from kernelquest.core.states.shop_state import ShopStateHandler
from kernelquest.core.states.tutorial_state import (
    TutorialRangeStateHandler,
    TutorialStateHandler,
)


def build_state_registry() -> dict[GameState, GameStateHandler]:
    """Construct the canonical mapping from :class:`GameState` to handler.

    Handlers are stateless singletons; one instance per state is plenty.
    The QUIT state has no handler — the engine's main loop terminates as
    soon as :class:`GameState.QUIT` is set.
    """
    return {
        GameState.MENU: MenuStateHandler(),
        GameState.SETTINGS: SettingsStateHandler(),
        GameState.HOWTOPLAY: HowToPlayStateHandler(),
        GameState.HIGH_SCORES: HighScoresStateHandler(),
        GameState.STATS: StatsStateHandler(),
        GameState.DAILY_BOARD: DailyBoardStateHandler(),
        GameState.DISTRO_SELECT: DistroSelectStateHandler(),
        GameState.PLAYING: PlayingStateHandler(),
        GameState.PATCH_PICK: PatchPickStateHandler(),
        GameState.STACK_TRACE: StackTraceStateHandler(),
        GameState.BESTIARY: BestiaryStateHandler(),
        GameState.INSPECT: InspectStateHandler(),
        GameState.MILESTONE_RESULT: MilestoneResultStateHandler(),
        GameState.VENDOR: VendorStateHandler(),
        GameState.SHOP: ShopStateHandler(),
        GameState.TUTORIAL: TutorialStateHandler(),
        GameState.TUTORIAL_RANGE: TutorialRangeStateHandler(),
        GameState.INTRO: IntroStateHandler(),
        GameState.ENDING: EndingStateHandler(),
        GameState.CODEX: CodexStateHandler(),
        GameState.GAME_OVER: GameOverStateHandler(),
        GameState.RUN_SUMMARY: RunSummaryStateHandler(),
    }


_DEFAULT_REGISTRY: dict[GameState, GameStateHandler] | None = None


def get_state_handler(state: GameState) -> GameStateHandler | None:
    """Return the handler for ``state`` from the lazily-built default registry.

    Returns ``None`` for :attr:`GameState.QUIT`, which has no handler.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_state_registry()
    return _DEFAULT_REGISTRY.get(state)
