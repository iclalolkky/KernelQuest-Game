"""Pygame rendering. The UI layer is render-only — it never mutates state."""

from __future__ import annotations

import pygame

from kernelquest.core.config import (
    TILE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from kernelquest.entities.items import get_item
from kernelquest.entities.malware import KernelPanic, LogicBomb, Malware, SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.ui import theme
from kernelquest.ui.viewport import Viewport
from kernelquest.world.grid import MemoryGrid
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

_TILE_COLORS: dict[TileType, tuple[int, int, int]] = {
    TileType.EMPTY: theme.TILE_EMPTY,
    TileType.SYSTEM_DATA: theme.TILE_SYSTEM_DATA,
    TileType.BAD_SECTOR: theme.TILE_BAD_SECTOR,
    TileType.EXIT: theme.TILE_EXIT,
}

_ITEM_COLORS: dict[str, tuple[int, int, int]] = {
    "gc": theme.ITEM_GC,
    "opt": theme.ITEM_OPTIMIZATION,
    "scan": theme.ITEM_SCAN_BOOST,
}


class UIManager:
    """Owns all `pygame.draw` calls."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font_small = pygame.font.SysFont("monospace", theme.FONT_SIZE_SMALL)
        self.font_body = pygame.font.SysFont("monospace", theme.FONT_SIZE_BODY)
        self.font_title = pygame.font.SysFont("monospace", theme.FONT_SIZE_TITLE, bold=True)

    # ----- frame plumbing -----

    def clear(self) -> None:
        self.screen.fill(theme.BACKGROUND)

    def present(self) -> None:
        pygame.display.flip()

    # ----- world rendering -----

    def render_world(self, world: World, viewport: Viewport) -> None:
        self.render_grid(world.grid, viewport)
        self.render_items(world, viewport)
        self.render_enemies(world, viewport)
        self.render_player(world.player, viewport)

    def render_grid(self, grid: MemoryGrid, viewport: Viewport) -> None:
        for y in range(grid.height):
            for x in range(grid.width):
                tile = grid.get(x, y)
                sx, sy = viewport.to_screen(x, y)
                rect = pygame.Rect(sx, sy, viewport.tile_size, viewport.tile_size)
                pygame.draw.rect(self.screen, _TILE_COLORS[tile], rect)
                pygame.draw.rect(self.screen, theme.GRID_LINE, rect, 1)

    def render_items(self, world: World, viewport: Viewport) -> None:
        for (x, y), item_id in world.items.items():
            sx, sy = viewport.to_screen(x, y)
            cx = sx + viewport.tile_size // 2
            cy = sy + viewport.tile_size // 2
            color = _ITEM_COLORS.get(item_id, theme.NEON_CYAN)
            pygame.draw.circle(self.screen, color, (cx, cy), viewport.tile_size // 4)
            label = get_item(item_id).short_label
            surface = self.font_small.render(label, True, theme.BACKGROUND)
            self.screen.blit(surface, surface.get_rect(center=(cx, cy)))

    def render_enemies(self, world: World, viewport: Viewport) -> None:
        for enemy in world.enemies:
            if not enemy.is_alive:
                continue
            self._render_enemy(enemy, viewport)

    def _render_enemy(self, enemy: Malware, viewport: Viewport) -> None:
        sx, sy = viewport.to_screen(*enemy.position)
        rect = pygame.Rect(sx + 4, sy + 4, viewport.tile_size - 8, viewport.tile_size - 8)
        if isinstance(enemy, KernelPanic):
            color = theme.ENEMY_KERNEL_PANIC
        elif isinstance(enemy, LogicBomb):
            color = theme.ENEMY_LOGIC_BOMB
        elif isinstance(enemy, SyntaxError_):
            color = theme.ENEMY_SYNTAX_ERROR
        else:
            color = theme.NEON_AMBER
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BACKGROUND, rect, width=1, border_radius=4)

        # HP pip strip above the sprite.
        pip_count = max(1, min(8, enemy.max_hp // 4))
        pip_w = (viewport.tile_size - 8) // pip_count
        filled = int(round(pip_count * (enemy.hp / max(1, enemy.max_hp))))
        for i in range(pip_count):
            pip_color = color if i < filled else theme.PANEL_BG
            pip_rect = pygame.Rect(sx + 4 + i * pip_w, sy + 1, max(2, pip_w - 1), 3)
            pygame.draw.rect(self.screen, pip_color, pip_rect)

    def render_player(self, player: Player, viewport: Viewport) -> None:
        sx, sy = viewport.to_screen(*player.position)
        center = (sx + viewport.tile_size // 2, sy + viewport.tile_size // 2)
        radius = viewport.tile_size // 2 - 4
        pygame.draw.circle(self.screen, theme.PLAYER_COLOR, center, radius)
        pygame.draw.circle(self.screen, theme.NEON_CYAN, center, radius, 2)
        if player.has_scan_boost:
            pygame.draw.circle(self.screen, theme.ITEM_SCAN_BOOST, center, radius + 4, 1)

    # ----- HUD -----

    def render_hud(self, player: Player, sector: int) -> None:
        panel_x = WINDOW_WIDTH - 280
        panel_rect = pygame.Rect(panel_x, 16, 264, WINDOW_HEIGHT - 32)
        pygame.draw.rect(self.screen, theme.PANEL_BG, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, panel_rect, width=1, border_radius=8)

        x = panel_x + 16
        y = 32
        self._blit_text("KERNEL QUEST", (x, y), theme.NEON_CYAN, self.font_body)
        y += 32
        self._blit_text(f"Sector  : 0x{sector:02X}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 24
        self._blit_text(f"Process : {player.name}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 32

        # RAM bar
        self._blit_text(
            f"RAM     : {player.ram}/{player.max_ram}",
            (x, y),
            theme.NEON_GREEN,
            self.font_body,
        )
        y += 22
        self._render_bar(
            (x, y),
            width=232,
            height=10,
            ratio=player.ram / max(1, player.max_ram),
            color=theme.NEON_GREEN,
        )
        y += 24

        # CPU cycles
        self._blit_text(
            f"CYCLES  : {player.cpu_cycles}/{player.max_cpu_cycles}",
            (x, y),
            theme.NEON_AMBER,
            self.font_body,
        )
        y += 22
        self._render_bar(
            (x, y),
            width=232,
            height=10,
            ratio=player.cpu_cycles / max(1, player.max_cpu_cycles),
            color=theme.NEON_AMBER,
        )
        y += 28

        self._blit_text(f"SCORE   : {player.score}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 28

        # Cache slots.
        self._blit_text(
            f"CACHE   : {len(player.cache)}/{player.cache_capacity}",
            (x, y),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        y += 22
        for i, item_id in enumerate(player.cache):
            item = get_item(item_id)
            color = _ITEM_COLORS.get(item_id, theme.NEON_CYAN)
            slot_rect = pygame.Rect(x + (i % 8) * 28, y + (i // 8) * 28, 24, 24)
            pygame.draw.rect(self.screen, color, slot_rect, border_radius=4)
            label = self.font_small.render(item.short_label, True, theme.BACKGROUND)
            self.screen.blit(label, label.get_rect(center=slot_rect.center))
            slot_index = self.font_small.render(f"{i + 1}", True, theme.TEXT_DIM)
            self.screen.blit(slot_index, (slot_rect.x, slot_rect.bottom + 2))
        y += 60

        if player.has_scan_boost:
            self._blit_text(
                f"SCAN+   : {player.scan_boost_turns}t",
                (x, y),
                theme.ITEM_SCAN_BOOST,
                self.font_body,
            )
            y += 22

        # Controls hint at bottom of panel.
        hint_y = panel_rect.bottom - 132
        hints = [
            "[↑/↓/←/→] move / attack",
            "[space]    wait",
            "[1..9]     use cache slot",
            "[esc]      quit run",
        ]
        for offset, text in enumerate(hints):
            self._blit_text(text, (x, hint_y + offset * 18), theme.TEXT_DIM, self.font_small)

    # ----- screens -----

    def render_menu(self) -> None:
        self.clear()
        title_surface = self.font_title.render("KERNEL QUEST", True, theme.NEON_CYAN)
        subtitle = self.font_body.render("The Memory Leak", True, theme.NEON_GREEN)
        prompt = self.font_body.render(
            "[ENTER] to spawn process    [ESC] to quit",
            True,
            theme.TEXT_PRIMARY,
        )
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        self.screen.blit(title_surface, title_surface.get_rect(center=(cx, cy - 60)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, cy - 20)))
        self.screen.blit(prompt, prompt.get_rect(center=(cx, cy + 60)))

    def render_game_over(self, player: Player, name_buffer: str) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        title = self.font_title.render("SYSTEM CRASH", True, theme.NEON_MAGENTA)
        cause = self.font_body.render(
            f"Crash cause: {player.crash_cause or 'unknown'}",
            True,
            theme.TEXT_PRIMARY,
        )
        score = self.font_body.render(
            f"Sectors cleared: {player.depth_reached}    Score: {player.score}",
            True,
            theme.TEXT_PRIMARY,
        )
        prompt = self.font_body.render(
            "Enter process name and press [ENTER]:", True, theme.NEON_CYAN
        )
        name_text = self.font_title.render(name_buffer + "_", True, theme.NEON_GREEN)

        self.screen.blit(title, title.get_rect(center=(cx, cy - 140)))
        self.screen.blit(cause, cause.get_rect(center=(cx, cy - 80)))
        self.screen.blit(score, score.get_rect(center=(cx, cy - 50)))
        self.screen.blit(prompt, prompt.get_rect(center=(cx, cy + 10)))
        self.screen.blit(name_text, name_text.get_rect(center=(cx, cy + 60)))

    # ----- helpers -----

    def _blit_text(
        self,
        text: str,
        pos: tuple[int, int],
        color: tuple[int, int, int],
        font: pygame.font.Font,
    ) -> None:
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def _render_bar(
        self,
        pos: tuple[int, int],
        width: int,
        height: int,
        ratio: float,
        color: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        bg = pygame.Rect(pos[0], pos[1], width, height)
        fg = pygame.Rect(pos[0], pos[1], int(width * ratio), height)
        pygame.draw.rect(self.screen, theme.PANEL_BG, bg, border_radius=3)
        pygame.draw.rect(self.screen, color, fg, border_radius=3)
        pygame.draw.rect(self.screen, theme.GRID_LINE, bg, width=1, border_radius=3)


__all__ = ["UIManager", "TILE_SIZE"]
