# Project Specification: Kernel Quest — The Memory Leak

> Moved here from the repository root on 2026-05-04. This document is the product/architecture source of truth referenced by [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [CLAUDE.md](../CLAUDE.md).

## 1. Project Overview

Kernel Quest is a grid-based, rogue-like RPG with a GUI, where players navigate a simulated operating system's memory to purge "corrupted data" and "malware." The game emphasizes resource management (RAM/CPU Cycles) and features a persistent leaderboard via SQLite.

## 2. Technical Stack

- **Language:** Python 3.12+
- **GUI Framework:** Pygame (core gameplay) and CustomTkinter (optional launcher/leaderboard).
- **Database:** `sqlite3` (stdlib).
- **Architecture:** Object-Oriented Programming (OOP) with a Model-View-Controller (MVC) approach.

## 3. Database Schema (SQLite)

`database.db` stores the following:

### Table: `scores`

| Column          | Type      | Notes                                |
|-----------------|-----------|--------------------------------------|
| `id`            | INTEGER   | Primary key                          |
| `player_name`   | TEXT      |                                      |
| `depth_reached` | INTEGER   | Deepest sector cleared               |
| `total_score`   | INTEGER   |                                      |
| `crash_cause`   | TEXT      | e.g. "Out of RAM", "Logic Bomb"      |
| `timestamp`     | DATETIME  |                                      |

### Table: `runs` *(Phase 4)*
Per-run telemetry: seed, depth, score, crash cause, duration.

### Table: `upgrades` *(Phase 4)*
Persistent meta-progression purchased with `bits` currency.

## 4. Class Architecture (MVP)

### A. `GameEngine` (Core)
- Manages the main game loop.
- Handles state transitions (`MENU` → `PLAYING` → `GAME_OVER`).
- Owns the SQLite connection.

### B. `MemoryGrid` (Map)
- Generates a 20×20 (adjustable) grid.
- Methods: `generate_level()`, `is_walkable(x, y)`, `trigger_event(x, y)`.
- Implements simple Fog-of-War.

### C. `Entity` (Base Class)

**`Player`**
- Attributes: `ram` (health), `cpu_cycles` (energy), `cache` (inventory).
- Methods: `move()`, `attack()`, `use_item()`.

**`Malware`**
- Types: `SyntaxError` (patrols), `LogicBomb` (kamikaze), `KernelPanic` (boss).
- AI: basic pathfinding toward the player.

### D. `UIManager` (Renderer)
- Handles all `pygame.draw` calls.
- Renders the Console Log at the bottom of the screen.
- Draws RAM/CPU bars and the side panel.

## 5. Core Gameplay Mechanics

- **RAM as health.** Damage decreases RAM; "Garbage Collector" / "Optimization" packets restore it.
- **CPU cycles.** Each action (move/attack) costs cycles; cycles replenish each turn (turn-based logic inside a real-time GUI).
- **Progression.** Each sector increases in difficulty. Maps are procedurally generated from a seed.

## 6. Layered Architecture

### Layer 1 — World & Exploration (The Grid)
Procedural memory map of `EMPTY`, `SYSTEM_DATA` (obstacles), `BAD_SECTOR` (traps). Player visibility limited to a small radius (Fog of War), expandable via scan-range upgrades.

### Layer 2 — Hardware Constraints
Three primary stats:
- **RAM** (health) — 0% triggers `System Crash` (Game Over).
- **CPU Cycle** (energy) — depletes per action, replenishes each turn.
- **Cache** (inventory) — stores collected data packets.

### Layer 3 — System Threats (Enemies)
- **Minion:** `SyntaxError`
- **Elite:** `LogicBomb`
- **Boss:** `KernelPanic`

## 7. SQLite Integration

- **Leaderboard:** highest sector reached + total score.
- **Run history:** which threat caused each crash.
- **Persistence:** `bits` currency carries between runs to fund permanent upgrades (e.g. `+10 RAM`).

## 8. UI Plan

- **Main screen:** minimalist dark mode, neon green/cyan palette, glassmorphism.
- **Side panel:** real-time RAM and CPU graphs (sine waves via `math.sin`).
- **Console log (bottom):** systemd-style feed:
  ```
  [INFO] User moved to Sector 0x04. Trace detected!
  ```

## 9. Development Phases

See [ROADMAP.md](../ROADMAP.md) for the canonical, checkbox-driven plan.

1. **Phase 1 — Core Loop:** window, grid, player movement, SQLite scaffolding.
2. **Phase 2 — Procedural & Combat:** map gen, malware AI, combat, items.
3. **Phase 3 — UI & Polish:** Tron theme, HUD, console log, SFX, screen shake.
4. **Phase 4 — Persistence & Meta:** leaderboard, run history, upgrades, packaging.

## 10. Naming Conventions

Use OS-architecture metaphors throughout the codebase:

| Generic term       | Project term       |
|--------------------|--------------------|
| `player_id`        | `process_id`       |
| `health`           | `ram`              |
| `energy`           | `cpu_cycles`       |
| `level`            | `sector`           |
| `inventory`        | `cache`            |
| `death_reason`     | `crash_cause`      |

---

## 11. Phase 11 — Distros & Structured Runs

### Tables

- `distros(key TEXT PRIMARY KEY, name TEXT, unlock_condition TEXT, unlocked_at TIMESTAMP NULL, description TEXT)` — sequential unlock chain, seeded by `DistroRepository.ensure_seeded()` at boot.
- `run_milestones(id PK, run_id FK→runs, release_index INT, milestone_index INT, kind TEXT, target_score INT, reached_score INT, was_skipped INT, was_cleared INT, timestamp)` — one row per played/skipped milestone.
- `skip_tags(id PK, run_id FK→runs, tag_key TEXT, used INT)` — Skip Tags awarded during the run.

### `runs` columns added

- `distro_key TEXT NULL` — distro chosen for the run, or NULL for legacy rows.
- `is_successful INT NOT NULL DEFAULT 0` — 1 iff all 8 Releases were cleared.

### Meta-gating rule (strict)

A run unlocks meta progression **only** when `is_successful = 1`:

- meta `bits` is granted (`max(50, score // 5)`),
- the next Distro in the chain is unlocked (`DistroRepository.unlock`),
- the `true_ending` lore beat is delivered.

A failed run is still persisted into `runs` (and the milestone trail / skip tags are saved), but the engine restores the pre-run `bits` snapshot so no currency is banked.

### Localization

The UI has been routed through `kernelquest.ui.i18n`. Two locales ship today (`en`, `tr`) and can be cycled live from **Settings → Language**; the active code is persisted in `~/.kernelquest_settings.json` under `settings.language`.
