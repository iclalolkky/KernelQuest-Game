# Changelog

All notable changes to **Kernel Quest: The Memory Leak** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

### Added (previous)
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
- _Nothing yet._

### Fixed
- _Nothing yet._

---

## [0.1.0] — TBD

First playable prototype (Phase 1 exit criteria).

- Static grid with player movement.
- SQLite scoreboard scaffolding.
- Pygame window and turn-based loop.
