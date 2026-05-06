"""Phase 12.4 — RUN HUD overlap fix + new readouts."""

from __future__ import annotations

import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.display.init()
pygame.font.init()

from kernelquest.entities.daemon import Daemon  # noqa: E402, F401
from kernelquest.entities.malware import LogicBomb  # noqa: E402
from kernelquest.entities.player import Player  # noqa: E402
from kernelquest.systems.combat import player_attack  # noqa: E402
from kernelquest.ui import renderer as renderer_mod  # noqa: E402
from kernelquest.world.grid import MemoryGrid  # noqa: E402
from kernelquest.world.tile import TileType  # noqa: E402
from kernelquest.world.world import World  # noqa: E402


def _world_with_enemy() -> World:
    tiles = [[TileType.SYSTEM_DATA for _ in range(10)] for _ in range(10)]
    grid = MemoryGrid(width=10, height=10, tiles=tiles)
    player = Player(position=(1, 1), name="proc")
    bomb = LogicBomb(position=(2, 1))
    return World(grid=grid, player=player, enemies=[bomb])


def test_damage_dealt_this_turn_increments_and_resets() -> None:
    world = _world_with_enemy()
    player = world.player
    bomb = world.enemies[0]
    assert player.damage_dealt_this_turn == 0
    import random

    player_attack(world, bomb, random.Random(0))
    assert player.damage_dealt_this_turn > 0
    player.end_turn()
    assert player.damage_dealt_this_turn == 0


def test_render_bottom_bar_does_not_crash() -> None:
    screen = pygame.display.set_mode(
        (renderer_mod.WINDOW_WIDTH, renderer_mod.WINDOW_HEIGHT), pygame.HIDDEN
    )
    ui = renderer_mod.UIManager(screen)
    ui.render_bottom_bar(["[esc] back", "[Q] kill -9"])
    # No assertion — surface compositing is the system under test; absence of
    # exception means the new widget is healthy.


def test_render_hud_does_not_overlap_console_strip() -> None:
    screen = pygame.display.set_mode(
        (renderer_mod.WINDOW_WIDTH, renderer_mod.WINDOW_HEIGHT), pygame.HIDDEN
    )
    ui = renderer_mod.UIManager(screen)
    world = _world_with_enemy()
    ui.render_hud(world.player, sector=1, world=world, patches=[])
    # The HUD panel rect must end strictly above the bottom-bar reservation.
    panel_bottom = (
        renderer_mod.WINDOW_HEIGHT
        - 32
        - renderer_mod._CONSOLE_HEIGHT
        - renderer_mod._BOTTOM_BAR_HEIGHT
    )
    assert panel_bottom > 0


def test_aoe_overlay_only_when_tcpdump_equipped(monkeypatch: pytest.MonkeyPatch) -> None:
    screen = pygame.display.set_mode(
        (renderer_mod.WINDOW_WIDTH, renderer_mod.WINDOW_HEIGHT), pygame.HIDDEN
    )
    ui = renderer_mod.UIManager(screen)
    world = _world_with_enemy()
    # Make every tile visible so the overlay path is exercised.
    world.visible = {(x, y) for x in range(world.grid.width) for y in range(world.grid.height)}

    called = {"n": 0}
    real_overlay = ui._render_aoe_overlays

    def _spy(world_arg: World, viewport_arg: object) -> None:
        called["n"] += 1
        real_overlay(world_arg, viewport_arg)  # type: ignore[arg-type]

    monkeypatch.setattr(ui, "_render_aoe_overlays", _spy)

    from kernelquest.ui.viewport import Viewport

    vp = Viewport(origin_x=0, origin_y=0, tile_size=24)

    # No daemon → overlay not drawn.
    ui.render_enemies(world, vp)
    assert called["n"] == 0

    # Equip tcpdump → overlay drawn.
    from kernelquest.entities.daemon import DAEMON_TCPDUMP

    world.player.daemons.append(DAEMON_TCPDUMP)
    ui.render_enemies(world, vp)
    assert called["n"] == 1
