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

## Phase 5 — Mechanics Expansion: "The Juice Update" 🎰

**Goal:** Move beyond plain bump-combat into a snappier, more replayable loop. Inspired by *Balatro*-style synergies, snappy feedback, and the joy of stacking small modifiers.

### 5.1 Data hygiene (carry-over fix)
- [x] One-time migration: backfill `runs` from any pre-Phase-4 `scores` rows so Stats screen matches High Scores.
- [x] `RunRepository.best()` falls back to `ScoreRepository.top_n(1)` when `runs` is empty.

### 5.2 Programs (deck of active abilities)
- [x] New entity: `Program` — a card-like usable with cooldown, charges, and a short flavor name (`fork()`, `kill -9`, `sudo`, `grep`, `nice`, `nohup`, `chmod +x`).
- [x] `programs` table + `ProgramRepository` (id, key, level, slot).
- [x] Loadout slot bar (3 active programs, hotkeys **Q / E / R**).
- [x] Effects examples:
  - `fork()` — spawn a 1-turn decoy clone that draws aggro.
  - `kill -9` — instakill a non-boss adjacent enemy, large cycle cost.
  - `sudo` — next attack deals 3× damage.
  - `grep` — reveal whole sector for 1 turn.
  - `nice` — skip enemy turn for 2 turns.

### 5.3 Daemons (passive modifiers — the "Joker" slot)
- [x] New entity: `Daemon` — passive process that buffs the player while equipped.
- [x] `daemons` table; up to **5** equipped slots, drag-and-drop reorder.
- [x] Synergy tags: `arithmetic`, `io`, `network`, `memory`, `signal` — daemons that share tags trigger combo bonuses.
- [x] Examples:
  - `cron` — every 10 turns, restore 5 RAM.
  - `swapd` — convert overflow RAM into bonus score on pickup.
  - `oom-killer` — when RAM < 20%, deal AoE damage.
  - `tcpdump` — see enemy intent arrows.
  - `niced` — +1 cycle per turn while no enemy is in FoV.

### 5.4 Combo / chain scoring
- [x] Score formula: `base × multiplier`. Multiplier grows when consecutive turns chain (kill → pickup → kill).
- [x] Big visible multiplier widget (Balatro-style: `× 4.20`) that pops/scales on increase.
- [x] Chain breaks on damage taken or 3+ idle turns.

### 5.5 Run-modifier "Patch Notes"
- [x] Between sectors, offer 3 random **Patch** cards (pick one): `+10% damage`, `enemies -1 HP but +1 speed`, `double item drops, half RAM regen`, etc.
- [x] `patches` table; selected patches persist for the run, render as small chips in the HUD.

### 5.6 Boss & elite variety
- [x] Add elite mob type: `ZombieProcess` (revives once after death).
- [x] Add second boss: `SegFault` — teleports, splits the grid into two halves.
- [x] Each boss drops a guaranteed Daemon.

### 5.7 Daily seed challenge (promoted from stretch goals)
- [x] Date-based seed; same dungeon for everyone that day.
- [x] Local-only daily leaderboard table.

**Exit criteria:** A run feels different every time because of the daemons + patches stacked on it; the multiplier widget makes a successful chain feel earned.

---

## Phase 6 — Onboarding, UI Polish & Accessibility 🎨

**Goal:** Make Kernel Quest legible, juicy, and welcoming on first launch. Lean into the Balatro/CRT visual language: chunky readable type, subtle bloom, scanlines, satisfying micro-animations.

### 6.1 Tutorial / "First Boot"
- [x] Detect first-run (no rows in `scores`) and route into a guided **Boot Sequence** tutorial sector instead of the menu.
- [x] Step-by-step prompts: "Press **WASD** to move", "Bump the `SyntaxError` to attack", "Press **1** to use a `GarbageCollector`", "Press **Q** to fire `kill -9`".
- [x] **Help** menu entry that re-opens the tutorial at any time.
- [x] In-game `?` overlay: contextual cheat-sheet of current controls.

### 6.2 Visual identity refresh (Balatro-inspired)
- [x] CRT post-process shader (scanlines, slight curvature, chromatic aberration) — toggle in Settings.
- [ ] Chunkier "card" components for menus (drop shadow, 4 px border, hover lift animation).
- [ ] Animated tile transitions: items wobble, enemies breathe, player has idle animation.
- [x] Number-pop particles on damage / score gain (Balatro-style floating digits).
- [ ] Smooth interpolated camera (lerp to player position, screen-shake on crit).

### 6.3 HUD pass
- [ ] Side panel becomes a real "Run Info" card: seed, sector, depth, multiplier, equipped daemons.
- [ ] Tooltips on every HUD element (hover any item / daemon → show full description).
- [x] Big readable score readout with comma separators and tween animation.
- [x] Persistent mini help-bar at the bottom showing the 4–5 most relevant keybinds for the current state.

### 6.4 Themes
- [x] Theme registry with 4 starter palettes:
  - **Kernel** (default neon cyan/magenta).
  - **Phosphor Green** (classic terminal).
  - **Amber CRT** (vintage monochrome).
  - **High Contrast** (accessibility).
- [x] Settings → Theme picker with live preview.
- [x] Persist theme choice in `meta` table.

### 6.5 Display & input options
- [x] **Fullscreen toggle** (Settings + global **F11** shortcut).
- [ ] Resolution picker: 1280×720 / 1920×1080 / Native.
- [x] UI scale slider (0.75× – 1.5×) for hi-DPI users.
- [ ] Full key remapping screen (write to `meta.keymap` JSON).
- [ ] Gamepad support (basic d-pad + 4 face buttons via `pygame.joystick`).

### 6.6 Audio polish
- [x] Separate **Music** and **SFX** volume sliders.
- [x] Mute toggle (**M** key, persisted).
- [x] Add 2–3 alternate chiptune tracks; pick at random per run.

### 6.7 Accessibility (promoted from stretch goals)
- [x] Colorblind palette (Deuteranopia / Protanopia / Tritanopia presets).
- [x] "Reduce motion" option (disables shake + particle pops).
- [x] Screen-reader-friendly text fallbacks for HUD numbers (logged via `ConsoleLog`).
- [x] Larger-text mode that bumps every font size +25%.

### 6.8 Documentation
- [x] In-repo `HOWTOPLAY.md` linked from main menu (`Help` opens it ingame as scrollable text).
- [ ] Animated GIFs in `README.md` showing each major mechanic.

**Exit criteria:** A complete newcomer can launch the game, finish the tutorial, switch to their preferred theme, go fullscreen, and complete a run without ever reading external docs.

---

## Stretch Goals

- [ ] Replay system (record input + seed, replay deterministically).
- [ ] Modding hooks: load enemy / item / daemon definitions from JSON.
- [ ] Online leaderboard (small Flask/FastAPI backend).
- [ ] Steam Workshop-style Daemon sharing.
- [ ] Mobile / touch port.
