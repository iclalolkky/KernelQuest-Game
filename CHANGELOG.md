# Changelog

All notable changes to **Kernel Quest: The Memory Leak** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-05-05

> **The "Juice + Onboarding" release.** Phases 5 and 6 land together: stacking modifiers (Programs, Daemons, Patch Notes), combo scoring, a second boss, daily seeds, a guided tutorial, themes, and a full accessibility/display options pass.

### Added — Phase 5: Mechanics Expansion ("The Juice Update")

- **Programs (active abilities).** New `Program` entity — card-like usables with cooldown and charges, hot-keyed to **Q / E / R**. Catalog includes `fork()`, `kill -9`, `sudo`, `grep`, `nice`, `nohup`, `chmod +x`. Backed by `programs` table + `ProgramRepository`.
- **Daemons (passive modifiers).** New `Daemon` entity — up to 5 equipped slots, drag-and-drop reorder. Synergy tags (`arithmetic`, `io`, `network`, `memory`, `signal`) trigger combo bonuses when stacked. Examples: `cron`, `swapd`, `oom-killer`, `tcpdump`, `niced`.
- **Combo / chain scoring.** Score formula is now `base × multiplier`. Multiplier grows on consecutive kill → pickup → kill turns; breaks on damage taken or 3+ idle turns. Balatro-style multiplier widget pops/scales on increase.
- **Patch Notes (run modifiers).** Between sectors, the player picks one of three random **Patch** cards. Catalog grew from a handful to **20 cards** spanning 13 effect dimensions (`player_damage_mult`, `enemy_damage_mult`, `enemy_hp_mult`, `enemy_speed_bonus`, `score_mult`, `fov_radius_bonus`, `extra_enemies_per_sector`, `pickup_score_mult`, `ram_per_action`, `starting_ram_bonus`, `cycle_refund_on_pickup`, `combo_decay_bonus`, `boss_damage_mult`). New cards: `kernel-bypass`, `dark-mode`, `fragmented`, `noatime`, `thermal-throttle`, `lazy-eval`, `page-fault`, `swap-thrash`, `stack-trace`, `root-kit`, `heap-spray`, `zero-copy`, `opportunistic`, `ddos`. Backed by `patches` table; selected patches render as HUD chips.
- **New boss & elite.** `ZombieProcess` elite mob (revives once on death). Second boss `SegFault` — teleports and splits the grid into halves. Both bosses now drop a guaranteed Daemon.
- **Boss redesign — radical.** Bosses are flagged `is_boss=True`; the **EXIT tile is locked** while a boss is alive (descending logs `[CRIT] EXIT LOCKED — terminate <boss> first.`). Each boss spawn:
  - swaps the BGM to a dedicated boss track,
  - flashes a red, full-width **BOSS HP bar** at the top of the screen,
  - shows a flashing **"!! BOSS LOADED !!"** banner with `EXIT LOCKED` subtitle,
  - triggers a **glitch overlay** (random horizontal slice offsets + faint red tint) that decays over time,
  - plays a `boss_warn` sweep SFX (110→880 Hz over 600 ms).
- **Daily seed challenge.** Date-based seed (`YYYY-MM-DD` → RNG); same dungeon for everyone that day. New `Daily Run` menu entry and **Daily Board** local leaderboard.
- **Carry-over data fix.** One-time migration that backfills `runs` from any pre-Phase-4 `scores` rows so the Stats screen matches High Scores. `RunRepository.best()` falls back to `ScoreRepository.top_n(1)` when `runs` is empty.

### Added — Phase 6: Onboarding, UI Polish & Accessibility

- **First-Boot tutorial.** New `GameState.TUTORIAL` with a 7-step guided walk-through (movement, bump-attack, cache, programs, daemons, patches, exit). On first launch (no rows in `scores`), the engine logs a hint pointing at the Tutorial menu entry. Completion is persisted via `meta.tutorial_done`. Re-entry is always available from the menu.
- **In-game `?` / `F1` help overlay.** Contextual cheat-sheet of current controls.
- **Persistent mini help-bar.** Bottom of every screen lists the 4–5 most relevant keybinds for the current state.
- **`HOWTOPLAY.md` viewer.** New `GameState.HOWTOPLAY` reads `HOWTOPLAY.md` from the repo and renders it as scrollable text (↑/↓, PgUp/PgDn).
- **Theme registry.** New `ui/themes.py` with 4 starter palettes — **Kernel** (default neon cyan/magenta), **Phosphor Green**, **Amber CRT**, **High Contrast**. `apply_theme()` mutates the runtime `ui.theme` module so every renderer call picks up the new palette live. Choice persists in `meta`. `ui/theme.py` constants had `Final[]` annotations stripped to allow live theme swaps.
- **Display options.** **F11** fullscreen toggle (also in Settings). UI scale slider 0.75× – 1.5× for hi-DPI users.
- **Audio polish.** Settings split **Music** and **SFX** volume sliders; **M** key (or Settings row) toggles persistent mute. Three alternate chiptune tracks (`main`, `variant_a`, `boss`, `tutorial`) selectable by context. New SFX `boss_warn` and `glitch`.
- **Accessibility.**
  - **Reduce motion** option — disables screen shake and clears particle pops; gates floating-text spawns.
  - **Large text** mode — multiplies every font size by 1.25 at boot.
  - **High Contrast** theme preset for colorblind / low-vision users.
  - Screen-reader-friendly fallbacks: every HUD-relevant change is mirrored to the in-game `ConsoleLog`.
- **Visual polish.**
  - **CRT scanline** post-process overlay (every-3-pixel dim line), toggleable in Settings.
  - **Floating numbers.** New `FloatingTextSystem` (`ui/fx.py`) renders `+score` / `-RAM` pops with upward velocity and alpha fade.
  - **Score readout** uses comma separators (`f"{player.score:,}"`).

### Changed

- **`Settings` model** vastly expanded: `music_volume`, `sfx_volume`, `muted`, `theme`, `fullscreen`, `ui_scale`, `reduce_motion`, `crt_effect`, `large_text` (alongside existing `volume`, `difficulty`). All round-trip through `MetaRepository`.
- **`GameEngine`** rewritten with new state machine entries (`TUTORIAL`, `HOWTOPLAY`), boss-state tracking (`_boss_active`, `_boss_banner_ttl`, `_glitch_intensity`), floating-text system, theme bootstrap, and 10-row Settings screen with `_handle_settings_key` cycling and `_adjust_setting` dispatch.
- **`world/generator.py`** now accepts `extra_enemies` (threaded from `extra_enemies_per_sector` patch effect) on top of the depth-scaled base count.
- **`UIManager`** picks tile/item/level colors via runtime attribute lookups instead of frozen dicts so theme switches take effect immediately. New methods: `render_floating_text`, `render_boss_hp_bar`, `render_boss_banner`, `render_glitch_overlay`, `render_scanlines`, `render_help_overlay`, `render_tutorial`, `render_howtoplay`.
- **Main menu** options: **New Run, Daily Run, Tutorial, How to Play, High Scores, Daily Board, Stats, Shop, Settings, Quit**.
- **Patch pickup** now applies one-shot effects on selection: `starting_ram_bonus` raises `player.max_ram + ram` and `fov_radius_bonus` extends `bonus_scan_radius` (FOV recomputed).

### Fixed

- Stats screen no longer shows zero best-run when `runs` table is empty but `scores` has rows (RunRepository fallback).
- Theme constants are now actually mutable at runtime (the `Final[]` annotations were preventing live theme swaps).

### Tests & quality gate

- 142 tests total (was 127). 15 new Phase-6 tests covering theme registry mutation, settings round-trip, patch catalog uniqueness/effects, boss flag wiring, `World.living_boss()`, and `extra_enemies` plumbing.
- `ruff`, `black`, `mypy --strict`, and `pytest` all green at release.

---

## [1.0.0] — 2025-12

First release tag. Includes Phases 0 – 4 in full (see Phase entries below).

### Added
- **Phase 4 — Persistence, Meta-progression & Final Integration (complete).**
  - `data/migrations.py`: `002_runs` adds the `runs` table (seed/depth/score/crash_cause/duration_ms/timestamp); `003_meta` adds the `meta_state` KV store and the `upgrades` table.
  - `data/repositories.py`: `RunRepository` (insert + `all` + `deaths_by_cause` + `average_depth` + `best`), `MetaRepository` (`get`/`set`/`get_int`/`set_int` over an UPSERT-backed key/value store), `UpgradeRepository` (catalog-validated level CRUD).
  - `data/upgrades_catalog.py`: typed catalog of five persistent upgrades (`ram`, `cycle`, `scan`, `damage`, `cache`) with deterministic cost curves and `PlayerBonus` accumulator.
  - `core/settings.py`: `Difficulty` enum (`EASY`/`NORMAL`/`HARD`) with player/enemy damage multipliers, persisted via `MetaRepository`.
  - `core/engine.py`: extended state machine (`MENU`/`HIGH_SCORES`/`STATS`/`SHOP`/`SETTINGS`/`PLAYING`/`GAME_OVER`/`QUIT`), keyboard-driven menu navigation, run timer, automatic `bits` award on game over, applies upgrade bonuses to fresh runs, applies difficulty multipliers to combat.
  - `systems/ai.py`: `run_enemy_turn` now accepts a `damage_multiplier`, scaling all enemy damage paths.
  - `ui/renderer.py`: new screens for high scores, stats, shop (with bits and cost preview), settings, and a navigable main menu.
  - `ui/sfx.py`: optional chiptune background loop synthesized from a triangle-wave arpeggio with seamless playback, runtime master-volume control, and graceful no-op on devices without audio.
  - 21 new unit tests: run/meta/upgrade repositories, settings (round-trip + clamping + garbage handling), upgrades catalog, and AI difficulty wiring.
  - `kernelquest.spec`: PyInstaller spec for one-file builds on macOS/Windows/Linux.

- **Phase 0 — Bootstrapping (complete).** `pyproject.toml`, package layout, lint/format/type/test tooling, GitHub Actions CI, MIT license, issue & PR templates, `.editorconfig`, `.gitignore`.
- **Phase 1 — Core Loop (complete).**
  - `core/engine.py`: `GameEngine` with FPS cap, delta-time, state machine (`MENU`/`PLAYING`/`GAME_OVER`/`QUIT`), clean shutdown.
  - `world/`: `TileType` enum (`EMPTY`, `SYSTEM_DATA`, `BAD_SECTOR`) and `MemoryGrid` with static default layout.
  - `entities/`: `Entity` base class and `Player` with `ram`, `cpu_cycles`, `cache`, turn-based movement, damage, healing.
  - `ui/`: `theme` palette, `Viewport` (centered grid), `UIManager` rendering grid, player, HUD, menu, and game-over screens.
  - `data/`: `Database` with idempotent migrations, `ScoreRepository` (`insert`, `top_n`, `all`).
  - 24 unit tests across grid, player, database.
- **Phase 2 — Procedural Generation & Combat (complete).**
  - `world/generator.py`: deterministic rooms-and-corridors generator with reachability, depth-scaled difficulty, and an `EXIT` tile that descends to the next sector.
  - `world/world.py`: `World` aggregate (grid + player + enemies + items) with `enemy_at`, `is_blocked`, `remove_dead_enemies`.
  - `entities/malware.py`: `Malware` base + `SyntaxError`, `LogicBomb` (AoE), and `KernelPanic` (two-phase boss).
  - `entities/items.py`: `GarbageCollector`, `Optimization`, `ScanBoost` consumables with a typed registry.
  - `systems/`: `pathfinding` (BFS), `combat` (bump-attack, loot rolls, score), `ai` (per-enemy turn dispatcher), `inventory` (pickup + cache slot use).
  - `ui/renderer.py`: renders enemies (with HP pips), items, EXIT tile, scan-boost overlay, and a numbered cache strip in the HUD.
  - `core/engine.py`: refactored to drive the new `World`, run AI when cycles deplete, descend on `EXIT`, and handle 1-9 cache hotkeys.
  - 33 new unit tests covering generator, malware, pathfinding, combat, items, inventory, world, and AI behavior.
- **Phase 3 — UI & Polish (complete; chiptune loop deferred).**
  - `ui/console_log.py`: ring-buffered, color-coded severity log (`INFO`/`WARN`/`ERROR`/`CRIT`); rendered as a glassmorphism feed at the bottom of the screen.
  - `systems/fov.py` + `World.recompute_fov`: Bresenham line-of-sight visibility with dimmed "explored" memory; `ScanBoost` extends the radius.
  - `ui/renderer.py`: animated RAM bar with low-RAM color shifts, live `math.sin` CPU waveform, mini-map with entity markers, glass side panel.
  - `ui/fx.py`: decaying screen shake (applied on damage and kills) plus a particle system used for attack/kill/pickup bursts.
  - `ui/sfx.py`: `SoundManager` with procedurally-synthesized square-wave SFX (move/attack/explode/pickup/crash/descend) that gracefully no-ops when no audio device is available.
  - 17 new unit tests for the console log, FOV, FX, and World fog-of-war integration.
- Initial project documentation: `README.md`, `ROADMAP.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `AGENTS.md`.
- Product spec: `docs/PRD_AND_ARCH.md`.

### Changed
- _Nothing in this release._

### Fixed
- _Nothing in this release._
