"""Pygame rendering. The UI layer is render-only — it never mutates state."""

from __future__ import annotations

import math
import random

import pygame

from kernelquest.core.config import (
    HUD_CPU_WAVE_HEIGHT,
    HUD_CPU_WAVE_WIDTH,
    HUD_MINIMAP_TILE,
    TILE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from kernelquest.entities.items import get_item
from kernelquest.entities.malware import KernelPanic, LogicBomb, Malware, SyntaxError_
from kernelquest.entities.player import Player
from kernelquest.ui import theme
from kernelquest.ui.console_log import ConsoleLog, LogLevel
from kernelquest.ui.fx import ParticleSystem, ScreenShake
from kernelquest.ui.viewport import Viewport
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

_LEVEL_COLORS: dict[LogLevel, tuple[int, int, int]] = {
    LogLevel.INFO: theme.NEON_CYAN,
    LogLevel.WARN: theme.NEON_AMBER,
    LogLevel.ERROR: (255, 110, 110),
    LogLevel.CRIT: theme.NEON_MAGENTA,
}

_CONSOLE_HEIGHT = 120


def _dim(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )


class UIManager:
    """Owns all `pygame.draw` calls."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font_small = pygame.font.SysFont("monospace", theme.FONT_SIZE_SMALL)
        self.font_body = pygame.font.SysFont("monospace", theme.FONT_SIZE_BODY)
        self.font_title = pygame.font.SysFont("monospace", theme.FONT_SIZE_TITLE, bold=True)
        self._wave_phase: float = 0.0
        self._fx_rng = random.Random(0xC0FFEE)

    # ----- frame plumbing -----

    def clear(self) -> None:
        self.screen.fill(theme.BACKGROUND)

    def present(self) -> None:
        pygame.display.flip()

    # ----- world rendering -----

    def render_world(
        self,
        world: World,
        viewport: Viewport,
        *,
        shake: ScreenShake | None = None,
        particles: ParticleSystem | None = None,
    ) -> None:
        offset = shake.offset(self._fx_rng) if shake is not None else (0, 0)
        shifted = Viewport(
            origin_x=viewport.origin_x + offset[0],
            origin_y=viewport.origin_y + offset[1],
            tile_size=viewport.tile_size,
        )
        self.render_grid(world, shifted)
        self.render_items(world, shifted)
        self.render_enemies(world, shifted)
        self.render_player(world.player, shifted)
        if particles is not None:
            self.render_particles(particles, shifted)

    def render_grid(self, world: World, viewport: Viewport) -> None:
        grid = world.grid
        for y in range(grid.height):
            for x in range(grid.width):
                pos = (x, y)
                if pos not in world.explored and world.explored:
                    continue
                tile = grid.get(x, y)
                base = _TILE_COLORS[tile]
                color = base if pos in world.visible or not world.visible else _dim(base, 0.45)
                sx, sy = viewport.to_screen(x, y)
                rect = pygame.Rect(sx, sy, viewport.tile_size, viewport.tile_size)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, theme.GRID_LINE, rect, 1)

    def render_items(self, world: World, viewport: Viewport) -> None:
        for (x, y), item_id in world.items.items():
            if world.visible and (x, y) not in world.visible:
                continue
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
            if world.visible and enemy.position not in world.visible:
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

    def render_particles(self, particles: ParticleSystem, viewport: Viewport) -> None:
        for p in particles.particles:
            sx = viewport.origin_x + int(p.x * viewport.tile_size)
            sy = viewport.origin_y + int(p.y * viewport.tile_size)
            size = max(1, int(3 * p.life / max(1, p.max_life)))
            surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*p.color, p.alpha), (size, size), size)
            self.screen.blit(surface, (sx - size, sy - size))

    # ----- HUD -----

    def render_hud(self, player: Player, sector: int, world: World) -> None:
        panel_x = WINDOW_WIDTH - 280
        panel_rect = pygame.Rect(panel_x, 16, 264, WINDOW_HEIGHT - 32 - _CONSOLE_HEIGHT)
        # Glassmorphism: translucent panel.
        glass = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 215))
        self.screen.blit(glass, panel_rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, panel_rect, width=1, border_radius=8)

        x = panel_x + 16
        y = 32
        self._blit_text("KERNEL QUEST", (x, y), theme.NEON_CYAN, self.font_body)
        y += 28
        self._blit_text(f"Sector  : 0x{sector:02X}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 22
        self._blit_text(f"Process : {player.name}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 28

        # RAM bar (color shifts when low).
        ram_ratio = player.ram / max(1, player.max_ram)
        ram_color = theme.NEON_GREEN
        if ram_ratio < 0.25:
            ram_color = (255, 110, 110)
        elif ram_ratio < 0.5:
            ram_color = theme.NEON_AMBER
        self._blit_text(
            f"RAM     : {player.ram}/{player.max_ram}", (x, y), ram_color, self.font_body
        )
        y += 22
        self._render_bar((x, y), 232, 10, ram_ratio, ram_color)
        y += 22

        # CPU sine-wave canvas.
        self._blit_text(
            f"CYCLES  : {player.cpu_cycles}/{player.max_cpu_cycles}",
            (x, y),
            theme.NEON_AMBER,
            self.font_body,
        )
        y += 22
        self._render_cpu_wave((x, y), player)
        y += HUD_CPU_WAVE_HEIGHT + 6

        self._blit_text(f"SCORE   : {player.score}", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 24

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
        y += 56

        if player.has_scan_boost:
            self._blit_text(
                f"SCAN+   : {player.scan_boost_turns}t",
                (x, y),
                theme.ITEM_SCAN_BOOST,
                self.font_body,
            )
            y += 22

        # Mini-map.
        self._render_minimap(world, (x, y))
        y += world.grid.height * HUD_MINIMAP_TILE + 12

        hints = [
            "[↑/↓/←/→] move / attack",
            "[space]    wait",
            "[1..9]     use cache slot",
            "[esc]      quit run",
        ]
        hint_y = panel_rect.bottom - 18 * len(hints) - 12
        for offset, text in enumerate(hints):
            self._blit_text(text, (x, hint_y + offset * 18), theme.TEXT_DIM, self.font_small)

    def render_console(self, log: ConsoleLog) -> None:
        rect = pygame.Rect(
            16, WINDOW_HEIGHT - _CONSOLE_HEIGHT - 8, WINDOW_WIDTH - 312, _CONSOLE_HEIGHT
        )
        glass = pygame.Surface(rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 200))
        self.screen.blit(glass, rect.topleft)
        pygame.draw.rect(self.screen, theme.GRID_LINE, rect, width=1, border_radius=6)

        pad_x = rect.x + 12
        line_h = self.font_small.get_height() + 2
        entries = log.entries()
        max_lines = max(1, (rect.height - 12) // line_h)
        visible = entries[-max_lines:]
        y = rect.y + 8
        for entry in visible:
            color = _LEVEL_COLORS.get(entry.level, theme.TEXT_PRIMARY)
            tag = self.font_small.render(f"[{entry.level.value}]", True, color)
            self.screen.blit(tag, (pad_x, y))
            msg = self.font_small.render(entry.message, True, theme.TEXT_PRIMARY)
            self.screen.blit(msg, (pad_x + 64, y))
            y += line_h

    # ----- screens -----

    def render_menu(self, options: list[str], selected: int) -> None:
        self.clear()
        title_surface = self.font_title.render("KERNEL QUEST", True, theme.NEON_CYAN)
        subtitle = self.font_body.render("The Memory Leak", True, theme.NEON_GREEN)
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        self.screen.blit(title_surface, title_surface.get_rect(center=(cx, cy - 180)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, cy - 140)))

        for i, label in enumerate(options):
            color = theme.NEON_CYAN if i == selected else theme.TEXT_PRIMARY
            prefix = "▶ " if i == selected else "  "
            surf = self.font_body.render(f"{prefix}{label}", True, color)
            self.screen.blit(surf, surf.get_rect(center=(cx, cy - 60 + i * 32)))

        hint = self.font_small.render(
            "[↑/↓] navigate  [enter] select  [esc] quit",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_high_scores(self, rows: list[tuple[str, int, int, str, str]]) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("HIGH SCORES", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        if not rows:
            empty = self.font_body.render("No runs recorded yet.", True, theme.TEXT_DIM)
            self.screen.blit(empty, empty.get_rect(center=(cx, WINDOW_HEIGHT // 2)))
        else:
            header = "{:<4}{:<18}{:>8}{:>8}  {:<14}{}".format(
                "#", "PROCESS", "SCORE", "DEPTH", "CRASH", "WHEN"
            )
            self._blit_text(header, (cx - 360, 120), theme.NEON_AMBER, self.font_body)
            for i, row in enumerate(rows):
                name, score, depth, cause, when = row
                line = "{:<4}{:<18}{:>8}{:>8}  {:<14}{}".format(
                    f"{i + 1}.", name[:16], score, depth, cause[:12], when[:16]
                )
                self._blit_text(line, (cx - 360, 152 + i * 24), theme.TEXT_PRIMARY, self.font_body)

        self._blit_back_hint()

    def render_stats(
        self,
        average_depth: float,
        deaths_by_cause: dict[str, int],
        best: tuple[str, int, int] | None,
        run_count: int,
    ) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("RUN STATS", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        x = cx - 240
        y = 130
        self._blit_text(
            f"Total runs       : {run_count}", (x, y), theme.TEXT_PRIMARY, self.font_body
        )
        y += 28
        self._blit_text(
            f"Average depth    : {average_depth:.2f}",
            (x, y),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        y += 28
        if best is not None:
            best_name, best_score, best_depth = best
            self._blit_text(
                f"Best run         : {best_name} — {best_score} pts (depth {best_depth})",
                (x, y),
                theme.NEON_GREEN,
                self.font_body,
            )
            y += 28
        else:
            self._blit_text("Best run         : —", (x, y), theme.TEXT_DIM, self.font_body)
            y += 28

        y += 12
        self._blit_text("Deaths by cause:", (x, y), theme.NEON_AMBER, self.font_body)
        y += 28
        if not deaths_by_cause:
            self._blit_text("  (no recorded crashes)", (x, y), theme.TEXT_DIM, self.font_body)
        else:
            for cause, count in deaths_by_cause.items():
                self._blit_text(
                    f"  {cause:<24} {count}",
                    (x, y),
                    theme.TEXT_PRIMARY,
                    self.font_body,
                )
                y += 22

        self._blit_back_hint()

    def render_shop(
        self,
        bits: int,
        rows: list[tuple[str, str, str, int, int, int | None]],
        selected: int,
        message: str | None = None,
    ) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("UPGRADE SHOP", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        bits_text = self.font_body.render(f"Bits available: {bits}", True, theme.NEON_GREEN)
        self.screen.blit(bits_text, bits_text.get_rect(center=(cx, 110)))

        x = cx - 360
        y = 160
        for i, row in enumerate(rows):
            key, label, desc, level, max_level, next_cost = row
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            prefix = "▶ " if is_sel else "  "
            cost_label = "MAX" if next_cost is None else f"{next_cost} bits"
            line = f"{prefix}{label:<10} L{level}/{max_level}    {desc}    [{cost_label}]"
            self._blit_text(line, (x, y), color, self.font_body)
            y += 28
            del key

        if message is not None:
            msg_surf = self.font_body.render(message, True, theme.NEON_AMBER)
            self.screen.blit(msg_surf, msg_surf.get_rect(center=(cx, WINDOW_HEIGHT - 90)))

        hint = self.font_small.render(
            "[↑/↓] select   [enter] buy   [esc] back",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_settings(self, options: list[tuple[str, str]], selected: int) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("SETTINGS", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 80)))

        x = cx - 220
        y = 180
        for i, (label, value) in enumerate(options):
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            prefix = "▶ " if is_sel else "  "
            self._blit_text(f"{prefix}{label:<14} : {value}", (x, y), color, self.font_body)
            y += 32

        hint = self.font_small.render(
            "[↑/↓] select   [←/→] adjust   [esc] back",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def _blit_back_hint(self) -> None:
        cx = WINDOW_WIDTH // 2
        hint = self.font_small.render("[esc] back", True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

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

    def _render_cpu_wave(self, pos: tuple[int, int], player: Player) -> None:
        """Live sine wave whose amplitude tracks current CPU cycles."""
        self._wave_phase += 0.18
        rect = pygame.Rect(pos[0], pos[1], HUD_CPU_WAVE_WIDTH, HUD_CPU_WAVE_HEIGHT)
        pygame.draw.rect(self.screen, theme.PANEL_BG, rect, border_radius=3)
        pygame.draw.rect(self.screen, theme.GRID_LINE, rect, width=1, border_radius=3)

        ratio = player.cpu_cycles / max(1, player.max_cpu_cycles)
        amp = (HUD_CPU_WAVE_HEIGHT / 2 - 2) * (0.2 + 0.8 * ratio)
        mid = rect.y + HUD_CPU_WAVE_HEIGHT // 2
        prev: tuple[int, int] | None = None
        for px in range(rect.width):
            theta = self._wave_phase + px * 0.22
            py = mid + int(amp * math.sin(theta))
            point = (rect.x + px, py)
            if prev is not None:
                pygame.draw.line(self.screen, theme.NEON_AMBER, prev, point, 1)
            prev = point

    def _render_minimap(self, world: World, pos: tuple[int, int]) -> None:
        ts = HUD_MINIMAP_TILE
        ox, oy = pos
        bg = pygame.Rect(ox - 2, oy - 2, world.grid.width * ts + 4, world.grid.height * ts + 4)
        pygame.draw.rect(self.screen, theme.PANEL_BG, bg, border_radius=4)
        for y in range(world.grid.height):
            for x in range(world.grid.width):
                if (x, y) not in world.explored and world.explored:
                    continue
                tile = world.grid.get(x, y)
                base = _TILE_COLORS[tile]
                if world.visible and (x, y) not in world.visible:
                    base = _dim(base, 0.55)
                pygame.draw.rect(self.screen, base, (ox + x * ts, oy + y * ts, ts, ts))
        # Draw entities on top.
        for enemy in world.enemies:
            if not enemy.is_alive:
                continue
            if world.visible and enemy.position not in world.visible:
                continue
            ex, ey = enemy.position
            pygame.draw.rect(self.screen, theme.NEON_MAGENTA, (ox + ex * ts, oy + ey * ts, ts, ts))
        px, py = world.player.position
        pygame.draw.rect(self.screen, theme.PLAYER_COLOR, (ox + px * ts, oy + py * ts, ts, ts))


__all__ = ["UIManager", "TILE_SIZE"]
