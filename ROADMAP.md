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

## Phase 7 — Narrative & Identity: "init(0)" 📖 ✅

**Goal:** Give the player a *who*, a *why*, and a *face*. Today the protagonist is a yellow dot with no story; we will turn the run into a journey through a dying machine, with a clear protagonist, antagonist, and world rules. The narrative is the spine that every later phase (enemies, bosses, distros) will hang dialogue and flavor on.

### 7.1 Story bible
- [x] Author `docs/LORE.md`: world premise (a sentient kernel infected by a rogue process), factions, tone (cyber-noir / sysadmin folklore), do/don't list for writers.
- [x] Define the protagonist `init(0)` — a recovery process spawned by a panicking kernel; goals: reach `/proc/1`, purge the leak, restore uptime.
- [x] Define the antagonist `THE_LEAK` — corrupted PID 0 fragment that grows with every wasted cycle.
- [x] Define 5 supporting NPCs (vendor daemons in the shop, mentors in the tutorial, etc.).

### 7.2 Protagonist redesign
- [x] Replace yellow circle with a 16×16 / 24×24 sprite: stylized "process glyph" (pulsing diamond core + 4 rotating I/O fins), distinct silhouette readable at a glance.
- [x] Idle animation (4 frames), walk animation (4 frames per direction), hit-flash, death dissolve.
- [x] Player palette swaps unlocked via meta-progression (1 default + 3 unlockable skins, each tied to a distro from Phase 11).
- [x] Tiny name-tag floats above the sprite showing the chosen handle (entered at run start).

### 7.3 Enemy redesign pass (visual layer only — combat behavior unchanged)
- [x] Each malware type gets a unique sprite + idle/attack animation that *telegraphs* its role:
  - `SyntaxError` — flickering red `;` glyph, jittery patrol idle.
  - `LogicBomb` — pulsing amber circle with growing fuse-ring as it nears the player.
  - `ZombieProcess` — desaturated grey sprite that goes corrupted-magenta after revive.
  - `KernelPanic` — large 2×2 BSOD-style block with glitching text overlay.
  - `SegFault` — half-rendered sprite that snaps to a new position on damage.
- [x] Death animations distinct per type (shatter, fizzle, BSOD-collapse, address-fault scatter).

### 7.4 Story delivery in-run
- [x] `Lore` table (id, key, title, body, unlock_condition).
- [x] Story beats unlocked by milestones: first kill, first boss, first distro completion, first death cause variety, sector 5/10/15.
- [x] Between-sector "Stack Trace" interstitial: a 1–3 line monologue from `init(0)` or a captured log line from `THE_LEAK`.
- [x] Codex screen in main menu (`Lore`) showing all unlocked entries; locked entries shown as `???`.

### 7.5 Cinematic intro & ending
- [x] 8–12 frame ASCII/pixel intro played on first launch (after Phase 6 first-boot detect): boot sequence → kernel panic → `init(0)` spawned.
- [x] "True ending" cutscene triggered only by a successful run (per Phase 11 success criteria).
- [x] Skippable with **ESC**; auto-skip after first viewing (toggle in Settings).

### 7.6 Naming & flavor unification
- [x] Audit every user-facing string against `docs/LORE.md`; replace generic copy ("You died") with in-world equivalents ("`init(0)` dumped core — signal: `<crash_cause>`").
- [x] Console log gets named voices: `[KERNEL]`, `[init]`, `[THE_LEAK]`, `[VENDOR]`.

**Exit criteria:** A new player understands within 60 seconds that they are a recovery process fighting a memory leak through a dying kernel, and the protagonist is visually distinct from every enemy on screen.

---

## Phase 8 — Enemy Variety, Recognition & Adaptive Music 🎼 ✅

**Goal:** Replace "two minions, two bosses" with a roster that has identity, variants, and tactical fingerprints — and make the soundtrack react to what is on screen.

### 8.1 Enemy roster expansion
- [x] Promote `Malware` to a full registry (`entities/malware_registry.py`) keyed by `archetype × variant`.
- [x] **Archetypes (role classes):**
  - `Skirmisher` — fast, low HP, swarm pressure (current `SyntaxError`).
  - `Bruiser` — slow, high HP, melee burst.
  - `Sapper` — kamikaze / detonator (current `LogicBomb`).
  - `Caster` — ranged tile-targeted attacks (`StackOverflow`: pushes player back, `NullPointer`: skips a player turn on hit).
  - `Stalker` — invisible until adjacent (`RaceCondition`).
  - `Support` — buffs nearby enemies (`Daemonizer`: gives allies +1 damage).
  - `Revenant` — revives or splits (current `ZombieProcess`, plus `ForkBomb`: spawns 2 minions on death).
- [x] **Variants per archetype** (each archetype ships 2–3 variants that tweak stats/behavior, not new code paths): e.g. `SyntaxError` → `RuntimeError` (faster), `IndexError` (drops more loot).
- [x] Spawn tables driven by sector depth + active distro (Phase 11).

### 8.2 Power affixes (the "modifier" layer)
- [x] Any enemy can roll up to 2 affixes from a shared pool, applied at spawn:
  - `Cached` — +25% HP.
  - `Overclocked` — +1 speed.
  - `Encrypted` — immune to one damage type until decrypted by a `grep` program.
  - `Networked` — heals nearby allies for 1/turn.
  - `Volatile` — explodes for half-damage on death.
- [x] Affixes render as small icon badges over the sprite + colored outline.
- [x] Affix score-multiplier: tougher mobs award more `bits` and combo points.

### 8.3 Damage types & resistances
- [x] Introduce 3 damage types: `kinetic` (melee bumps), `signal` (most programs), `logic` (special items).
- [x] Each enemy has a resistance/weakness profile (e.g. `LogicBomb` weak to `signal`, resistant to `kinetic`).
- [x] Combat resolution multiplies damage by resistance factor (0.5× / 1× / 1.5× / 2×); floating damage numbers color-code by effectiveness.

### 8.4 Scout / "Recognition" mechanic
- [x] New stat per enemy *species*: `intel_level` (0–3), persisted in a new `enemy_intel` table (`species_key`, `kills`, `damage_dealt_to`, `intel_level`, `weakness_revealed`).
- [x] Intel earned by: killing N of that species, surviving its attack, or using `tcpdump` daemon / `grep` program while in FoV.
- [x] Intel tiers reveal progressively richer info on hover/inspect:
  - **0** — name + sprite only.
  - **1** — HP, damage, archetype.
  - **2** — resistances/weaknesses, AI summary.
  - **3** — recommended counter-program, lore blurb, all affix interactions.
- [x] **Bestiary** screen in main menu listing every species with current intel level and personal-best damage record per program.
- [x] In-run **Inspect mode** (`I` key): cursor selects any visible enemy → opens an Intel popover.

### 8.5 Player-vs-enemy damage analytics
- [x] Per-run tracking: which `Program` / weapon dealt the most damage to which species (stored in `run_combat_log`).
- [x] Post-run summary screen highlights top matchups ("Your `kill -9` deleted 7 `LogicBomb`s — favorite tool: signal").
- [x] Aggregate ("lifetime") stats roll up into the Bestiary so players can read their own meta.

### 8.6 Adaptive music engine
- [x] Refactor `ui/sfx.py` (or new `ui/music.py`) into a **layered stem player**: each track is composed of stems (`bed`, `melody`, `tension`, `boss`) loaded as separate `pygame.mixer.Channel`s with synced loop length.
- [x] Each enemy archetype declares an associated stem motif (e.g. `Sapper` → "tension_lead", `Stalker` → "tension_pad", `Caster` → "melody_arp").
- [x] **Mixer rules:**
  - No enemies in FoV → only `bed` audible.
  - 1 enemy in FoV → fade in that archetype's stem at 60% gain.
  - ≥2 archetypes → blend stems; stems are written in the same key/BPM so they layer cleanly.
  - Boss enters FoV → crossfade into boss-exclusive `boss` stem; non-boss stems duck to 30%.
- [x] Crossfades are time-based (250–500 ms) and triggered on visibility changes, not every turn.
- [x] **Asset spec doc** `docs/AUDIO_STEMS.md` describing required stems (key, BPM, length, file naming) so a composer can deliver matching loops.
- [x] "Reduce motion" option also caps stem layer count for sensory-sensitive players.

### 8.7 Tests
- [x] Unit-test the stem mixer using a fake mixer interface (no real audio): assert correct stems active for a given visible-enemy set.
- [x] Unit-test resistance math, intel-tier transitions, affix HP rolls.

**Exit criteria:** A run with three enemy archetypes on screen plays a richer track than a run with one; opening the Bestiary tells the player exactly which program melts which mob; affix-rolled enemies feel meaningfully different to fight.

---

## Phase 9 — Boss Spectacle & Pantheon 👑 ✅

**Goal:** Bosses become *events*. Each fight has its own arena, music swap, multi-phase script, and signature mechanic the player has to *learn*.

### 9.1 Boss framework
- [x] `BossEncounter` class encapsulating: arena dimensions, intro cinematic, phase script, music stem, defeat reward, lore beat.
- [x] Boss arenas are dedicated pre-authored sub-grids (not pure proc-gen) loaded from `data/boss_arenas/*.json`.
- [x] Boss intro: camera pans, screen letterboxes, title card ("`KERNEL_PANIC.exe` — pid 1"), HP bar slides up across the top of the screen.
- [x] Boss HP bar: large, segmented per phase, with phase names.

### 9.2 New boss roster (target: 6 total)
Existing: `KernelPanic`, `SegFault`. Add at least 4 more:
- [x] `THE_LEAK` (final boss, Phase 7 antagonist): grows in size each turn it isn't damaged; arena tiles slowly corrupt.
- [x] `DeadlockTwins` — paired bosses; damaging one heals the other unless attacked on the same turn.
- [x] `RootkitHydra` — single body with 3 heads; killing a head spawns 2 unless killed by a `signal` program.
- [x] `BufferOverflow` — fills the arena with projectile data-blocks every 3 turns; player must hide behind `SYSTEM_DATA` cover.
- [x] (stretch) `ZeroDay` — secret boss unlocked after collecting all `Lore` codex entries.

### 9.3 Phase scripting
- [x] Each boss has 2–4 explicit phases with HP thresholds, an entry telegraph, and a unique attack pattern.
- [x] Phase transitions trigger: screen flash, console-log warning, music stem swap inside the boss layer.
- [x] Boss patterns are deterministic given the run seed (so they're learnable, not random).

### 9.4 Audio for bosses
- [x] Each boss owns a dedicated track (not a stem) that *replaces* the adaptive bed for the duration of the fight, then crossfades back on victory/defeat.
- [x] Phase-specific overlay stems (e.g. `THE_LEAK` adds a distortion layer in phase 3).

### 9.5 Rewards & progression hooks
- [x] First kill of each boss unlocks: a Daemon, a Lore entry, and a permanent Bestiary trophy.
- [x] Subsequent kills award scaling `bits` + a chance at a unique Patch card.
- [x] Boss kill telemetry feeds the success criteria for distros (Phase 11).

### 9.6 Tests
- [x] Snapshot tests on phase scripts (given seed S and player actions A, boss reaches phase X at turn Y).
- [x] Audio-mixer test confirming boss track replaces bed during encounter.

**Exit criteria:** Encountering any boss triggers a recognizable event — different arena, different music, telegraphed phases — and beating one for the first time feels like a milestone the player wants to brag about.

---

## Phase 10 — Interactive Tutorial Range: "/dev/sandbox" 🎯 ✅

**Goal:** Replace the text-only tutorial with a hands-on training facility where the player is *taught* every system, then *let loose* to experiment without consequences.

### 10.1 The Range
- [x] New game state `TUTORIAL_RANGE` with its own scene; reachable from main menu (`Training`) and auto-opened on first launch (replaces Phase 6.1 first-boot tutorial).
- [x] Pre-authored arena `data/tutorial/range.json`: clearly zoned rooms (Movement Bay, Combat Pit, Item Lab, Program Foundry, Daemon Lounge, Boss Simulator).
- [x] No death, no run timer, no score; closing returns to menu with no DB writes.

### 10.2 Guided lessons (curriculum)
Each lesson is a short scripted scene with goals that auto-complete when the player demonstrates the skill:
- [x] **L1 Boot** — movement, FoV, console log.
- [x] **L2 Combat** — bump-attack, damage numbers, RAM bar.
- [x] **L3 Items** — pickup, cache, `use_item`.
- [x] **L4 Programs** — slot bar, hotkeys, cooldowns; one lesson per Program type.
- [x] **L5 Daemons** — equip slots, synergy tags, swap during combat.
- [x] **L6 Patches** — pick a Patch, see HUD chip, observe stat change.
- [x] **L7 Recognition** — Inspect mode, Bestiary, weakness exploitation (Phase 8).
- [x] **L8 Boss Drill** — fight a "training dummy" boss with 1 HP per phase to see the script.
- [x] Lessons can be replayed individually from a Curriculum menu.

### 10.3 The Polygon (free-play sandbox)
- [x] After lessons (or skippable from the menu), the player drops into the Range with a debug toolbar:
  - Spawn any enemy / affix / boss at cursor.
  - Grant any Item / Program / Daemon / Patch.
  - Set RAM, cycles, depth.
  - Toggle FoV, god mode, infinite cycles.
- [x] Toolbar is a transparent overlay (`~` key) with searchable lists.
- [x] Range state never touches `runs`, `scores`, or `bits`.

### 10.4 Hint system
- [x] Every Program / Daemon / Item has an `explain()` string used both in the Range and as a tooltip elsewhere (single source of truth).
- [x] Lesson scripts call `explain()` so copy never drifts from runtime behavior.
- [x] "Show me" button next to each entry triggers a 3-second auto-played demo (scripted player actions).

### 10.5 Tests
- [x] Lesson completion conditions tested with scripted input streams.
- [x] Range smoke test: spawn one of every entity, confirm no crash, confirm DB is untouched.

**Exit criteria:** A new player can finish the curriculum, then open the polygon and answer "what does daemon X do?" by trying it — without ever reading external docs or risking a real run.

---

## Phase 11 — Distros & Structured Runs 💿 ✅

**Goal:** Replace "click New Run → drop in" with a *Balatro-style* meta loop: choose a **Distro** (themed starting build), play a structured ladder of objectives, hit a success bar, and only then advance meta-progression. Skipping objectives is allowed but costly.

> **Naming.** A "deck" in our world is a **Distro** (Linux distro / OS image): a curated starting bundle of Programs, Daemons, starting stats, and a unique mechanic. The protagonist boots into the chosen Distro at the start of the run.

### 11.1 Run structure: Releases, Milestones, Sectors
- [x] A run is composed of **8 Releases** (≈ Balatro antes).
- [x] Each Release contains **3 Milestones** (Sector_A / Sector_B / Boss). Boss is mandatory; A and B are *Skippable*.
- [x] Each Milestone has a target score the player must hit before exiting the sector; failing the target ends the run.
- [x] Target score grows per Release on a tunable curve (`base × growth^release`).

### 11.2 Skip mechanic
- [x] Player may **skip** a non-boss Milestone from a between-sector screen.
- [x] Skipping awards a **Skip Tag** (a one-time consumable modifier: e.g. "Next shop is free", "+1 Daemon slot for next sector", "Double bits next milestone").
- [x] Skipping forfeits that Milestone's score, shop, and loot — creating real opportunity cost for builds that depend on shop access.
- [x] HUD visualizes the Release ladder (3 milestones × 8 releases) with current position, skip/play state, and target score.

### 11.3 Vendor (between-Milestone shop)
- [x] After every *played* Milestone, open the **Vendor** screen (in-run, not the meta shop).
- [x] Stock: Programs, Daemons, Patches, single-use Consumables, Reroll button, Skip Tag exchange.
- [x] Currency: in-run `bits`; carry-over to meta `bits` only on successful run.
- [x] Vendor stock biased by current Distro tags (a `signal`-themed Distro is more likely to roll `signal` Daemons).

### 11.4 Distros (the "decks")
- [x] `distros` table (`key`, `name`, `unlock_condition`, `unlocked_at`, `description`).
- [x] Distro selection screen replaces the current "New Run" button: card-like grid of Distros with stats preview, locked Distros shown as `???` with their unlock hint.
- [x] **Sequential unlocks**: each Distro unlocks the next only after a *successful run* (see 11.6).
- [x] **Starter Distros** (target: 6, sequentially unlocked):
  1. **`Vanilla`** — baseline starting kit; no bonuses, no penalties.
  2. **`Minimal`** — fewer cycles, but +50% bits from kills.
  3. **`Hardened`** — +20 starting RAM, programs cost +1 cycle.
  4. **`Realtime`** — enemies always act first, but player gets +1 free move every 5 turns.
  5. **`Bleeding-Edge`** — start with 2 random Daemons but RAM regen disabled.
  6. **`Recovery`** — built around `init(0)` lore; starts with the `cron` daemon and a unique Program `restore --from-snapshot`.
- [x] Each Distro defines: starting Programs/Daemons, starting stats, vendor weighting, one *signature* unique mechanic (its "joker").

### 11.5 New Run flow
- [x] `New Run` opens **Distro Select** → **Seed (random or daily)** → **Confirm Boot** → run starts.
- [x] Selected Distro is displayed in the HUD's Run Info card and persisted to the `runs` row.

### 11.6 Run success criteria & meta gating
- [x] A run is **successful** iff the player clears all 8 Releases (Milestone 8.3 boss defeated) without crashing.
- [x] **Meta-progression rules (strict):**
  - Failed run → no `bits` carried to meta shop, no Distro unlocks, no skin unlocks. Run is still recorded in `runs` for stats.
  - Successful run → meta `bits` granted, next Distro in the chain unlocks, lore entry awarded, optional cosmetic unlock.
- [x] Existing meta shop (Phase 4.3) continues to work but only receives currency from successful runs.
- [x] One-time migration: existing `bits` are preserved (no rug-pull), but documented in `CHANGELOG.md`.

### 11.7 UI for the loop
- [x] **Release ladder** widget on the run-info card.
- [x] **Milestone results** screen between sectors: shows score vs. target, bits earned, lore beat, and the Skip / Continue choice.
- [x] **Run summary** screen on win or loss: full ladder recap, biggest combo, best matchup (Phase 8.5), Distro unlocked, lore entries unlocked.

### 11.8 Tests
- [x] Score-target curve unit tests.
- [x] Skip mechanic: skipping a milestone forfeits its score/shop and grants a Skip Tag.
- [x] Meta gating: failed run → meta `bits` delta == 0 and no Distro unlock side effects; successful run → exactly one new Distro unlocked.
- [x] Distro registry test: every Distro defines required fields and references valid Programs/Daemons.

### 11.9 Documentation
- [x] Update `HOWTOPLAY.md` with Distro selection, Release ladder, skip mechanics, success criteria.
- [x] Update `docs/PRD_AND_ARCH.md` with the new tables (`distros`, `release_progress`, optional `skip_tags`) and the meta-gating rule.

**Exit criteria:** Clicking "New Run" never drops the player straight into a sector — they pick a Distro first; the run is structured into a visible 8×3 ladder; meta-progression only advances on a successful run; at least 6 Distros exist and unlock sequentially.

---

## Phase 12 — Player Experience Polish: "uptime++" 🪄

**Goal:** Tighten everything the player actually sees and hears so the game feels like a finished product, not a tech demo. Driven by playtest feedback (overlapping HUD, missing in-run guidance, flat boss fights, dry menus, untranslated control glyphs, ungenerous quit flow).

> Convention: every checkbox is a single PR. Each PR keeps `python -m kernelquest.main` runnable and the `ruff/black/mypy/pytest` gate green.

### 12.1 Tutorial parity with current branch
- [ ] Audit `data/tutorial/range.json` rooms vs. shipped systems; remove/replace any room that references a feature not yet in this branch.
- [ ] Rewrite `world/tutorial_range.py::CURRICULUM` so each lesson references only Programs/Daemons/Items/Affixes that exist in the current registries (validated by a unit test that imports both registries and asserts every lesson key resolves).
- [ ] Tutorial dummy enemies use the same `malware_registry` species the player will fight in real runs (no bespoke `TutorialDummy` placeholder).
- [ ] Lesson copy is sourced via `Program.explain()` / `Daemon.explain()` / `Item.explain()` — drift impossible.
- [ ] Test: `pytest tests/test_phase10.py` extended with "every lesson references a real entity" assertion.

### 12.2 Onboarding via LORE (combat / cycle / RAM literacy)
- [ ] New `Lore` codex entries: `combat_basics`, `cpu_cycles_explained`, `ram_explained`, `cache_explained`, `program_slots`, `daemon_synergy`. Body text written in `init(0)` / `[KERNEL]` voice.
- [ ] First-run flow: after intro cinematic, before tutorial range, surface a 3-card "Boot Briefing" (combat, cycles, RAM) using the same Stack Trace renderer.
- [ ] Same entries unlocked permanently in Codex on first view.
- [ ] Tutorial lessons cross-link to their lore entry ("Read more: `man combat`").

### 12.3 i18n: keep OS terminology in English
- [ ] Add a `glossary` set to `ui/i18n.py` listing terms that must NOT be translated: `RAM`, `CPU`, `cycle(s)`, `sector`, `cache`, `daemon`, `program`, `process`, `kernel`, `run`, `bit(s)`, `boot`, `crash`, `patch`, `distro`, `vendor`, `seed`, `intel`, `affix`, `pid`, `FoV`, `init(0)`.
- [ ] Sweep `ui/i18n.py` Turkish strings: replace any translated occurrences of the glossary terms back to their English forms (e.g. "Çalıştırma" → "Run", "Bellek" → "RAM").
- [ ] Add a unit test that loads each locale and asserts no glossary term appears translated.
- [ ] Rename main-menu label `menu.new_run` Turkish copy from "Yeni Çalıştırma" → "Yeni Run".

### 12.4 RUN HUD: layout fix + new readouts
- [ ] Fix overlap: move bottom action hints ("move / attack…") into a dedicated `BottomBar` widget that reserves vertical space; viewport recomputes available height accordingly (no more text drawn over tiles).
- [ ] Add **damage-dealt-this-turn** popover on the run-info card (also visible as floating number when > 0).
- [ ] Add **enemy HP bar** above each visible enemy sprite (3-segment glassmorphism style, hidden when full).
- [ ] Perk-gated AoE preview: when player owns the new `tcpdump+` Daemon (upgrade of existing `tcpdump`), show telegraphed AoE tiles for `Sapper`/`Caster` archetypes (tinted overlay, low alpha).
- [ ] Tooltip / hover layer respects the new BottomBar reservation — no overlap with mini-help row.
- [ ] Tests: snapshot test of HUD layout rectangles asserting non-overlap.

### 12.5 Main-menu redesign: navigable "Boot Map"
- [ ] New state `MENU_MAP`: an interactive scene where `init(0)` walks on a small grid between labeled "kiosks" (Run, Daily, Help, Codex, Stats, Settings, Quit). Bumping a kiosk activates its panel.
- [ ] Reuse player sprite + idle/walk animations from Phase 7.2.
- [ ] Old keyboard menu (`MenuStateHandler`) kept as a fallback (toggle in Settings → "Classic menu").
- [ ] Tests: `test_menu_map.py` smoke-tests kiosk activation per direction, asserts no DB writes.

### 12.6 Menu consolidation into terminal tabs
- [ ] New `TabbedPanel` UI primitive in `ui/renderer.py`: top tab strip styled like a terminal multiplexer (zsh-tab look), `TAB`/`SHIFT+TAB` cycles, `1..n` jumps directly.
- [ ] Group A — **Manual**: tabs `Tutorial`, `How to Play`, `Codex`. Single state `STATE_MANUAL`. Old states (`HOWTOPLAY`, `CODEX`, `TUTORIAL` entrypoint) route through it.
- [ ] Group B — **Launch**: tabs `New Run`, `Daily Run`. Single state `STATE_LAUNCH`. Replaces direct hops from menu.
- [ ] Group C — **Records**: tabs `High Scores`, `Daily Board`, `Stats`, `Bestiary`. Single state `STATE_RECORDS`.
- [ ] Update menu kiosks (12.5) and classic menu to point at the 3 grouped entries.
- [ ] Tests: tab cycling, deep-link (open at specific tab), back-key behavior.

### 12.7 Sector ladder visibility (Balatro 8×3)
- [ ] Promote `RunProgress` ladder widget from "small chip" to a persistent vertical strip on the run-info card: 8 releases × 3 milestones = 24 dots, current dot highlighted, bosses marked with a skull glyph.
- [ ] Hovering / pressing **L** toggles a fullscreen overlay version with target scores per milestone.
- [ ] Visual style synced with terminal-tab theme.

### 12.8 Inter-sector cinematic transition
- [ ] New `CinematicPlayer` script: 1.2 s "descent" animation between milestones — terminal-style `cd /sector/0xNN/` typed line, screen wipe, sub-bass thump from music layer, ladder dot tweens.
- [ ] Skippable with **SPACE**; auto-skip on second view per run.
- [ ] Reused by all sector→sector transitions and by the entry to a Boss milestone (longer variant).
- [ ] Tests: state-transition snapshot + skip behavior.

### 12.9 Boss phase-transition spectacle
- [ ] On every phase boundary in `BossEncounter`: hard screen flash, brief letterbox, 0.4 s music stem cut → re-enter with new phase stem, console `[KERNEL] !!! phase shift !!!` line, boss sprite glitches/recolors.
- [ ] Each existing boss gets an authored `phase_intro` line + arena-mutation hook (e.g. `BufferOverflow` adds extra cover blocks at phase 2).
- [ ] Tests: `test_phase9` extended — phase boundary fires exactly one transition event.

### 12.10 Vendor visual redesign
- [ ] Reskin Vendor as a CRT shop terminal: ASCII storefront banner, three "shelf" rows (Programs / Daemons / Patches+Consumables), price tags using bit-style glyphs.
- [ ] Item cards get hover-lift, rarity glow, and an inline `explain()` panel.
- [ ] Reroll button styled as a `kill -HUP vendor` command.
- [ ] Vendor NPC portrait (tied to Phase 7 supporting NPCs) shown top-left with one rotating flavor line per visit.
- [ ] Layout tests asserting no overlap with HUD reservations.

### 12.11 Visualized LORE / dialogue scenes
- [ ] New renderer `ui/dialogue.py`: portrait + name plate + typewriter dialogue box, configurable left/right placement.
- [ ] Author 5 scripted scenes for existing lore beats (intro, first kill, first boss, first distro success, ending).
- [ ] Stack Trace interstitial keeps its terse style; full scenes only on milestones.
- [ ] Portraits are stylized 48×48 pixel art (init(0), THE_LEAK, KERNEL, VENDOR, MENTOR) — drawn programmatically for now; sprite slots reserved for future hand-drawn art.
- [ ] Tests: dialogue script playback, skip behavior.

### 12.12 Arrow-key glyph rendering fix
- [ ] Add four glyph constants (`↑↓←→`) to the embedded font OR fall back to ASCII `[Up]/[Down]/[Left]/[Right]` when missing.
- [ ] Replace every use site (mini help bar, tutorial copy, dialogues, vendor instructions) with a `key_glyph()` helper that picks glyph vs. ASCII based on font support.
- [ ] Test: render the help bar headlessly and assert no `tofu` (`?` block) codepoints.

### 12.13 Self-quit run reward
- [ ] In `GameEngine._end_run()`: if the player ended via the in-game pause menu's "Abort run" (not crash), grant **partial** meta `bits` proportional to current run score (cap 25%), award no Distro unlock and no lore.
- [ ] Console log clearly distinguishes `[init] graceful shutdown` from `[init] dumped core`.
- [ ] Tests: aborted run writes a `runs` row with status=`aborted`, `bits_delta > 0`, no Distro side-effects.

### 12.14 Boss dev menu (both routes)
- [ ] Hidden main-menu kiosk (or classic-menu row) shown only when env var `KQ_DEV=1`: opens a Boss Test Range that lets you pick any boss and fight it in its arena with full kit.
- [ ] Tutorial Range Polygon overlay (`~`) gets a dedicated `Boss` kind tab with all 6+ bosses; "Show me" auto-plays a 5-second scripted demo of phase 1 → phase 2 transition.
- [ ] Boss Test Range never writes to `runs`/`scores`/`bits`.
- [ ] Tests: env-gated kiosk visibility, Polygon boss spawn smoke test.

### 12.15 Original menu music (synthesized in repo)
- [ ] New module `ui/menu_theme.py`: generates a "safe bed" looped chiptune track procedurally with `numpy` + `pygame.sndarray` (saw-pad chord progression in A minor, 80 BPM, 4-bar loop, soft sub-bass, optional shimmer pad). Output cached to `assets/audio/menu_safe.ogg` on first launch.
- [ ] Plays on `MENU` / `MENU_MAP` / tabbed-manual / launch / records states; ducks to 30% during quit-confirm modal.
- [ ] Replaces the current adaptive bed only on menu states; in-run music untouched.
- [ ] Test: audio module imports headlessly without opening a real device; cache file written exactly once.

### 12.16 Documentation & changelog
- [ ] Update `HOWTOPLAY.md` to reflect tabbed menus, sector ladder, abort reward, dev menu.
- [ ] `CHANGELOG.md` entry per merged PR (Conventional-Commits style).

**Exit criteria:** A new tester opening the game on this branch reads zero out-of-game docs, navigates the boot-map menu, completes a refreshed tutorial that teaches RAM/cycles/combat in lore voice, plays a run with a non-overlapping HUD that shows enemy HP and damage dealt, watches a sector ladder progress with proper transitions, fights a boss whose phase changes feel like *events*, and — even on a self-aborted run — comes back to a menu that already offers them a couple of meta `bits` to spend.

---

## Stretch Goals

- [ ] Replay system (record input + seed, replay deterministically).
- [ ] Modding hooks: load enemy / item / daemon definitions from JSON.
- [ ] Online leaderboard (small Flask/FastAPI backend).
- [ ] Steam Workshop-style Daemon sharing.
- [ ] Mobile / touch port.
