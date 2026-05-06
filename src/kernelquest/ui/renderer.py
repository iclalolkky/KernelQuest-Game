"""Pygame rendering. The UI layer is render-only - it never mutates state."""

from __future__ import annotations

import math
import random
from typing import Final

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


# ---- Tutorial (Türkçe, görsel destekli) ---------------------------------------

_TUTORIAL_PAGE_TITLES: tuple[str, ...] = (
    "1. GENEL BAKIŞ - HUD",
    "2. KARAKTER (PROCESS)",
    "3. DÜŞMANLAR (Malware)",
    "4. HARİTA & İLERLEME",
    "5. ITEMLER & CACHE",
    "6. SKOR & META PROGRESS",
    "7. KONTROLLER & TAKTİK",
)

TUTORIAL_PAGE_COUNT: Final[int] = len(_TUTORIAL_PAGE_TITLES)


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

        # Numeric HP overlay so the player can see exact remaining HP.
        hp_text = f"{enemy.hp}/{enemy.max_hp}"
        hp_surface = self.font_small.render(hp_text, True, theme.TEXT_PRIMARY)
        shadow = self.font_small.render(hp_text, True, theme.BACKGROUND)
        hp_rect = hp_surface.get_rect(
            center=(sx + viewport.tile_size // 2, sy + viewport.tile_size // 2)
        )
        self.screen.blit(shadow, hp_rect.move(1, 1))
        self.screen.blit(hp_surface, hp_rect)

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
        self._blit_text(f"Sektör  : 0x{sector:02X}", (x, y), theme.TEXT_PRIMARY, self.font_body)
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

        self._blit_text(
            f"HASAR   : {player.base_damage}", (x, y), theme.NEON_MAGENTA, self.font_body
        )
        y += 22
        self._blit_text(f"SKOR    : {player.score}", (x, y), theme.TEXT_PRIMARY, self.font_body)
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
            "[OK Tuşları] hareket / saldırı",
            "[space]    bekle",
            "[1..9]     cache yuvası kullan",
            "[esc]      RUN'u sonlandır",
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
        subtitle = self.font_body.render("Bellek Sızıntısı", True, theme.NEON_GREEN)
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        self.screen.blit(title_surface, title_surface.get_rect(center=(cx, cy - 200)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, cy - 160)))

        for i, label in enumerate(options):
            color = theme.NEON_CYAN if i == selected else theme.TEXT_PRIMARY
            prefix = "> " if i == selected else "  "
            surf = self.font_body.render(f"{prefix}{label}", True, color)
            self.screen.blit(surf, surf.get_rect(center=(cx, cy - 80 + i * 32)))

        hint = self.font_small.render(
            "[OK Tuşları] gez   [enter] seç   [esc] çıkış",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_quit_confirm(self) -> None:
        """Modal overlay asking the player to confirm exit."""
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

        title = self.font_body.render("ÇIKIŞ ONAYI", True, theme.NEON_MAGENTA)
        self.screen.blit(title, title.get_rect(center=(cx, box.y + 36)))
        msg = self.font_body.render(
            "Oyundan çıkmak istediğine emin misin?", True, theme.TEXT_PRIMARY
        )
        self.screen.blit(msg, msg.get_rect(center=(cx, box.y + 84)))

        hint = self.font_small.render(
            "[Y] / [Enter] evet, çık     [N] / [Esc] hayır, menüye dön",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, box.y + box_h - 36)))

    def render_high_scores(self, rows: list[tuple[str, int, int, str, str]]) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("YÜKSEK SKORLAR", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        if not rows:
            empty = self.font_body.render("Henüz kayıtlı RUN yok.", True, theme.TEXT_DIM)
            self.screen.blit(empty, empty.get_rect(center=(cx, WINDOW_HEIGHT // 2)))
        else:
            header = "{:<4}{:<18}{:>8}{:>8}  {:<14}{}".format(
                "#", "PROCESS", "SKOR", "DERINLIK", "ÇÖKME", "ZAMAN"
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
        title = self.font_title.render("İSTATİSTİKLER", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        x = cx - 240
        y = 130
        self._blit_text(
            f"Toplam RUN       : {run_count}", (x, y), theme.TEXT_PRIMARY, self.font_body
        )
        y += 28
        self._blit_text(
            f"Ortalama derinlik: {average_depth:.2f}",
            (x, y),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        y += 28
        if best is not None:
            best_name, best_score, best_depth = best
            self._blit_text(
                f"En iyi RUN       : {best_name} - {best_score} skor (derinlik {best_depth})",
                (x, y),
                theme.NEON_GREEN,
                self.font_body,
            )
            y += 28
        else:
            self._blit_text("En iyi RUN       : -", (x, y), theme.TEXT_DIM, self.font_body)
            y += 28

        y += 12
        self._blit_text("Çökme nedenleri:", (x, y), theme.NEON_AMBER, self.font_body)
        y += 28
        if not deaths_by_cause:
            self._blit_text("  (kayıtlı çökme yok)", (x, y), theme.TEXT_DIM, self.font_body)
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
        title = self.font_title.render("YÜKSELTME MAĞAZASI", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        bits_text = self.font_body.render(f"Mevcut bits: {bits}", True, theme.NEON_GREEN)
        self.screen.blit(bits_text, bits_text.get_rect(center=(cx, 110)))

        x = cx - 360
        y = 160
        for i, row in enumerate(rows):
            key, label, desc, level, max_level, next_cost = row
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            prefix = "> " if is_sel else "  "
            cost_label = "AZAMİ" if next_cost is None else f"{next_cost} bits"
            line = f"{prefix}{label:<10} L{level}/{max_level}    {desc}    [{cost_label}]"
            self._blit_text(line, (x, y), color, self.font_body)
            y += 28
            del key

        if message is not None:
            msg_surf = self.font_body.render(message, True, theme.NEON_AMBER)
            self.screen.blit(msg_surf, msg_surf.get_rect(center=(cx, WINDOW_HEIGHT - 90)))

        hint = self.font_small.render(
            "[OK Tuşları] seç   [enter] satın al   [esc] geri",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_settings(self, options: list[tuple[str, str]], selected: int) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        title = self.font_title.render("AYARLAR", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 80)))

        x = cx - 220
        y = 180
        for i, (label, value) in enumerate(options):
            is_sel = i == selected
            color = theme.NEON_CYAN if is_sel else theme.TEXT_PRIMARY
            prefix = "> " if is_sel else "  "
            self._blit_text(f"{prefix}{label:<14} : {value}", (x, y), color, self.font_body)
            y += 32

        hint = self.font_small.render(
            "[OK Tuşları] seç   [</>] değiştir   [esc] geri",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def _blit_back_hint(self) -> None:
        cx = WINDOW_WIDTH // 2
        hint = self.font_small.render("[esc] geri", True, theme.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    def render_tutorial(self, page: int) -> None:
        """Render a single tutorial page (0-indexed) with paging hints.

        Each page draws actual in-game iconography (enemy sprites, tile colors,
        item glyphs, mock HUD) so a brand-new player can recognize them at a
        glance once the run starts.
        """
        self.clear()
        cx = WINDOW_WIDTH // 2
        page = max(0, min(TUTORIAL_PAGE_COUNT - 1, page))
        title_text = _TUTORIAL_PAGE_TITLES[page]

        title = self.font_title.render("NASIL OYNANIR", True, theme.NEON_CYAN)
        self.screen.blit(title, title.get_rect(center=(cx, 50)))
        section = self.font_body.render(title_text, True, theme.NEON_AMBER)
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
            f"Sayfa {page + 1}/{TUTORIAL_PAGE_COUNT}", True, theme.TEXT_DIM
        )
        self.screen.blit(page_label, page_label.get_rect(center=(cx, WINDOW_HEIGHT - 64)))

        hint = self.font_small.render(
            "[</>] sayfa değiştir   [enter/space] ileri   [esc] menüye dön",
            True,
            theme.TEXT_DIM,
        )
        self.screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    # ----- tutorial helpers -----

    def _tutorial_overview(self, top: int) -> None:
        """Mock HUD with callouts: RAM, CYCLES, HASAR, SCORE, CACHE, MINIMAP."""
        cx = WINDOW_WIDTH // 2
        intro = "RUN sırasında ekranın sağında her zaman görünen HUD paneli budur."
        self._blit_text(intro, (cx - 460, top), theme.TEXT_PRIMARY, self.font_body)
        self._blit_text(
            "Aşağıdaki örnekte hangi alan ne işe yarıyor görebilirsin:",
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
        self._blit_text("Sektör  : 0x03", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 22
        self._blit_text("Process : process_0", (x, y), theme.TEXT_PRIMARY, self.font_body)
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
        self._blit_text("HASAR   : 10", (x, y), theme.NEON_MAGENTA, self.font_body)
        y += 22
        score_y = y
        self._blit_text("SKOR    : 245", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 24
        cache_y = y
        self._blit_text("CACHE   : 2/8", (x, y), theme.TEXT_PRIMARY, self.font_body)
        y += 22
        # Two filled cache slots + empty slots.
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

        # Callouts pointing from the panel to descriptions on the right.
        callouts = [
            (ram_y + 10, "RAM = canın. 0 olursa SYSTEM CRASH.", theme.NEON_GREEN),
            (cycles_y + 10, "CYCLES = bu turda harcayabileceğin enerji.", theme.NEON_AMBER),
            (damage_y + 10, "HASAR = bir vuruşta verdiğin temel hasar.", theme.NEON_MAGENTA),
            (score_y + 10, "SKOR = RUN boyunca biriken puan.", theme.TEXT_PRIMARY),
            (cache_y + 26, "CACHE = envanter; [1..9] ile yuva kullanılır.", theme.NEON_CYAN),
        ]
        text_x = panel_x + panel_w + 40
        line_start_x = panel_x + panel_w + 4
        for cy_, text, color in callouts:
            pygame.draw.line(self.screen, color, (line_start_x, cy_), (text_x - 10, cy_), 1)
            self._blit_text(text, (text_x, cy_ - 10), color, self.font_body)

        # Bottom note about minimap & console.
        note_y = panel_y + panel_h + 16
        self._blit_text(
            "Panelin altında MINIMAP (sektörün küçük haritası) yer alır.",
            (panel_x, note_y),
            theme.TEXT_DIM,
            self.font_body,
        )
        self._blit_text(
            "Ekranın altındaki konsol son olayları (saldırı, ölüm, item) gösterir.",
            (panel_x, note_y + 22),
            theme.TEXT_DIM,
            self.font_body,
        )

    def _tutorial_character(self, top: int) -> None:
        """Player avatar + RAM/CYCLES bars with explanations."""
        cx = WINDOW_WIDTH // 2
        # Player sprite (same as in-game render_player).
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
        self._blit_text("Sen (Process)", (ox, oy + cell + 8), theme.NEON_GREEN, self.font_body)
        self._blit_text(
            "Yeşil daire = oyuncu",
            (ox, oy + cell + 32),
            theme.TEXT_DIM,
            self.font_small,
        )

        text_x = ox + 200
        ty = oy
        line_h = self.font_body.get_height() + 6
        rows: tuple[tuple[tuple[int, int, int], str], ...] = (
            (theme.NEON_GREEN, "RAM    = canın. Düşman, Bad Sector ve LogicBomb azaltır."),
            (theme.TEXT_PRIMARY, "         0'a inerse SYSTEM CRASH (RUN biter)."),
            (theme.NEON_AMBER, "CYCLES = her tur kullanılan enerji havuzu."),
            (theme.TEXT_PRIMARY, "         Hareket = 1 cycle, saldırı = 1 cycle."),
            (theme.TEXT_PRIMARY, "         Tur sonunda otomatik dolar; biriktirilemez."),
            (theme.NEON_CYAN, "CACHE  = topladığın paketlerin envanteri."),
            (theme.TEXT_PRIMARY, "         Doluyken yeni item alamazsın."),
            (theme.NEON_MAGENTA, "HASAR  = saldırıda verilen temel hasar (HUD'da yazar)."),
        )
        for color, text in rows:
            self._blit_text(text, (text_x, ty), color, self.font_body)
            ty += line_h

        # Demo RAM bar - placed below both the avatar caption and the rows.
        demo_y = max(ty + 24, oy + cell + 64)
        self._blit_text("RAM bar örnekleri:", (ox, demo_y), theme.TEXT_PRIMARY, self.font_body)
        demo_y += 24
        for ratio, color, label in (
            (0.9, theme.NEON_GREEN, "yüksek"),
            (0.4, theme.NEON_AMBER, "orta"),
            (0.15, (255, 110, 110), "kritik"),
        ):
            self._render_bar((ox, demo_y), 232, 12, ratio, color)
            self._blit_text(label, (ox + 244, demo_y - 2), color, self.font_body)
            demo_y += 22

        self._blit_text(
            "Renk kritiğe döndüğünde GarbageCollector kullanmayı düşün.",
            (ox, demo_y + 8),
            theme.NEON_AMBER,
            self.font_body,
        )

    def _tutorial_enemies(self, top: int) -> None:
        """Three rows: real enemy sprite + name + behaviour description."""
        cx = WINDOW_WIDTH // 2
        cell = 64
        ox = cx - 460
        rows: tuple[tuple[type[Malware], int, int, str, str, list[str]], ...] = (
            (
                SyntaxError_,
                8,
                8,
                "SyntaxError",
                "Sarı, zayıf ama kalabalık. (8 RAM)",
                [
                    "- Yakına gelir, bitişikteyken seni ısırır (-4 RAM).",
                    "- %25 ihtimalle rasgele bir yöne kayar.",
                    "- Tek vuruşta ölmesi kolaydır.",
                ],
            ),
            (
                LogicBomb,
                12,
                10,
                "LogicBomb",
                "Kırmızı, yavaş ama tehlikeli. (12 RAM)",
                [
                    "- 1 kare yakınına girersen kendini patlatır.",
                    "- AoE patlama -18 RAM (her yöne).",
                    "- Mesafeden öldürmek genelde daha güvenlidir.",
                ],
            ),
            (
                KernelPanic,
                60,
                42,
                "KernelPanic",
                "Mor, BOSS. Sektör 5+'da çıkar. (60 RAM)",
                [
                    "- Bitişikteyken ezer (-12 RAM).",
                    "- Canı yarıya inince 'enraged' olur:",
                    "  doğru çizgide kernel-tuzağı atar.",
                ],
            ),
        )

        y = top + 10
        line_h = self.font_body.get_height() + 4
        for cls, max_hp, current_hp, name, header, desc in rows:
            # Real-style sprite with HP pips and HP number overlay.
            self._tutorial_draw_enemy(cls, max_hp, current_hp, ox, y, cell)
            color_map = {
                SyntaxError_: theme.ENEMY_SYNTAX_ERROR,
                LogicBomb: theme.ENEMY_LOGIC_BOMB,
                KernelPanic: theme.ENEMY_KERNEL_PANIC,
            }
            name_color = color_map[cls]
            tx = ox + cell + 24
            self._blit_text(name, (tx, y), name_color, self.font_body)
            self._blit_text(header, (tx, y + 22), theme.TEXT_DIM, self.font_small)
            for i, line in enumerate(desc):
                self._blit_text(line, (tx, y + 44 + i * line_h), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 60

        self._blit_text(
            "İpucu: Her düşmanın üstünde HP/MaxHP rakamı ve renkli pip-bar görünür.",
            (ox, y + 8),
            theme.NEON_CYAN,
            self.font_body,
        )

    def _tutorial_draw_enemy(
        self, cls: type[Malware], max_hp: int, hp: int, ox: int, oy: int, cell: int
    ) -> None:
        """Render a single enemy preview (matches in-game `_render_enemy`)."""
        color_map = {
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
        cx = WINDOW_WIDTH // 2
        cell = 56
        ox = cx - 460
        rows: tuple[tuple[TileType, str, str, tuple[int, int, int]], ...] = (
            (
                TileType.SYSTEM_DATA,
                "System Data",
                "YÜRÜNEBİLİR koridor. RUN'un büyük kısmını burada geçirirsin.",
                theme.NEON_GREEN,
            ),
            (
                TileType.EMPTY,
                "Boşluk / Duvar",
                "Yürünemez. Hareket bu kareye gitmeye çalışırsa engellenir.",
                theme.TEXT_DIM,
            ),
            (
                TileType.BAD_SECTOR,
                "Bad Sector",
                "YÜRÜNEBİLİR ama her basışta -5 RAM yakar. Mecbur kalmadıkça basma.",
                (255, 110, 110),
            ),
            (
                TileType.EXIT,
                "EXIT (pembe)",
                "YÜRÜNEBİLİR. Üstüne basar basmaz bir alt sektöre geçersin (+100 skor).",
                theme.NEON_MAGENTA,
            ),
        )
        y = top + 10
        for tile, name, desc, name_color in rows:
            tile_rect = pygame.Rect(ox, y, cell, cell)
            pygame.draw.rect(self.screen, _TILE_COLORS[tile], tile_rect)
            pygame.draw.rect(self.screen, theme.GRID_LINE, tile_rect, 1)
            tx = ox + cell + 24
            self._blit_text(name, (tx, y + 4), name_color, self.font_body)
            self._blit_text(desc, (tx, y + 28), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 16

        # "Player on EXIT" demo.
        demo_x = ox
        demo_y = y + 10
        self._blit_text(
            "Örnek: oyuncu EXIT (pembe) karesine basıyor -> sonraki sektör.",
            (demo_x, demo_y),
            theme.NEON_AMBER,
            self.font_body,
        )
        demo_y += 28
        for i, tile in enumerate(
            (TileType.SYSTEM_DATA, TileType.SYSTEM_DATA, TileType.EXIT, TileType.SYSTEM_DATA)
        ):
            r = pygame.Rect(demo_x + i * (cell + 4), demo_y, cell, cell)
            pygame.draw.rect(self.screen, _TILE_COLORS[tile], r)
            pygame.draw.rect(self.screen, theme.GRID_LINE, r, 1)
            if i == 2:
                pygame.draw.circle(
                    self.screen,
                    theme.PLAYER_COLOR,
                    r.center,
                    cell // 2 - 8,
                )
                pygame.draw.circle(
                    self.screen,
                    theme.NEON_CYAN,
                    r.center,
                    cell // 2 - 8,
                    2,
                )

        # Fog-of-war note.
        note_y = demo_y + cell + 16
        self._blit_text(
            "Görüş yarıçapın sınırlıdır (Fog of War). Karanlık kareler kararır.",
            (ox, note_y),
            theme.TEXT_DIM,
            self.font_body,
        )
        self._blit_text(
            "ScanBoost (item) veya +Scan (mağaza) görüş yarıçapını büyütür.",
            (ox, note_y + 22),
            theme.TEXT_DIM,
            self.font_body,
        )

    def _tutorial_items(self, top: int) -> None:
        """Item glyphs as drawn on the floor + cache strip + usage explanation."""
        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        cell = 56

        items: tuple[tuple[str, str, str, str, tuple[int, int, int]], ...] = (
            (
                "gc",
                "G",
                "GarbageCollector",
                "Anında +25 RAM geri yükler. RAM kritikken kullan.",
                theme.ITEM_GC,
            ),
            (
                "opt",
                "O",
                "Optimization",
                "Tur ortasında +3 CPU cycle verir. Ekstra saldırı / kaçış için.",
                theme.ITEM_OPTIMIZATION,
            ),
            (
                "scan",
                "S",
                "ScanBoost",
                "5 tur boyunca tarama yarıçapını büyütür. Keşif için ideal.",
                theme.ITEM_SCAN_BOOST,
            ),
        )
        y = top + 10
        for _id, glyph, name, desc, color in items:
            tile_rect = pygame.Rect(ox, y, cell, cell)
            pygame.draw.rect(self.screen, theme.TILE_SYSTEM_DATA, tile_rect)
            pygame.draw.rect(self.screen, theme.GRID_LINE, tile_rect, 1)
            center = tile_rect.center
            pygame.draw.circle(self.screen, color, center, cell // 4)
            label = self.font_small.render(glyph, True, theme.BACKGROUND)
            self.screen.blit(label, label.get_rect(center=center))
            tx = ox + cell + 24
            self._blit_text(name, (tx, y + 4), color, self.font_body)
            self._blit_text(desc, (tx, y + 28), theme.TEXT_PRIMARY, self.font_body)
            y += cell + 12

        # Cache strip visualization.
        strip_y = y + 16
        self._blit_text(
            "CACHE: HUD'da 8 yuvalı şerit. [1..9] tuşlarıyla yuvayı kullanırsın.",
            (ox, strip_y),
            theme.NEON_CYAN,
            self.font_body,
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
            "Item üstüne basınca otomatik cache'e alınır.",
            (ox, notes_y),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        self._blit_text(
            "Cache doluysa item yerde kalır - önce bir yuvayı boşalt.",
            (ox, notes_y + 22),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        self._blit_text(
            "Düşman öldürünce %35 ihtimalle item düşürür.",
            (ox, notes_y + 44),
            theme.TEXT_DIM,
            self.font_body,
        )

    def _tutorial_score_meta(self, top: int) -> None:
        """Score table + bits formula + shop list."""
        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        line_h = self.font_body.get_height() + 6

        self._blit_text("SKOR NASIL ARTAR?", (ox, top), theme.NEON_AMBER, self.font_body)
        score_rows = (
            "- Her hareket             : +1 skor",
            "- SyntaxError öldürmek    : +25 skor",
            "- LogicBomb öldürmek      : +50 skor",
            "- KernelPanic öldürmek    : +250 skor",
            "- Bir alt sektöre inmek   : +100 skor",
        )
        y = top + 30
        for row in score_rows:
            self._blit_text(row, (ox, y), theme.TEXT_PRIMARY, self.font_body)
            y += line_h
        y += 8
        self._blit_text(
            "RUN bitince skor + derinlik + çökme nedeni veritabanına kaydedilir.",
            (ox, y),
            theme.NEON_CYAN,
            self.font_body,
        )

        meta_y = y + line_h * 2
        self._blit_text(
            "META PROGRESS (RUN'lar arası kalıcı):", (ox, meta_y), theme.NEON_GREEN, self.font_body
        )
        meta_y += 28
        self._blit_text(
            "Her RUN sonunda 'bits' kazanırsın:", (ox, meta_y), theme.TEXT_PRIMARY, self.font_body
        )
        meta_y += line_h
        self._blit_text(
            "    bits = (skor / 10) + (ulaşılan derinlik x 2)",
            (ox, meta_y),
            theme.NEON_AMBER,
            self.font_body,
        )
        meta_y += line_h + 4
        self._blit_text(
            "Bits'i Mağaza'da kalıcı yükseltmelere harcarsın:",
            (ox, meta_y),
            theme.TEXT_PRIMARY,
            self.font_body,
        )
        meta_y += line_h
        upgrades = (
            ("+RAM", "azami RAM (5 seviye)", theme.NEON_GREEN),
            ("+Cycle", "başlangıç CPU cycle (3 seviye)", theme.NEON_AMBER),
            ("+Scan", "kalıcı tarama yarıçapı (3 seviye)", theme.ITEM_SCAN_BOOST),
            ("+Hasar", "her vuruşa eklenir (3 seviye)", theme.NEON_MAGENTA),
            ("+Cache", "cache yuva sayısı (2 seviye)", theme.NEON_CYAN),
        )
        for label, desc, color in upgrades:
            self._blit_text(f"  {label:<8}- {desc}", (ox, meta_y), color, self.font_body)
            meta_y += line_h

        self._blit_text(
            "Yükseltmeler kalıcıdır; her yeni RUN onlarla başlar.",
            (ox, meta_y + 6),
            theme.TEXT_DIM,
            self.font_body,
        )

    def _tutorial_controls(self, top: int) -> None:
        cx = WINDOW_WIDTH // 2
        ox = cx - 460
        line_h = self.font_body.get_height() + 8

        self._blit_text("KONTROLLER", (ox, top), theme.NEON_AMBER, self.font_body)
        rows = (
            ("[OK Tuşları] / [W A S D]", "hareket / bitişik düşmana saldırı"),
            ("[SPACE]", "bekle (1 tur, düşmanlar oynar)"),
            ("[1] .. [9]", "cache yuvasındaki itemi kullan"),
            ("[ESC]", "RUN'u sonlandır / menüye dön"),
        )
        y = top + 32
        for keys, action in rows:
            self._blit_text(f"{keys:<28}{action}", (ox, y), theme.TEXT_PRIMARY, self.font_body)
            y += line_h

        y += 8
        self._blit_text("OYUN MANTALITESI", (ox, y), theme.NEON_CYAN, self.font_body)
        y += 28
        tactics = (
            "1. Cycle ekonomisini yönet: gereksiz hareket etme.",
            "2. RAM'i koru: Bad Sector'lere basma, LogicBomb yarıçapına girme.",
            "3. Cache'ini stratejik boşalt: GC kritikte, Optimization kalabalıkta.",
            "4. Bilmediğin koridora dalmadan tarama yarıçapını kullan.",
            "5. KernelPanic ile karşılaştığında doğru çizgide kalma (kernel-tuzağı).",
            "6. RUN bitse de bits biriktirir, bir sonraki sefer daha güçlü başlarsın.",
        )
        for line in tactics:
            self._blit_text(line, (ox, y), theme.TEXT_PRIMARY, self.font_body)
            y += line_h

        self._blit_text(
            "Hazır mısın? Ana menüden 'Yeni RUN' ile başlayabilirsin.",
            (ox, y + 8),
            theme.NEON_GREEN,
            self.font_body,
        )

    def render_game_over(self, player: Player, name_buffer: str) -> None:
        self.clear()
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        title = self.font_title.render("SYSTEM CRASH", True, theme.NEON_MAGENTA)
        cause = self.font_body.render(
            f"Çökme nedeni: {player.crash_cause or 'bilinmiyor'}",
            True,
            theme.TEXT_PRIMARY,
        )
        score = self.font_body.render(
            f"Temizlenen sektör: {player.depth_reached}    Skor: {player.score}",
            True,
            theme.TEXT_PRIMARY,
        )
        prompt = self.font_body.render("Process adını gir ve [ENTER]'a bas:", True, theme.NEON_CYAN)
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


__all__ = ["UIManager", "TILE_SIZE", "TUTORIAL_PAGE_COUNT"]
