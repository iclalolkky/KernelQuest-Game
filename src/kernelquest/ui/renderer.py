"""Pygame rendering. The UI layer is render-only — it never mutates state."""

from __future__ import annotations

import math
import random
from typing import Final, cast

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
from kernelquest.ui.cinematics import CinematicPlayer, render_cinematic
from kernelquest.ui.console_log import ConsoleLog, LogLevel
from kernelquest.ui.fx import ParticleSystem, ScreenShake
from kernelquest.ui.sprites import (
    FrameClock,
    PlayerPalette,
    draw_enemy_sprite,
    draw_player_nameplate,
    draw_player_sprite,
    get_player_palette,
)
from kernelquest.ui.viewport import Viewport
from kernelquest.world.tile import TileType
from kernelquest.world.world import World

_TILE_COLOR_KEYS: dict[TileType, str] = {
    TileType.EMPTY: "TILE_EMPTY",
    TileType.SYSTEM_DATA: "TILE_SYSTEM_DATA",
    TileType.BAD_SECTOR: "TILE_BAD_SECTOR",
    TileType.EXIT: "TILE_EXIT",
}

# Direct color lookup used by tutorial helpers.
_TILE_COLORS: dict[TileType, tuple[int, int, int]] = {
    TileType.EMPTY: theme.TILE_EMPTY,
    TileType.SYSTEM_DATA: theme.TILE_SYSTEM_DATA,
    TileType.BAD_SECTOR: theme.TILE_BAD_SECTOR,
    TileType.EXIT: theme.TILE_EXIT,
}

_ITEM_COLOR_KEYS: dict[str, str] = {
    "gc": "ITEM_GC",
    "opt": "ITEM_OPTIMIZATION",
    "scan": "ITEM_SCAN_BOOST",
}

_LEVEL_COLOR_KEYS: dict[LogLevel, str] = {
    LogLevel.INFO: "NEON_CYAN",
    LogLevel.WARN: "NEON_AMBER",
    LogLevel.ERROR: "NEON_MAGENTA",
    LogLevel.CRIT: "NEON_MAGENTA",
}


def _tile_color(tile: TileType) -> tuple[int, int, int]:
    return getattr(theme, _TILE_COLOR_KEYS[tile])  # type: ignore[no-any-return]


def _item_color(item_id: str) -> tuple[int, int, int]:
    attr = _ITEM_COLOR_KEYS.get(item_id)
    return getattr(theme, attr) if attr else theme.NEON_CYAN


def _level_color(level: LogLevel) -> tuple[int, int, int]:
    if level is LogLevel.ERROR:
        return (255, 110, 110)
    return getattr(theme, _LEVEL_COLOR_KEYS.get(level, "TEXT_PRIMARY"))  # type: ignore[no-any-return]


# ---- Tutorial page titles (i18n keys used for structural chrome) ----------

_TUTORIAL_PAGE_TITLE_KEYS: Final[tuple[str, ...]] = (
    "tutorial.page1_title",
    "tutorial.page2_title",
    "tutorial.page3_title",
    "tutorial.page4_title",
    "tutorial.page5_title",
    "tutorial.page6_title",
    "tutorial.page7_title",
)

TUTORIAL_PAGE_COUNT: Final[int] = len(_TUTORIAL_PAGE_TITLE_KEYS)


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
        # Phase 7 — sprite animation clock + selected palette.
        self.frame_clock = FrameClock()
        self.player_palette: PlayerPalette = get_player_palette("kernel")
        # Interactive menu — animated character avatar position.
        self._menu_avatar_y: float = 0.0
        self._menu_avatar_target_y: float = 0.0
        self._menu_phase: float = 0.0

    # ----- frame plumbing -----

    def clear(self) -> None:
        self.screen.fill(theme.BACKGROUND)

    def present(self) -> None:
        self.frame_clock.tick()
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
                base = _tile_color(tile)
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
            color = _item_color(item_id)
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
        rect = pygame.Rect(sx, sy, viewport.tile_size, viewport.tile_size)
        draw_enemy_sprite(
            self.screen,
            rect,
            enemy,
            frame=self.frame_clock.frame,
            font_small=self.font_small,
            font_body=self.font_body,
        )

    def render_player(self, player: Player, viewport: Viewport) -> None:
        sx, sy = viewport.to_screen(*player.position)
        rect = pygame.Rect(sx, sy, viewport.tile_size, viewport.tile_size)
        draw_player_sprite(
            self.screen,
            rect,
            frame=self.frame_clock.frame,
            palette=self.player_palette,
            has_scan_boost=player.has_scan_boost,
        )
        draw_player_nameplate(self.screen, rect, player.name, self.font_small)

    def render_particles(self, particles: ParticleSystem, viewport: Viewport) -> None:
        for p in particles.particles:
            sx = viewport.origin_x + int(p.x * viewport.tile_size)
            sy = viewport.origin_y + int(p.y * viewport.tile_size)
            size = max(1, int(3 * p.life / max(1, p.max_life)))
            surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*p.color, p.alpha), (size, size), size)
            self.screen.blit(surface, (sx - size, sy - size))

    # ----- HUD -----

    def render_hud(
        self,
        player: Player,
        sector: int,
        world: World,
        patches: list[str] | None = None,
    ) -> None:
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

        self._blit_text(f"SCORE   : {player.score:,}", (x, y), theme.TEXT_PRIMARY, self.font_body)
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
            color = _item_color(item_id)
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

        # Combo.
        if player.combo_count > 0:
            self._blit_text(
                f"COMBO   : x{player.combo_multiplier:.2f} ({player.combo_count})",
                (x, y),
                theme.NEON_MAGENTA,
                self.font_body,
            )
            y += 22

        # Programs (Q/E/R).
        if player.programs:
            self._blit_text("PROGRAMS", (x, y), theme.NEON_CYAN, self.font_small)
            y += 16
            hotkeys = ("Q", "E", "R")
            for idx, slot in enumerate(player.programs[:3]):
                tag = hotkeys[idx]
                ready = slot.ready and player.cpu_cycles >= slot.program.cycle_cost
                color = theme.NEON_GREEN if ready else theme.TEXT_DIM
                cd = (
                    f" cd{slot.cooldown_remaining}"
                    if slot.cooldown_remaining > 0
                    else f" x{slot.charges}"
                )
                self._blit_text(
                    f"[{tag}] {slot.program.label}{cd}",
                    (x, y),
                    color,
                    self.font_small,
                )
                y += 16
            y += 4

        # Daemons.
        if player.daemons:
            self._blit_text("DAEMONS", (x, y), theme.NEON_CYAN, self.font_small)
            y += 16
            for d in player.daemons:
                self._blit_text(f". {d.label}", (x, y), theme.TEXT_DIM, self.font_small)
                y += 14
            y += 4

        # Patches.
        if patches:
            self._blit_text("PATCHES", (x, y), theme.NEON_CYAN, self.font_small)
            y += 16
            for patch_label in patches:
                self._blit_text(f"+ {patch_label}", (x, y), theme.NEON_AMBER, self.font_small)
                y += 14
            y += 4

        # Mini-map.
        self._render_minimap(world, (x, y))
        y += world.grid.height * HUD_MINIMAP_TILE + 12

        hints = [
            "[↑/↓/←/→] move / attack",
            "[space]    wait",
            "[Q/E/R]    programs",
            "[1..9]     use cache slot",
            "[?]        controls",
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
            color = _level_color(entry.level)
            tag = self.font_small.render(f"[{entry.level.value}]", True, color)
            self.screen.blit(tag, (pad_x, y))
            msg = self.font_small.render(entry.message, True, theme.TEXT_PRIMARY)
            self.screen.blit(msg, (pad_x + 64, y))
            y += line_h

    # ----- screens -----

    def render_menu(self, options: list[str], selected: int) -> None:
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # Animated background — slow scrolling grid + scanlines.
        self._render_menu_background()

        # Title block with subtle glow.
        title_surface = self.font_title.render("KERNEL QUEST", True, theme.NEON_CYAN)
        glow = self.font_title.render("KERNEL QUEST", True, theme.NEON_GREEN)
        title_rect = title_surface.get_rect(center=(cx, cy - 220))
        self.screen.blit(glow, glow.get_rect(center=(cx + 2, cy - 218)))
        self.screen.blit(title_surface, title_rect)

        subtitle = self.font_body.render("// The Memory Leak", True, theme.NEON_AMBER)
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, cy - 180)))

        # Layout the option list as a left-aligned column anchored on cx.
        first_y = cy - 80
        row_height = 34
        label_x = cx + 16
        avatar_x = cx - 200

        # Animate avatar position towards the selected row.
        self._menu_phase += 0.10
        target_y = float(first_y + selected * row_height)
        self._menu_avatar_target_y = target_y
        if self._menu_avatar_y == 0.0:
            self._menu_avatar_y = target_y
        # Critically damped slide.
        self._menu_avatar_y += (target_y - self._menu_avatar_y) * 0.22

        for i, label in enumerate(options):
            row_y = first_y + i * row_height
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            if is_sel:
                # Highlight bar behind the active row.
                bar = pygame.Rect(label_x - 12, row_y - 14, 360, 28)
                surf = pygame.Surface(bar.size, pygame.SRCALPHA)
                surf.fill((*theme.NEON_CYAN, 28))
                self.screen.blit(surf, bar.topleft)
                pygame.draw.line(
                    self.screen,
                    theme.NEON_CYAN,
                    (label_x - 12, row_y + 14),
                    (label_x + 348, row_y + 14),
                    1,
                )
            text = self.font_body.render(label, True, color)
            self.screen.blit(text, text.get_rect(midleft=(label_x, row_y)))

        # Draw the character avatar at its animated position.
        bob = math.sin(self._menu_phase) * 2.0
        self._draw_menu_avatar((avatar_x, int(self._menu_avatar_y + bob)))

        # Footer hint — translated.
        hint = self.font_small.render(
            t("menu.hint"),
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def _render_menu_background(self) -> None:
        """Slow-scrolling cyberpunk grid lines behind the menu."""
        offset = int(self._menu_phase * 6) % 40
        line_color = (*theme.GRID_LINE, 60)
        # Translucent overlay surface so the grid blends with the BG.
        layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(-40 + offset, WINDOW_HEIGHT, 40):
            pygame.draw.line(layer, line_color, (0, y), (WINDOW_WIDTH, y), 1)
        for x in range(0, WINDOW_WIDTH, 40):
            pygame.draw.line(layer, line_color, (x, 0), (x, WINDOW_HEIGHT), 1)
        self.screen.blit(layer, (0, 0))

    def _draw_menu_avatar(self, pos: tuple[int, int]) -> None:
        """Tiny pixel avatar (the protagonist 'process') used on the menu."""
        x, y = pos
        # Idle cycle: 4 frames driven by _menu_phase.
        frame = int(self._menu_phase * 4) % 4
        leg_offset = (0, 1, 0, -1)[frame]

        body = self.player_palette.core
        accent = self.player_palette.fin
        glow = self.player_palette.halo

        # Soft glow halo.
        halo = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*glow, 60), (22, 22), 20)
        self.screen.blit(halo, (x - 22, y - 22))

        # Head.
        pygame.draw.rect(self.screen, body, pygame.Rect(x - 6, y - 14, 12, 10), border_radius=2)
        # Visor.
        pygame.draw.rect(self.screen, accent, pygame.Rect(x - 5, y - 11, 10, 3))
        # Body.
        pygame.draw.rect(self.screen, body, pygame.Rect(x - 8, y - 4, 16, 10), border_radius=2)
        # Belt accent.
        pygame.draw.line(self.screen, accent, (x - 8, y + 2), (x + 8, y + 2), 1)
        # Arms.
        pygame.draw.rect(self.screen, body, pygame.Rect(x - 11, y - 3, 3, 8))
        pygame.draw.rect(self.screen, body, pygame.Rect(x + 8, y - 3, 3, 8))
        # Legs (animated).
        pygame.draw.rect(self.screen, body, pygame.Rect(x - 6, y + 6, 4, 6 + leg_offset))
        pygame.draw.rect(self.screen, body, pygame.Rect(x + 2, y + 6, 4, 6 - leg_offset))
        # Pointing arrow towards the menu row.
        tip_x = x + 18
        pygame.draw.polygon(
            self.screen,
            theme.NEON_CYAN,
            [(tip_x, y - 5), (tip_x + 8, y), (tip_x, y + 5)],
        )

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

    def render_daily_board(self, date_iso: str, rows: list[tuple[str, int, int, str, str]]) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("DAILY BOARD", True, theme.NEON_MAGENTA)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))
        sub = self.font_body.render(date_iso, True, theme.TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(cx, 100)))

        if not rows:
            empty = self.font_body.render("No daily runs yet. Be the first!", True, theme.TEXT_DIM)
            self.screen.blit(empty, empty.get_rect(center=(cx, WINDOW_HEIGHT // 2)))
        else:
            header = "{:<4}{:<18}{:>8}{:>8}  {:<14}{}".format(
                "#", "PROCESS", "SCORE", "DEPTH", "CRASH", "WHEN"
            )
            self._blit_text(header, (cx - 360, 140), theme.NEON_AMBER, self.font_body)
            for i, row in enumerate(rows):
                name, score, depth, cause, when = row
                line = "{:<4}{:<18}{:>8}{:>8}  {:<14}{}".format(
                    f"{i + 1}.", name[:16], score, depth, cause[:12], when[:16]
                )
                self._blit_text(line, (cx - 360, 172 + i * 24), theme.TEXT_PRIMARY, self.font_body)

        self._blit_back_hint()

    def render_patch_pick(self, choices: list[tuple[str, str]], selected: int) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("APPLY PATCH", True, theme.NEON_AMBER)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))
        sub = self.font_body.render(
            "Choose 1 of 3 modifiers for the new sector", True, theme.TEXT_DIM
        )
        self.screen.blit(sub, sub.get_rect(center=(cx, 100)))

        card_w = 280
        card_h = 220
        gap = 24
        total_w = card_w * len(choices) + gap * (len(choices) - 1)
        start_x = (WINDOW_WIDTH - total_w) // 2
        top_y = 160
        for idx, (label, desc) in enumerate(choices):
            rect = pygame.Rect(start_x + idx * (card_w + gap), top_y, card_w, card_h)
            color = theme.NEON_AMBER if idx == selected else theme.TEXT_DIM
            pygame.draw.rect(self.screen, color, rect, width=2, border_radius=10)
            self._blit_text(label, (rect.x + 16, rect.y + 16), theme.NEON_CYAN, self.font_body)
            # Wrap description.
            words = desc.split()
            line = ""
            line_y = rect.y + 56
            for w in words:
                test = (line + " " + w).strip()
                if self.font_small.size(test)[0] > card_w - 32:
                    self._blit_text(
                        line, (rect.x + 16, line_y), theme.TEXT_PRIMARY, self.font_small
                    )
                    line_y += 18
                    line = w
                else:
                    line = test
            if line:
                self._blit_text(line, (rect.x + 16, line_y), theme.TEXT_PRIMARY, self.font_small)

        hint = self.font_body.render("[←/→] choose      [Enter] apply", True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, top_y + card_h + 60)))

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

        title = self.font_title.render("CORE DUMPED", True, theme.NEON_MAGENTA)
        cause = self.font_body.render(
            f"init(0) terminated — signal: {player.crash_cause or 'unknown'}",
            True,
            theme.TEXT_PRIMARY,
        )
        score = self.font_body.render(
            f"Sectors cleared: {player.depth_reached}    Score: {player.score}",
            True,
            theme.TEXT_PRIMARY,
        )
        prompt = self.font_body.render(
            "init(0) needs a handle — type and press [ENTER]:", True, theme.NEON_CYAN
        )
        name_text = self.font_title.render(name_buffer + "_", True, theme.NEON_GREEN)

        self.screen.blit(title, title.get_rect(center=(cx, cy - 140)))
        self.screen.blit(cause, cause.get_rect(center=(cx, cy - 80)))
        self.screen.blit(score, score.get_rect(center=(cx, cy - 50)))
        self.screen.blit(prompt, prompt.get_rect(center=(cx, cy + 10)))
        self.screen.blit(name_text, name_text.get_rect(center=(cx, cy + 60)))

    # ----- Phase 6 overlays -----

    def render_floating_text(self, system: object, viewport: Viewport) -> None:
        from kernelquest.ui.fx import FloatingTextSystem

        if not isinstance(system, FloatingTextSystem):
            return
        for ft in system.items:
            sx = viewport.origin_x + int(ft.x * viewport.tile_size)
            sy = viewport.origin_y + int(ft.y * viewport.tile_size)
            surf = self.font_small.render(ft.text, True, ft.color)
            surf.set_alpha(ft.alpha)
            self.screen.blit(surf, surf.get_rect(center=(sx, sy)))

    def render_boss_hp_bar(self, boss: Malware) -> None:
        margin = 80
        bar_w = WINDOW_WIDTH - margin * 2
        bar_h = 14
        x = margin
        y = 10
        bg = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bg.fill((20, 0, 0, 220))
        self.screen.blit(bg, (x, y))
        ratio = max(0.0, min(1.0, boss.hp / max(1, boss.max_hp)))
        fill_w = int(bar_w * ratio)
        pygame.draw.rect(self.screen, (220, 30, 60), pygame.Rect(x, y, fill_w, bar_h))
        pygame.draw.rect(self.screen, (255, 80, 100), pygame.Rect(x, y, bar_w, bar_h), width=1)
        label = self.font_small.render(
            f"!! BOSS: {boss.crash_label}  {boss.hp}/{boss.max_hp} !!",
            True,
            (255, 220, 220),
        )
        self.screen.blit(label, label.get_rect(center=(WINDOW_WIDTH // 2, y + bar_h + 12)))

    def render_boss_banner(self, name: str, alpha_factor: float) -> None:
        alpha = int(255 * max(0.0, min(1.0, alpha_factor)))
        if alpha <= 0:
            return
        text = self.font_title.render(f"!! {name} LOADED !!", True, (255, 60, 80))
        text.set_alpha(alpha)
        self.screen.blit(text, text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))
        sub = self.font_body.render("EXIT LOCKED — terminate the process", True, (255, 200, 200))
        sub.set_alpha(alpha)
        self.screen.blit(sub, sub.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))

    def render_glitch_overlay(self, intensity: float) -> None:
        intensity = max(0.0, min(1.0, intensity))
        if intensity <= 0.0:
            return
        rng = random.Random()
        slices = int(8 + 24 * intensity)
        for _ in range(slices):
            y = rng.randint(0, WINDOW_HEIGHT - 8)
            h = rng.randint(2, 8)
            offset = rng.randint(-int(20 * intensity), int(20 * intensity))
            try:
                rect = pygame.Rect(0, y, WINDOW_WIDTH, h)
                strip = self.screen.subsurface(rect).copy()
                self.screen.blit(strip, (offset, y))
            except (ValueError, pygame.error):  # pragma: no cover
                pass
        # Faint red tint.
        tint = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        tint.fill((255, 0, 30, int(40 * intensity)))
        self.screen.blit(tint, (0, 0))

    def render_scanlines(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(0, WINDOW_HEIGHT, 3):
            pygame.draw.line(overlay, (0, 0, 0, 50), (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(overlay, (0, 0))

    def render_help_overlay(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("CONTROLS", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 80)))
        rows = [
            "[Arrow keys / WASD] move or attack",
            "[Space]             wait one turn",
            "[Q] [E] [R]         fire program slot 1/2/3",
            "[1..9]              use cache item",
            "[?] / [F1]          toggle this overlay",
            "[F11]               toggle fullscreen",
            "[M]                 toggle mute",
            "[Esc]               quit run",
        ]
        y = 160
        for r in rows:
            surf = self.font_body.render(r, True, theme.TEXT_PRIMARY)
            self.screen.blit(surf, surf.get_rect(center=(cx, y)))
            y += 30
        hint = self.font_small.render("Press [?] to dismiss.", True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 50)))

    def render_quit_confirm(self) -> None:
        """Modal overlay asking the player to confirm exit."""
        from kernelquest.ui.i18n import t

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        box_w, box_h = 560, 200
        box = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
        glass = pygame.Surface(box.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 235))
        self.screen.blit(glass, box.topleft)
        pygame.draw.rect(self.screen, theme.NEON_MAGENTA, box, width=2, border_radius=10)

        title = self.font_body.render(t("quit_confirm.title"), True, theme.NEON_MAGENTA)
        self.screen.blit(title, title.get_rect(center=(cx, box.y + 36)))
        msg = self.font_body.render(t("quit_confirm.message"), True, theme.TEXT_PRIMARY)
        self.screen.blit(msg, msg.get_rect(center=(cx, box.y + 84)))
        hint = self.font_small.render(t("quit_confirm.hint"), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, box.y + box_h - 36)))

    def render_tutorial(self, page: int) -> None:
        """Render a single tutorial page (0-indexed) with actual in-game iconography.

        Each of the 7 pages draws real sprites, tile colors, item glyphs and a
        mock HUD so a brand-new player can recognise them at a glance once the
        run starts.
        """
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        page = max(0, min(TUTORIAL_PAGE_COUNT - 1, page))

        title_surf = self.font_title.render(t("tutorial.title"), True, theme.NEON_CYAN)
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, 50)))
        section = self.font_body.render(t(_TUTORIAL_PAGE_TITLE_KEYS[page]), True, theme.NEON_AMBER)
        self.screen.blit(section, section.get_rect(center=(cx, 100)))

        body_top = 140
        renderers = (
            self._tutorial_overview,
            self._tutorial_character,
            self._tutorial_enemies,
            self._tutorial_map,
            self._tutorial_items,
            self._tutorial_score_meta,
            self._tutorial_controls,
        )
        renderers[page](body_top)

        page_label = self.font_small.render(
            t("tutorial.page_label", page=page + 1, total=TUTORIAL_PAGE_COUNT),
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(page_label, page_label.get_rect(center=(cx, WINDOW_HEIGHT - 64)))

        hint = self.font_small.render(t("tutorial.hint"), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    # ----- tutorial page helpers -----

    def _tutorial_overview(self, top: int) -> None:
        """Mock HUD with callouts: RAM, CYCLES, DAMAGE, SCORE, CACHE, MINIMAP."""
        cx = WINDOW_WIDTH // 2
        from kernelquest.ui.i18n import t

        intro = t("tutorial.overview.intro")
        self._blit_text(intro, (cx - 460, top), theme.TEXT_PRIMARY, self.font_body)
        self._blit_text(
            t("tutorial.overview.sub"),
            (cx - 460, top + 24),
            theme.TEXT_DIM,
            self.font_body,
        )

        # Mock HUD panel.
        panel_w = 280
        panel_h = 360
        panel_x = cx - 460
        panel_y = top + 70
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        glass = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 215))
        self.screen.blit(glass, panel_rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, panel_rect, width=1, border_radius=8)

        x = panel_x + 16
        y = panel_y + 16
        self._blit_text("KERNEL QUEST", (x, y), theme.NEON_CYAN, self.font_body)
        y += 26
        self._blit_text(
            t("tutorial.overview.sector_ex"), (x, y), theme.TEXT_PRIMARY, self.font_body
        )
        y += 22
        self._blit_text(
            t("tutorial.overview.process_ex"), (x, y), theme.TEXT_PRIMARY, self.font_body
        )
        y += 28
        ram_y = y
        self._blit_text("RAM     : 75/100", (x, y), theme.NEON_GREEN, self.font_body)
        y += 22
        self._render_bar((x, y), 232, 10, 0.75, theme.NEON_GREEN)
        y += 22
        cycles_y = y
        self._blit_text("CYCLES  : 4/5", (x, y), theme.NEON_AMBER, self.font_body)
        y += 22
        wave_rect = pygame.Rect(x, y, HUD_CPU_WAVE_WIDTH, HUD_CPU_WAVE_HEIGHT)
        pygame.draw.rect(self.screen, theme.PANEL_BG, wave_rect, border_radius=3)
        pygame.draw.rect(self.screen, theme.GRID_LINE, wave_rect, width=1, border_radius=3)
        mid = wave_rect.y + HUD_CPU_WAVE_HEIGHT // 2
        prev_pt: tuple[int, int] | None = None
        for px in range(wave_rect.width):
            theta = px * 0.22
            py = mid + int((HUD_CPU_WAVE_HEIGHT / 2 - 4) * 0.8 * math.sin(theta))
            point = (wave_rect.x + px, py)
            if prev_pt is not None:
                pygame.draw.line(self.screen, theme.NEON_AMBER, prev_pt, point, 1)
            prev_pt = point
        y += HUD_CPU_WAVE_HEIGHT + 6
        damage_y = y
        self._blit_text(
            t("tutorial.overview.damage_ex"), (x, y), theme.NEON_MAGENTA, self.font_body
        )
        y += 22
        score_y = y
        self._blit_text(t("tutorial.overview.score_ex"), (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 24
        cache_y = y
        self._blit_text(t("tutorial.overview.cache_ex"), (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 22
        for i in range(8):
            slot_rect = pygame.Rect(x + i * 28, y, 24, 24)
            if i == 0:
                pygame.draw.rect(self.screen, theme.ITEM_GC, slot_rect, border_radius=4)
                lab = self.font_small.render("G", True, theme.BACKGROUND)
                self.screen.blit(lab, lab.get_rect(center=slot_rect.center))
            elif i == 1:
                pygame.draw.rect(self.screen, theme.ITEM_OPTIMIZATION, slot_rect, border_radius=4)
                lab = self.font_small.render("O", True, theme.BACKGROUND)
                self.screen.blit(lab, lab.get_rect(center=slot_rect.center))
            else:
                pygame.draw.rect(self.screen, theme.PANEL_BG, slot_rect, border_radius=4)
                pygame.draw.rect(self.screen, theme.GRID_LINE, slot_rect, width=1, border_radius=4)
            num = self.font_small.render(f"{i + 1}", True, theme.TEXT_DIM)
            self.screen.blit(num, (slot_rect.x, slot_rect.bottom + 2))

        callouts = [
            (ram_y + 10, t("tutorial.overview.callout_ram"), theme.NEON_GREEN),
            (cycles_y + 10, t("tutorial.overview.callout_cycles"), theme.NEON_AMBER),
            (damage_y + 10, t("tutorial.overview.callout_damage"), theme.NEON_MAGENTA),
            (score_y + 10, t("tutorial.overview.callout_score"), theme.TEXT_PRIMARY),
            (cache_y + 26, t("tutorial.overview.callout_cache"), theme.NEON_CYAN),
        ]
        text_x = panel_x + panel_w + 40
        line_start_x = panel_x + panel_w + 4
        for cy_, text, color in callouts:
            pygame.draw.line(self.screen, color, (line_start_x, cy_), (text_x - 10, cy_), 1)
            self._blit_text(text, (text_x, cy_ - 10), color, self.font_body)

        note_y = panel_y + panel_h + 16
        self._blit_text(
            t("tutorial.overview.note_minimap"), (panel_x, note_y), theme.TEXT_DIM, self.font_body
        )
        self._blit_text(
            t("tutorial.overview.note_console"),
            (panel_x, note_y + 22),
            theme.TEXT_DIM,
            self.font_body,
        )

    def _tutorial_character(self, top: int) -> None:
        """Player avatar + RAM/CYCLES bars with explanations."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        cell = 64
        ox = cx - 380
        oy = top + 20
        cell_rect = pygame.Rect(ox, oy, cell, cell)
        pygame.draw.rect(self.screen, theme.TILE_SYSTEM_DATA, cell_rect)
        pygame.draw.rect(self.screen, theme.GRID_LINE, cell_rect, 1)
        center = (ox + cell // 2, oy + cell // 2)
        radius = cell // 2 - 6
        pygame.draw.circle(self.screen, theme.PLAYER_COLOR, center, radius)
        pygame.draw.circle(self.screen, theme.NEON_CYAN, center, radius, 2)
        self._blit_text(
            t("tutorial.character.avatar_label"),
            (ox, oy + cell + 8),
            theme.NEON_GREEN,
            self.font_body,
        )
        self._blit_text(
            t("tutorial.character.avatar_sub"),
            (ox, oy + cell + 32),
            theme.TEXT_DIM,
            self.font_small,
        )

        text_x = ox + 200
        ty = oy
        line_h = self.font_body.get_height() + 6
        stat_rows: tuple[tuple[tuple[int, int, int], str], ...] = (
            (theme.NEON_GREEN, t("tutorial.character.ram1")),
            (theme.TEXT_PRIMARY, t("tutorial.character.ram2")),
            (theme.NEON_AMBER, t("tutorial.character.cycles1")),
            (theme.TEXT_PRIMARY, t("tutorial.character.cycles2")),
            (theme.TEXT_PRIMARY, t("tutorial.character.cycles3")),
            (theme.NEON_CYAN, t("tutorial.character.cache1")),
            (theme.TEXT_PRIMARY, t("tutorial.character.cache2")),
            (theme.NEON_MAGENTA, t("tutorial.character.damage1")),
        )
        for color, text in stat_rows:
            self._blit_text(text, (text_x, ty), color, self.font_body)
            ty += line_h

        demo_y = max(ty + 24, oy + cell + 64)
        self._blit_text(
            t("tutorial.character.bar_label"), (ox, demo_y), theme.TEXT_PRIMARY, self.font_body
        )
        demo_y += 24
        for ratio, color, label_key in (
            (0.9, theme.NEON_GREEN, "tutorial.character.bar_high"),
            (0.4, theme.NEON_AMBER, "tutorial.character.bar_mid"),
            (0.15, (255, 110, 110), "tutorial.character.bar_low"),
        ):
            self._render_bar((ox, demo_y), 232, 12, ratio, color)
            self._blit_text(t(label_key), (ox + 244, demo_y - 2), color, self.font_body)
            demo_y += 22

        self._blit_text(
            t("tutorial.character.bar_tip"), (ox, demo_y + 8), theme.NEON_AMBER, self.font_body
        )

    def _tutorial_enemies(self, top: int) -> None:
        """Three rows: real enemy sprite + name + behaviour description."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        cell = 64
        ox = cx - 460
        enemy_rows: tuple[tuple[type[Malware], int, int, str, str, str], ...] = (
            (
                SyntaxError_,
                8,
                8,
                "tutorial.enemy.syntax_name",
                "tutorial.enemy.syntax_header",
                "tutorial.enemy.syntax_desc",
            ),
            (
                LogicBomb,
                12,
                10,
                "tutorial.enemy.logic_name",
                "tutorial.enemy.logic_header",
                "tutorial.enemy.logic_desc",
            ),
            (
                KernelPanic,
                60,
                42,
                "tutorial.enemy.kernel_name",
                "tutorial.enemy.kernel_header",
                "tutorial.enemy.kernel_desc",
            ),
        )

        y = top + 10
        line_h = self.font_body.get_height() + 4
        for cls, max_hp, current_hp, name_key, header_key, desc_key in enemy_rows:
            self._tutorial_draw_enemy(cls, max_hp, current_hp, ox, y, cell)
            color_map: dict[type[Malware], tuple[int, int, int]] = {
                SyntaxError_: theme.ENEMY_SYNTAX_ERROR,
                LogicBomb: theme.ENEMY_LOGIC_BOMB,
                KernelPanic: theme.ENEMY_KERNEL_PANIC,
            }
            name_color = color_map[cls]
            tx = ox + cell + 24
            self._blit_text(t(name_key), (tx, y), name_color, self.font_body)
            self._blit_text(t(header_key), (tx, y + 22), theme.TEXT_DIM, self.font_small)
            for i, line in enumerate(t(desc_key).split("\n")):
                self._blit_text(line, (tx, y + 44 + i * line_h), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 60

        self._blit_text(t("tutorial.enemy.tip"), (ox, y + 8), theme.NEON_CYAN, self.font_body)

    def _tutorial_draw_enemy(
        self, cls: type[Malware], max_hp: int, hp: int, ox: int, oy: int, cell: int
    ) -> None:
        """Render a single enemy preview (matches in-game ``_render_enemy``)."""
        color_map: dict[type[Malware], tuple[int, int, int]] = {
            SyntaxError_: theme.ENEMY_SYNTAX_ERROR,
            LogicBomb: theme.ENEMY_LOGIC_BOMB,
            KernelPanic: theme.ENEMY_KERNEL_PANIC,
        }
        color = color_map.get(cls, theme.NEON_AMBER)
        bg = pygame.Rect(ox, oy, cell, cell)
        pygame.draw.rect(self.screen, theme.TILE_SYSTEM_DATA, bg)
        pygame.draw.rect(self.screen, theme.GRID_LINE, bg, 1)
        rect = pygame.Rect(ox + 8, oy + 8, cell - 16, cell - 16)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, theme.BACKGROUND, rect, width=1, border_radius=6)

        pip_count = max(1, min(8, max_hp // 4))
        pip_w = (cell - 16) // pip_count
        filled = int(round(pip_count * (hp / max(1, max_hp))))
        for i in range(pip_count):
            pip_color = color if i < filled else theme.PANEL_BG
            pip_rect = pygame.Rect(ox + 8 + i * pip_w, oy + 4, max(2, pip_w - 1), 4)
            pygame.draw.rect(self.screen, pip_color, pip_rect)

        hp_text = f"{hp}/{max_hp}"
        hp_surface = self.font_small.render(hp_text, True, theme.TEXT_PRIMARY)
        shadow = self.font_small.render(hp_text, True, theme.BACKGROUND)
        hp_rect = hp_surface.get_rect(center=(ox + cell // 2, oy + cell // 2))
        self.screen.blit(shadow, hp_rect.move(1, 1))
        self.screen.blit(hp_surface, hp_rect)

    def _tutorial_map(self, top: int) -> None:
        """Real tile palette + walkability rules + player-on-tile demo."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        cell = 56
        ox = cx - 460
        tile_rows: tuple[tuple[TileType, str, str, tuple[int, int, int]], ...] = (
            (
                TileType.SYSTEM_DATA,
                "tutorial.map.system_data_name",
                "tutorial.map.system_data_desc",
                theme.NEON_GREEN,
            ),
            (TileType.EMPTY, "tutorial.map.empty_name", "tutorial.map.empty_desc", theme.TEXT_DIM),
            (
                TileType.BAD_SECTOR,
                "tutorial.map.bad_sector_name",
                "tutorial.map.bad_sector_desc",
                (255, 110, 110),
            ),
            (TileType.EXIT, "tutorial.map.exit_name", "tutorial.map.exit_desc", theme.NEON_MAGENTA),
        )
        y = top + 10
        for tile, name_key, desc_key, name_color in tile_rows:
            tile_rect = pygame.Rect(ox, y, cell, cell)
            pygame.draw.rect(self.screen, _TILE_COLORS[tile], tile_rect)
            pygame.draw.rect(self.screen, theme.GRID_LINE, tile_rect, 1)
            tx = ox + cell + 24
            self._blit_text(t(name_key), (tx, y + 4), name_color, self.font_body)
            self._blit_text(t(desc_key), (tx, y + 28), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 16

        demo_x = ox
        demo_y = y + 10
        self._blit_text(
            t("tutorial.map.demo_label"), (demo_x, demo_y), theme.NEON_AMBER, self.font_body
        )
        demo_y += 28
        for i, tile in enumerate(
            (TileType.SYSTEM_DATA, TileType.SYSTEM_DATA, TileType.EXIT, TileType.SYSTEM_DATA)
        ):
            r = pygame.Rect(demo_x + i * (cell + 4), demo_y, cell, cell)
            pygame.draw.rect(self.screen, _TILE_COLORS[tile], r)
            pygame.draw.rect(self.screen, theme.GRID_LINE, r, 1)
            if i == 2:
                pygame.draw.circle(self.screen, theme.PLAYER_COLOR, r.center, cell // 2 - 8)
                pygame.draw.circle(self.screen, theme.NEON_CYAN, r.center, cell // 2 - 8, 2)

        note_y = demo_y + cell + 16
        self._blit_text(t("tutorial.map.fov_note1"), (ox, note_y), theme.TEXT_DIM, self.font_body)
        self._blit_text(
            t("tutorial.map.fov_note2"), (ox, note_y + 22), theme.TEXT_DIM, self.font_body
        )

    def _tutorial_items(self, top: int) -> None:
        """Item glyphs as drawn on the floor + cache strip + usage explanation."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        cell = 56

        item_rows: tuple[tuple[str, str, str, str, tuple[int, int, int]], ...] = (
            ("gc", "G", "tutorial.items.gc_name", "tutorial.items.gc_desc", theme.ITEM_GC),
            (
                "opt",
                "O",
                "tutorial.items.opt_name",
                "tutorial.items.opt_desc",
                theme.ITEM_OPTIMIZATION,
            ),
            (
                "scan",
                "S",
                "tutorial.items.scan_name",
                "tutorial.items.scan_desc",
                theme.ITEM_SCAN_BOOST,
            ),
        )
        y = top + 10
        for _id, glyph, name_key, desc_key, color in item_rows:
            tile_rect = pygame.Rect(ox, y, cell, cell)
            pygame.draw.rect(self.screen, theme.TILE_SYSTEM_DATA, tile_rect)
            pygame.draw.rect(self.screen, theme.GRID_LINE, tile_rect, 1)
            pygame.draw.circle(self.screen, color, tile_rect.center, cell // 4)
            label_surf = self.font_small.render(glyph, True, theme.BACKGROUND)
            self.screen.blit(label_surf, label_surf.get_rect(center=tile_rect.center))
            tx = ox + cell + 24
            self._blit_text(t(name_key), (tx, y + 4), color, self.font_body)
            self._blit_text(t(desc_key), (tx, y + 28), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 12

        strip_y = y + 16
        self._blit_text(
            t("tutorial.items.cache_strip_label"), (ox, strip_y), theme.NEON_CYAN, self.font_body
        )
        strip_y += 28
        slot = 36
        for i in range(8):
            r = pygame.Rect(ox + i * (slot + 6), strip_y, slot, slot)
            if i == 0:
                pygame.draw.rect(self.screen, theme.ITEM_GC, r, border_radius=6)
                lab = self.font_small.render("G", True, theme.BACKGROUND)
                self.screen.blit(lab, lab.get_rect(center=r.center))
            elif i == 1:
                pygame.draw.rect(self.screen, theme.ITEM_OPTIMIZATION, r, border_radius=6)
                lab = self.font_small.render("O", True, theme.BACKGROUND)
                self.screen.blit(lab, lab.get_rect(center=r.center))
            elif i == 2:
                pygame.draw.rect(self.screen, theme.ITEM_SCAN_BOOST, r, border_radius=6)
                lab = self.font_small.render("S", True, theme.BACKGROUND)
                self.screen.blit(lab, lab.get_rect(center=r.center))
            else:
                pygame.draw.rect(self.screen, theme.PANEL_BG, r, border_radius=6)
                pygame.draw.rect(self.screen, theme.GRID_LINE, r, width=1, border_radius=6)
            num = self.font_small.render(f"{i + 1}", True, theme.TEXT_DIM)
            self.screen.blit(num, (r.x, r.bottom + 2))

        notes_y = strip_y + slot + 28
        self._blit_text(
            t("tutorial.items.note1"), (ox, notes_y), theme.TEXT_PRIMARY, self.font_body
        )
        self._blit_text(
            t("tutorial.items.note2"), (ox, notes_y + 22), theme.TEXT_PRIMARY, self.font_body
        )
        self._blit_text(
            t("tutorial.items.note3"), (ox, notes_y + 44), theme.TEXT_DIM, self.font_body
        )

    def _tutorial_score_meta(self, top: int) -> None:
        """Score table + bits formula + shop list."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        line_h = self.font_body.get_height() + 6

        self._blit_text(
            t("tutorial.score.section_title"), (ox, top), theme.NEON_AMBER, self.font_body
        )
        score_rows = (
            "tutorial.score.move",
            "tutorial.score.syntax",
            "tutorial.score.logic",
            "tutorial.score.kernel",
            "tutorial.score.descend",
        )
        y = top + 30
        for key in score_rows:
            self._blit_text(t(key), (ox, y), theme.TEXT_PRIMARY, self.font_body)
            y += line_h
        y += 8
        self._blit_text(t("tutorial.score.persist_note"), (ox, y), theme.NEON_CYAN, self.font_body)

        meta_y = y + line_h * 2
        self._blit_text(
            t("tutorial.meta.section_title"), (ox, meta_y), theme.NEON_GREEN, self.font_body
        )
        meta_y += 28
        self._blit_text(
            t("tutorial.meta.bits_intro"), (ox, meta_y), theme.TEXT_PRIMARY, self.font_body
        )
        meta_y += line_h
        self._blit_text(
            t("tutorial.meta.bits_formula"), (ox, meta_y), theme.NEON_AMBER, self.font_body
        )
        meta_y += line_h + 4
        self._blit_text(
            t("tutorial.meta.shop_intro"), (ox, meta_y), theme.TEXT_PRIMARY, self.font_body
        )
        meta_y += line_h
        upgrade_rows = (
            ("tutorial.meta.upgrade_ram", theme.NEON_GREEN),
            ("tutorial.meta.upgrade_cycle", theme.NEON_AMBER),
            ("tutorial.meta.upgrade_scan", theme.ITEM_SCAN_BOOST),
            ("tutorial.meta.upgrade_damage", theme.NEON_MAGENTA),
            ("tutorial.meta.upgrade_cache", theme.NEON_CYAN),
        )
        for key, color in upgrade_rows:
            self._blit_text(t(key), (ox, meta_y), color, self.font_body)
            meta_y += line_h
        self._blit_text(
            t("tutorial.meta.persist_note"), (ox, meta_y + 6), theme.TEXT_DIM, self.font_body
        )

    def _tutorial_controls(self, top: int) -> None:
        """Controls reference and tactical tips."""
        from kernelquest.ui.i18n import t

        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        line_h = self.font_body.get_height() + 8

        self._blit_text(
            t("tutorial.controls.section_title"), (ox, top), theme.NEON_AMBER, self.font_body
        )
        control_rows = (
            ("tutorial.controls.move_keys", "tutorial.controls.move_action"),
            ("tutorial.controls.space_key", "tutorial.controls.space_action"),
            ("tutorial.controls.slot_keys", "tutorial.controls.slot_action"),
            ("tutorial.controls.esc_key", "tutorial.controls.esc_action"),
        )
        y = top + 32
        for key_key, action_key in control_rows:
            self._blit_text(
                f"{t(key_key):<28}{t(action_key)}",
                (ox, y),
                theme.TEXT_PRIMARY,
                self.font_body,
            )
            y += line_h

        y += 8
        self._blit_text(
            t("tutorial.controls.tactics_title"), (ox, y), theme.NEON_CYAN, self.font_body
        )
        y += 28
        tactic_keys = (
            "tutorial.controls.tactic1",
            "tutorial.controls.tactic2",
            "tutorial.controls.tactic3",
            "tutorial.controls.tactic4",
            "tutorial.controls.tactic5",
            "tutorial.controls.tactic6",
        )
        for tac_key in tactic_keys:
            self._blit_text(t(tac_key), (ox, y), theme.TEXT_PRIMARY, self.font_body)
            y += line_h

        self._blit_text(t("tutorial.controls.cta"), (ox, y + 8), theme.NEON_GREEN, self.font_body)

    # ---------------- Phase 10 — Tutorial Range UI ----------------

    def render_range_lesson_panel(
        self,
        lesson: object | None,
        lesson_index: int,
        total_lessons: int,
        progress: object,
        completed: bool,
    ) -> None:
        """Render the curriculum panel at the top of the Range scene."""
        # ``lesson`` is a Lesson | None; ``progress`` a LessonProgress.
        panel_w = 760
        panel_h = 96
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = 8
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((10, 14, 22, 220))
        pygame.draw.rect(bg, theme.NEON_CYAN, bg.get_rect(), 2)
        self.screen.blit(bg, (panel_x, panel_y))

        if completed and lesson is None:
            title = self.font_title.render(
                "/dev/sandbox — CURRICULUM COMPLETE",
                True,
                theme.NEON_GREEN,
            )
            self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 30)))
            sub = self.font_small.render(
                "[~] Polygon free-play   [Esc] return to menu",
                True,
                theme.TEXT_DIM,
            )
            self.screen.blit(sub, sub.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 64)))
            return
        if lesson is None:
            return

        # Type-narrow at runtime to avoid a hard import cycle.
        title_text = getattr(lesson, "title", "Lesson")
        body_text = getattr(lesson, "body", "")
        hint_text = getattr(lesson, "hint", "")
        goal_field = getattr(lesson, "goal_field", "")
        goal_target = int(getattr(lesson, "goal_target", 1))
        if goal_field == "programs_fired":
            current = sum(getattr(progress, "programs_fired", {}).values())
        else:
            current = int(getattr(progress, goal_field, 0))

        head = self.font_title.render(title_text, True, theme.NEON_CYAN)
        self.screen.blit(head, (panel_x + 12, panel_y + 6))
        idx = self.font_small.render(f"{lesson_index + 1}/{total_lessons}", True, theme.TEXT_DIM)
        self.screen.blit(idx, (panel_x + panel_w - idx.get_width() - 12, panel_y + 12))
        body = self.font_small.render(body_text, True, theme.TEXT_PRIMARY)
        self.screen.blit(body, (panel_x + 12, panel_y + 36))
        hint = self.font_small.render(
            f">> {hint_text}  ({min(current, goal_target)}/{goal_target})",
            True,
            theme.NEON_AMBER,
        )
        self.screen.blit(hint, (panel_x + 12, panel_y + 66))

    def render_polygon_overlay(
        self,
        kind: str,
        items: list[tuple[str, str]],
        selected: int,
        *,
        god_mode: bool,
        infinite_cycles: bool,
        full_fov: bool,
    ) -> None:
        """Render the free-play sandbox toolbar (the Polygon)."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        cx = WINDOW_WIDTH // 2
        title = self.font_title.render(f"POLYGON — {kind.upper()}", True, theme.NEON_MAGENTA)
        self.screen.blit(title, title.get_rect(center=(cx, 80)))

        flags_line = (
            f"[F1] god={god_mode}   [F2] inf_cycles={infinite_cycles}   "
            f"[F3] full_fov={full_fov}"
        )
        flags_surf = self.font_small.render(flags_line, True, theme.TEXT_DIM)
        self.screen.blit(flags_surf, flags_surf.get_rect(center=(cx, 110)))

        kinds_hint = self.font_small.render(
            "[A/D] kind   [W/S] select   [Enter] spawn/grant   [~/Esc] close",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(kinds_hint, kinds_hint.get_rect(center=(cx, 132)))

        list_x = 120
        list_y = 170
        max_rows = 16
        start = max(0, min(selected - max_rows // 2, len(items) - max_rows))
        for i, (label, desc) in enumerate(items[start : start + max_rows]):
            real_idx = start + i
            color = theme.NEON_AMBER if real_idx == selected else theme.TEXT_PRIMARY
            line = f"{'> ' if real_idx == selected else '  '}{label}  —  {desc}"
            surf = self.font_small.render(line[:130], True, color)
            self.screen.blit(surf, (list_x, list_y + i * 22))

    # ----------------------------------------------------------------

    def render_howtoplay(self, lines: list[str], scroll: int) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("HOW TO PLAY", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))
        x = 80
        y = 120
        line_h = self.font_body.get_height() + 4
        max_lines = (WINDOW_HEIGHT - 200) // line_h
        slice_ = lines[scroll : scroll + max_lines]
        for ln in slice_:
            color = theme.TEXT_PRIMARY
            if ln.startswith("# "):
                color = theme.NEON_CYAN
                ln = ln[2:]
            elif ln.startswith("## "):
                color = theme.NEON_AMBER
                ln = ln[3:]
            elif ln.startswith("- "):
                color = theme.TEXT_DIM
            surf = self.font_body.render(ln[:120], True, color)
            self.screen.blit(surf, (x, y))
            y += line_h
        hint = self.font_small.render(
            "[↑/↓] scroll   [pgup/pgdn] page   [esc] back",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    # ----- Phase 7 narrative screens -----

    def render_cinematic(self, player: CinematicPlayer) -> None:
        """Render the active intro/ending cutscene frame."""
        render_cinematic(
            self.screen,
            player,
            font_title=self.font_title,
            font_body=self.font_body,
            font_small=self.font_small,
        )

    def render_codex(
        self,
        rows: list[tuple[str, str, bool]],
        selected: int,
        body: str | None,
    ) -> None:
        """Codex screen — left list of entries, right pane for selected body.

        Each row is ``(key, title, unlocked)``; locked rows show ``???``.
        """
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("CODEX", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        list_x = 80
        list_top = 130
        list_w = 360
        for i, (_key, label, unlocked) in enumerate(rows):
            is_sel = i == selected
            if not unlocked:
                color = theme.TEXT_DIM
                text = "???"
            else:
                color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
                text = label
            prefix = "▶ " if is_sel else "  "
            self._blit_text(
                f"{prefix}{text[:42]}", (list_x, list_top + i * 26), color, self.font_body
            )

        body_x = list_x + list_w + 32
        body_w = WINDOW_WIDTH - body_x - 80
        pane_rect = pygame.Rect(
            body_x - 16, list_top - 16, body_w + 32, WINDOW_HEIGHT - list_top - 80
        )
        glass = pygame.Surface(pane_rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 200))
        self.screen.blit(glass, pane_rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, pane_rect, width=1, border_radius=8)

        if body:
            y = pane_rect.y + 20
            for paragraph in body.split("\n"):
                # Word-wrap each paragraph.
                words = paragraph.split(" ") if paragraph else [""]
                line = ""
                for w in words:
                    candidate = (line + " " + w).strip() if line else w
                    if self.font_body.size(candidate)[0] > body_w - 16:
                        self._blit_text(line, (body_x, y), theme.TEXT_PRIMARY, self.font_body)
                        y += 24
                        line = w
                    else:
                        line = candidate
                if line:
                    self._blit_text(line, (body_x, y), theme.TEXT_PRIMARY, self.font_body)
                    y += 24
                y += 8
        else:
            self._blit_text(
                "Locked. Discover this entry by playing.",
                (body_x, pane_rect.y + 20),
                theme.TEXT_DIM,
                self.font_body,
            )

        hint = self.font_small.render(
            "[↑/↓] navigate    [esc] back",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_stack_trace(self, lines: list[tuple[str, str]], sector: int) -> None:
        """Between-sector "stack trace" interstitial (7.4)."""
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render(f"-- stack trace -- 0x{sector:02X}", True, theme.NEON_AMBER)
        self.screen.blit(title, title.get_rect(center=(cx, 100)))

        y = WINDOW_HEIGHT // 2 - len(lines) * 18
        for speaker, body in lines:
            speaker_color = {
                "[KERNEL]": theme.NEON_CYAN,
                "[init]": theme.NEON_GREEN,
                "[THE_LEAK]": (255, 80, 200),
                "[CRON]": theme.NEON_AMBER,
                "[VENDOR]": theme.TEXT_PRIMARY,
            }.get(speaker, theme.TEXT_PRIMARY)
            speaker_surf = self.font_body.render(speaker, True, speaker_color)
            body_surf = self.font_body.render(body, True, theme.TEXT_PRIMARY)
            total_w = speaker_surf.get_width() + 12 + body_surf.get_width()
            x0 = cx - total_w // 2
            self.screen.blit(speaker_surf, (x0, y))
            self.screen.blit(body_surf, (x0 + speaker_surf.get_width() + 12, y))
            y += 32

        hint = self.font_small.render(
            "[ENTER] continue",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 80)))

    # ----- helpers -----

    def render_bestiary(
        self,
        rows: list[tuple[str, str, int, int, int, str, str, str]],
        selected: int,
    ) -> None:
        """Phase 8 — Bestiary screen.

        Each row: ``(key, label, intel_level, kills, dmg, archetype, weakness, lore)``.
        Higher intel tiers reveal more fields; tier 0 shows ``???``.
        """
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("BESTIARY", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        list_x = 80
        list_top = 130
        list_w = 360
        for i, (_key, label, tier, _k, _d, _a, _w, _lore) in enumerate(rows):
            is_sel = i == selected
            if tier == 0:
                color = theme.TEXT_DIM
                text = "???  (lvl 0)"
            else:
                color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
                text = f"{label}  (lvl {tier})"
            prefix = "▶ " if is_sel else "  "
            self._blit_text(
                f"{prefix}{text[:42]}", (list_x, list_top + i * 26), color, self.font_body
            )

        body_x = list_x + list_w + 32
        body_w = WINDOW_WIDTH - body_x - 80
        pane_rect = pygame.Rect(
            body_x - 16, list_top - 16, body_w + 32, WINDOW_HEIGHT - list_top - 80
        )
        glass = pygame.Surface(pane_rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 200))
        self.screen.blit(glass, pane_rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, pane_rect, width=1, border_radius=8)

        if rows:
            row = rows[selected]
            _key, label, tier, kills, dmg, archetype, weakness, lore = row
            y = pane_rect.y + 20
            if tier == 0:
                self._blit_text(
                    "No intel yet — engage to reveal.",
                    (body_x, y),
                    theme.TEXT_DIM,
                    self.font_body,
                )
            else:
                self._blit_text(label, (body_x, y), theme.NEON_AMBER, self.font_title)
                y += 38
                self._blit_text(
                    f"Archetype: {archetype}",
                    (body_x, y),
                    theme.TEXT_PRIMARY,
                    self.font_body,
                )
                y += 26
                self._blit_text(
                    f"Kills: {kills}    Damage dealt: {dmg}",
                    (body_x, y),
                    theme.TEXT_PRIMARY,
                    self.font_body,
                )
                y += 26
                if tier >= 2:
                    self._blit_text(
                        f"Weakness: {weakness}",
                        (body_x, y),
                        theme.NEON_GREEN,
                        self.font_body,
                    )
                    y += 26
                if tier >= 3:
                    self._blit_text(
                        lore[: body_w // 8],
                        (body_x, y),
                        theme.TEXT_DIM,
                        self.font_small,
                    )

        hint = self.font_small.render(
            "[↑/↓] navigate    [esc] back",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_inspect_overlay(
        self,
        screen_pos: tuple[int, int],
        label: str,
        tier: int,
        kills: int,
        damage_dealt: int,
        weakness: str,
        affixes: list[str],
    ) -> None:
        """Floating intel popover anchored at a tile (Inspect mode)."""
        x, y = screen_pos
        lines: list[tuple[str, tuple[int, int, int]]] = []
        if tier == 0:
            lines.append(("??? (no intel)", theme.TEXT_DIM))
        else:
            lines.append((f"{label} (lvl {tier})", theme.NEON_AMBER))
            lines.append((f"kills: {kills}  dmg: {damage_dealt}", theme.TEXT_PRIMARY))
            if tier >= 2:
                lines.append((f"weak: {weakness}", theme.NEON_GREEN))
            if affixes:
                lines.append(("affix: " + ", ".join(affixes), theme.NEON_MAGENTA))
        w = 240
        h = 16 + 22 * len(lines)
        rect = pygame.Rect(x, y, w, h)
        rect.clamp_ip(self.screen.get_rect())
        glass = pygame.Surface(rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 220))
        self.screen.blit(glass, rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_CYAN, rect, width=1, border_radius=6)
        cy = rect.y + 8
        for text, color in lines:
            self._blit_text(text, (rect.x + 10, cy), color, self.font_small)
            cy += 22

    def render_distro_select(
        self,
        rows: list[dict[str, object]],
        selected: int,
        daily: bool,
    ) -> None:
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        title_key = "distro.title_daily" if daily else "distro.title"
        title = self.font_title.render(t(title_key), True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 70)))

        x = cx - 380
        y = 140
        for i, row in enumerate(rows):
            is_sel = i == selected
            unlocked = bool(row.get("unlocked"))
            color = (
                theme.NEON_CYAN
                if is_sel and unlocked
                else (theme.TEXT_PRIMARY if unlocked else theme.TEXT_DIM)
            )
            prefix = "▶ " if is_sel else "  "
            name = str(row.get("name", "?"))
            line = f"{prefix}{name}"
            if not unlocked:
                line += f"   [{t('distro.locked')}]"
            self._blit_text(line, (x, y), color, self.font_body)
            sub_color = theme.TEXT_DIM if not is_sel else theme.NEON_GREEN
            self._blit_text(
                str(row.get("description", "")),
                (x + 24, y + 22),
                sub_color,
                self.font_small,
            )
            if not unlocked:
                self._blit_text(
                    str(row.get("unlock_hint", "")),
                    (x + 24, y + 40),
                    theme.NEON_AMBER,
                    self.font_small,
                )
            y += 70

        hint = self.font_small.render(t("distro.hint"), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_milestone_result(self, panel: dict[str, object]) -> None:
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        title = self.font_title.render(t("milestone.title"), True, theme.NEON_GREEN)
        self.screen.blit(title, title.get_rect(center=(cx, cy - 160)))

        rel = cast(int, panel.get("release_index", 0)) + 1
        ms = cast(int, panel.get("milestone_index", 0)) + 1
        kind = str(panel.get("kind", ""))
        score = cast(int, panel.get("score", 0))
        target = cast(int, panel.get("target", 0))
        bits = cast(int, panel.get("bits", 0))
        target_hit = bool(panel.get("target_hit"))
        is_boss = bool(panel.get("boss"))

        lines = [
            f"{t('milestone.release')}: {rel} / 8",
            f"{t('milestone.milestone')}: {ms} / 3   ({kind})",
            f"{t('milestone.score')}: {score} / {target}",
            f"{t('milestone.bits')}: +{bits}",
            t("milestone.target_hit") if target_hit else t("milestone.target_missed"),
        ]
        y = cy - 90
        for line in lines:
            surf = self.font_body.render(line, True, theme.TEXT_PRIMARY)
            self.screen.blit(surf, surf.get_rect(center=(cx, y)))
            y += 30

        hint_key = "milestone.hint_boss" if is_boss else "milestone.hint"
        hint = self.font_small.render(t(hint_key), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 50)))

    def render_vendor(
        self,
        bits: int,
        stock: list[dict[str, object]],
        selected: int,
        message: str | None,
        free: bool,
    ) -> None:
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render(t("vendor.title"), True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 70)))

        bits_label = t("vendor.bits", bits=bits) + (f"   [{t('vendor.free')}]" if free else "")
        bits_surf = self.font_body.render(bits_label, True, theme.NEON_GREEN)
        self.screen.blit(bits_surf, bits_surf.get_rect(center=(cx, 110)))

        x = cx - 360
        y = 160
        for i, item in enumerate(stock):
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            prefix = "▶ " if is_sel else "  "
            cost = 0 if free else cast(int, item.get("cost", 0))
            label = str(item.get("label", "?"))
            kind = str(item.get("kind", ""))
            cost_text = f"{cost}b" if cost > 0 else t("vendor.free_cost")
            line = f"{prefix}{label:<22} [{kind:<8}]   {cost_text}"
            self._blit_text(line, (x, y), color, self.font_body)
            desc = str(item.get("description", ""))
            if desc:
                self._blit_text(desc, (x + 24, y + 22), theme.TEXT_DIM, self.font_small)
            y += 50

        if message is not None:
            msg = self.font_body.render(message, True, theme.NEON_AMBER)
            self.screen.blit(msg, msg.get_rect(center=(cx, WINDOW_HEIGHT - 90)))

        hint = self.font_small.render(t("vendor.hint"), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_run_summary(self, payload: dict[str, object]) -> None:
        from kernelquest.ui.i18n import t

        self.clear()
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        success = bool(payload.get("success"))
        title_key = "summary.title_success" if success else "summary.title_failed"
        color = theme.NEON_GREEN if success else theme.NEON_MAGENTA
        title = self.font_title.render(t(title_key), True, color)
        self.screen.blit(title, title.get_rect(center=(cx, cy - 140)))

        lines = [
            f"{t('summary.distro')}: {payload.get('distro', '?')}",
            f"{t('summary.releases_cleared')}: {payload.get('releases_cleared', 0)} / 8",
            f"{t('summary.score')}: {payload.get('score', 0)}",
            f"{t('summary.bits_to_meta')}: +{payload.get('bits_to_meta', 0)}",
        ]
        unlocked = str(payload.get("unlocked_distro", ""))
        if unlocked:
            lines.append(f"{t('summary.unlocked')}: {unlocked}")

        y = cy - 60
        for line in lines:
            surf = self.font_body.render(line, True, theme.TEXT_PRIMARY)
            self.screen.blit(surf, surf.get_rect(center=(cx, y)))
            y += 30

        hint = self.font_small.render(t("summary.hint"), True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 50)))

    def render_post_run_summary(
        self,
        rows: list[tuple[str, str, int, int]],
    ) -> None:
        """Post-run combat summary overlay.

        Each row: ``(program_label, species_label, damage, kills)``.
        """
        if not rows:
            return
        w = 480
        h = 64 + 24 * len(rows)
        x = WINDOW_WIDTH // 2 - w // 2
        y = WINDOW_HEIGHT // 2 - h // 2
        rect = pygame.Rect(x, y, w, h)
        glass = pygame.Surface(rect.size, pygame.SRCALPHA)
        glass.fill((*theme.PANEL_BG, 235))
        self.screen.blit(glass, rect.topleft)
        pygame.draw.rect(self.screen, theme.NEON_AMBER, rect, width=2, border_radius=8)
        title = self.font_body.render("RUN SUMMARY", True, theme.NEON_AMBER)
        self.screen.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 12)))
        cy = rect.y + 48
        for prog, species, dmg, kills in rows[:10]:
            text = f"{prog:<10} → {species:<14} dmg {dmg:>4}  k {kills}"
            self._blit_text(text, (rect.x + 16, cy), theme.TEXT_PRIMARY, self.font_small)
            cy += 22

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
                base = _tile_color(tile)
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


__all__ = ["UIManager", "TILE_SIZE", "TUTORIAL_PAGE_COUNT"]
