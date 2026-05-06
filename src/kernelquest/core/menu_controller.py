"""Menu and side-screen input handling (menu, settings, shop, tutorial).

This controller owns input/state-transition logic for every non-gameplay
screen. The owning :class:`GameEngine` delegates key events here and reads
back tabular data via :meth:`shop_rows` / :meth:`settings_rows` /
:meth:`fetch_high_scores` / :meth:`fetch_stats` / :meth:`fetch_bits`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from kernelquest.core import settings as settings_module
from kernelquest.core.state import GameState
from kernelquest.data.upgrades_catalog import CATALOG

if TYPE_CHECKING:
    from kernelquest.core.engine import GameEngine

_KEY_BITS = "meta.bits"

MENU_OPTIONS: tuple[str, ...] = (
    "Yeni RUN",
    "Nasıl Oynanır",
    "Yüksek Skorlar",
    "İstatistikler",
    "Mağaza",
    "Ayarlar",
    "Çıkış",
)


class MenuController:
    """Handles input + data fetching for menu and side screens."""

    def __init__(self, engine: GameEngine) -> None:
        self._engine = engine

    # ----- key handlers -----

    def handle_menu_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        if event.key == pygame.K_ESCAPE:
            eng._state = GameState.QUIT_CONFIRM
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            eng._menu_index = (eng._menu_index - 1) % len(MENU_OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            eng._menu_index = (eng._menu_index + 1) % len(MENU_OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate_menu_option()

    def _activate_menu_option(self) -> None:
        eng = self._engine
        choice = MENU_OPTIONS[eng._menu_index]
        if choice == "Yeni RUN":
            eng._start_new_run()
        elif choice == "Nasıl Oynanır":
            eng._tutorial_page = 0
            eng._state = GameState.TUTORIAL
        elif choice == "Yüksek Skorlar":
            eng._state = GameState.HIGH_SCORES
        elif choice == "İstatistikler":
            eng._state = GameState.STATS
        elif choice == "Mağaza":
            eng._shop_index = 0
            eng._shop_message = None
            eng._state = GameState.SHOP
        elif choice == "Ayarlar":
            eng._settings_index = 0
            eng._state = GameState.SETTINGS
        elif choice == "Çıkış":
            eng._state = GameState.QUIT_CONFIRM

    def handle_quit_confirm_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
            eng._state = GameState.QUIT
        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
            eng._state = GameState.MENU

    def handle_back_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._engine._state = GameState.MENU

    def handle_tutorial_key(self, event: pygame.event.Event) -> None:
        from kernelquest.ui.renderer import TUTORIAL_PAGE_COUNT

        eng = self._engine
        if event.key == pygame.K_ESCAPE:
            eng._state = GameState.MENU
            return
        if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_PAGEUP):
            eng._tutorial_page = max(0, eng._tutorial_page - 1)
        elif event.key in (
            pygame.K_RIGHT,
            pygame.K_d,
            pygame.K_PAGEDOWN,
            pygame.K_SPACE,
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
        ):
            if eng._tutorial_page >= TUTORIAL_PAGE_COUNT - 1:
                eng._state = GameState.MENU
            else:
                eng._tutorial_page += 1

    def handle_shop_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        if event.key == pygame.K_ESCAPE:
            eng._state = GameState.MENU
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            eng._shop_index = (eng._shop_index - 1) % len(CATALOG)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            eng._shop_index = (eng._shop_index + 1) % len(CATALOG)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._buy_selected_upgrade()

    def _buy_selected_upgrade(self) -> None:
        eng = self._engine
        if eng._upgrades is None or eng._meta is None:
            return
        upgrade = CATALOG[eng._shop_index]
        current = eng._upgrades.get_level(upgrade.key)
        cost = upgrade.cost_for_next_level(current)
        if cost is None:
            eng._shop_message = f"{upgrade.label} azami seviyede."
            return
        bits = eng._meta.get_int(_KEY_BITS, 0)
        if bits < cost:
            eng._shop_message = f"Yeterli bits yok ({bits}/{cost})."
            return
        eng._meta.set_int(_KEY_BITS, bits - cost)
        eng._upgrades.set_level(upgrade.key, current + 1)
        eng._shop_message = f"{upgrade.label} L{current + 1} alındı ({cost} bits)."

    def handle_settings_key(self, event: pygame.event.Event) -> None:
        eng = self._engine
        if event.key == pygame.K_ESCAPE:
            assert eng._meta is not None
            settings_module.save(eng._meta, eng._settings)
            eng._state = GameState.MENU
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            eng._settings_index = (eng._settings_index - 1) % 2
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            eng._settings_index = (eng._settings_index + 1) % 2
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._adjust_setting(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._adjust_setting(+1)

    def _adjust_setting(self, direction: int) -> None:
        eng = self._engine
        if eng._settings_index == 0:
            eng._settings.adjust_volume(0.1 * direction)
            if eng._sfx is not None:
                eng._sfx.set_volume(eng._settings.volume)
        else:
            eng._settings.cycle_difficulty()

    # ----- data getters used by render dispatcher -----

    def fetch_bits(self) -> int:
        meta = self._engine._meta
        return meta.get_int(_KEY_BITS, 0) if meta is not None else 0

    def shop_rows(self) -> list[tuple[str, str, str, int, int, int | None]]:
        upgrades = self._engine._upgrades
        if upgrades is None:
            return []
        levels = upgrades.all_levels()
        rows: list[tuple[str, str, str, int, int, int | None]] = []
        for upgrade in CATALOG:
            level = levels.get(upgrade.key, 0)
            rows.append(
                (
                    upgrade.key,
                    upgrade.label,
                    upgrade.description,
                    level,
                    upgrade.max_level,
                    upgrade.cost_for_next_level(level),
                )
            )
        return rows

    def settings_rows(self) -> list[tuple[str, str]]:
        s = self._engine._settings
        difficulty_label = {
            "EASY": "KOLAY",
            "NORMAL": "NORMAL",
            "HARD": "ZOR",
        }.get(s.difficulty.value, s.difficulty.value)
        return [
            ("Ses", f"{int(round(s.volume * 100))}%"),
            ("Zorluk", difficulty_label),
        ]

    def fetch_high_scores(self) -> list[tuple[str, int, int, str, str]]:
        scores = self._engine._scores
        if scores is None:
            return []
        rows = scores.top_n(10)
        return [
            (r.player_name, r.total_score, r.depth_reached, r.crash_cause, r.timestamp)
            for r in rows
        ]

    def fetch_stats(
        self,
    ) -> tuple[float, dict[str, int], tuple[str, int, int] | None, int]:
        runs = self._engine._runs
        if runs is None:
            return (0.0, {}, None, 0)
        all_runs = runs.all()
        avg = runs.average_depth()
        deaths = runs.deaths_by_cause()
        best = runs.best()
        best_tuple: tuple[str, int, int] | None = None
        if best is not None:
            best_tuple = (best.player_name, best.total_score, best.depth_reached)
        return (avg, deaths, best_tuple, len(all_runs))
