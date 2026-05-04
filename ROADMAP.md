# Kernel Quest — Development Roadmap

This roadmap breaks the project into four phases, each with concrete, testable deliverables. Treat each checkbox as a unit of work small enough to ship in a single commit/PR.

> Status legend: `[ ]` not started · `[~]` in progress · `[x]` complete

---

## Phase 0 — Project Bootstrapping ✅

**Goal:** A clean, runnable Python project with tooling in place.

- [x] Initialize `pyproject.toml` (project metadata, deps: `pygame`, dev: `pytest`, `ruff`, `black`, `mypy`).
- [x] Create `src/kernelquest/` package layout.
- [x] Add `.gitignore` (Python, venv, IDE, SQLite db files, asset caches).
- [x] Add `.editorconfig`.
- [x] Configure `ruff` + `black` + `mypy` in `pyproject.toml`.
- [x] Add a smoke test that imports the package.
- [x] CI: GitHub Actions workflow running `ruff`, `pytest`, `mypy` on push/PR.
- [x] `LICENSE` (MIT) and updated `README.md`.

**Exit criteria:** `python -m kernelquest.main` opens an empty Pygame window; `pytest` passes.

---

## Phase 1 — The Core Loop ✅

**Goal:** A minimum playable prototype: player on a static grid, turn-based, scores persisted.

### 1.1 Engine skeleton
- [x] `GameEngine` class managing the main loop (`init` → `update` → `render` → `quit`).
- [x] `GameState` enum: `MENU`, `PLAYING`, `GAME_OVER`.
- [x] FPS cap, delta-time tracking, clean shutdown.

### 1.2 Static grid & rendering
- [x] `MemoryGrid` (e.g. 20×20) with tile types: `EMPTY`, `SYSTEM_DATA`, `BAD_SECTOR`.
- [x] `UIManager.render_grid()` draws cells with neon palette.
- [x] Camera/viewport (if grid > screen).

### 1.3 Player movement
- [x] `Entity` base class.
- [x] `Player` with `ram`, `cpu_cycles`, `cache`, `position`.
- [x] Keyboard input → `move(dx, dy)`; respect walls and grid bounds.
- [x] Turn-based tick: each player action consumes a CPU cycle and advances the world.

### 1.4 Persistence groundwork
- [x] `database.py`: open/close SQLite, run migrations.
- [x] `scores` table (`id`, `player_name`, `depth_reached`, `total_score`, `crash_cause`, `timestamp`).
- [x] `ScoreRepository` with `insert`, `top_n`, `all`.
- [x] Game-over flow: prompt name → write row → return to menu.

**Exit criteria:** Player walks on a grid; closing the game writes a row to `scores`.

---

## Phase 2 — Procedural Generation & Combat ✅

**Goal:** Replayable, dangerous runs.

### 2.1 Procedural grid
- [x] Seedable RNG (`random.Random(seed)`); record seed in run metadata.
- [x] Generation algorithm (rooms + corridors **or** cellular automata) with reachability validation.
- [x] Increase difficulty with depth (more enemies, denser obstacles).

### 2.2 Enemies
- [x] `Malware` base class with `hp`, `damage`, `take_turn(world)`.
- [x] `SyntaxError`: random/patrol movement.
- [x] `LogicBomb`: charges player, AoE detonation when adjacent.
- [x] `KernelPanic` (boss): multi-phase pattern, larger footprint.
- [x] Basic pathfinding (BFS or A*) toward player.

### 2.3 Combat
- [x] Bump-to-attack on adjacent enemy.
- [x] Damage application + death cleanup.
- [x] Loot drops → added to `Player.cache`.
- [x] **Game Over:** RAM ≤ 0 → record crash cause (enemy class name).

### 2.4 Items & cache
- [x] Item types: `GarbageCollector` (restore RAM), `Optimization` (refund cycles), `ScanBoost` (extend FoV).
- [x] Inventory UI; `use_item(slot)`.

**Exit criteria:** Death is possible and meaningful; depth, score, and crash cause are recorded.

---

## Phase 3 — UI & Polish ✅

**Goal:** A game that *feels* like Tron-meets-htop.

### 3.1 Theme & layout
- [x] Color palette (deep navy/black + neon cyan/green/magenta).
- [x] Glassmorphism-style side panel.
- [x] Custom monospace font (e.g. JetBrains Mono / Fira Code).

### 3.2 HUD
- [x] RAM bar (animated, color shifts when low).
- [x] CPU meter rendered as a live sine-wave (`math.sin`) on a small canvas.
- [x] Depth/sector indicator.
- [x] Mini-map (optional).

### 3.3 Console log
- [x] Bottom-screen log feed: `[INFO] User moved to Sector 0x04. Trace detected!`
- [x] Severity levels: `INFO`, `WARN`, `ERROR`, `CRIT`, color-coded.
- [x] Ring-buffer of last N messages.

### 3.4 Fog of War
- [x] Visibility radius around player.
- [x] Explored-but-not-visible tiles dimmed.
- [x] `ScanBoost` item temporarily extends radius.

### 3.5 Juice
- [x] Screen shake on damage / crash.
- [x] Particle effects for hits, explosions, item pickups.
- [x] SFX (movement blip, attack, explosion, crash jingle).
- [x] Optional chiptune background loop.

**Exit criteria:** Looks and feels distinctive; new players can grasp the HUD without explanation.

---

## Phase 4 — Persistence, Meta-progression & Final Integration ✅

**Goal:** Replay incentive and a polished release.

### 4.1 Leaderboard
- [x] `HighScores` screen (top N by `total_score`, then `depth_reached`).
- [x] Filter by date / player.

### 4.2 Run history
- [x] `runs` table: seed, depth, score, crash cause, duration, timestamp.
- [x] Stats screen: deaths per enemy type, average depth, best run.

### 4.3 Meta-progression (optional but recommended)
- [x] `bits` currency persisted across runs.
- [x] `upgrades` table: `id`, `key`, `level`, `cost`.
- [x] Shop screen between runs (e.g. `+10 RAM`, `+1 starting cycle`, `wider scan`).

### 4.4 Launcher / menus
- [x] Main menu: New Run, High Scores, Shop, Settings, Quit.
- [x] Settings: volume, key bindings, difficulty.

### 4.5 Quality & release
- [x] Test coverage > 70% on `world/`, `entities/`, `systems/`, `data/`.
- [x] Performance pass (target 60 FPS at 1080p).
- [x] Package with `pyinstaller` for macOS / Windows / Linux.
- [x] `CHANGELOG.md` updated; tag `v1.0.0`.

**Exit criteria:** A first-time player can install, play, lose, and see their name on the leaderboard.

---

## Stretch Goals

- [ ] Daily seed challenge.
- [ ] Replay system (record input + seed, replay deterministically).
- [ ] Modding hooks: load enemy / item definitions from JSON.
- [ ] Online leaderboard (small Flask/FastAPI backend).
- [ ] Accessibility: colorblind palette, key remapping, scalable UI.
