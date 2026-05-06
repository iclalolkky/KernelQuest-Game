# Changelog

All notable changes to **Kernel Quest: The Memory Leak** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — Phase 12: Polish, Onboarding & UX

> **The "Quality-of-Life and Showmanship" release.** Phase 12 layers presentation polish, onboarding parity, and a kiosk-style main menu over the 3.0 narrative core. 351 → 356 tests.

### Added

- **HUD redesign (12.4).** Compact top-bar HUD with explicit `DAMAGE` readout, enemy HP bars rendered above hostile sprites, AoE telegraph overlays for Sapper (3×3) and Caster (axis 1–4 tiles), and a permanent bottom hint bar for the current input state.
- **Sector ladder (12.7).** New 8×3 ladder strip in the playing HUD shows release / milestone / boss columns with target scores; press `L` for the fullscreen ladder overlay.
- **Inter-sector cinematic (12.8).** Typewriter `cd /sector/0xNN/` descent with intro fade-in over 1200 ms before each sector transition.
- **Boss phase spectacle (12.9).** New `[KERNEL] !!! phase shift !!!` console banner, 0.45 s flash + letterbox + chroma tint via `render_phase_shift`, plus a 0.9 s glitch tail.
- **Tutorial parity (12.1).** `lesson_examples()` and `_LESSON_EXAMPLES` ship richer per-lesson example panels (items, programs, daemons, patches) inside the Tutorial Range.
- **Onboarding LORE (12.2).** Six new `man <topic>` codex entries (combat, cycles, RAM, cache, programs, daemons) gated by `onboarding_*` conditions.
- **Self-quit reward (12.13).** Manual exits (`SIGINT`) now grant 25% of the would-be meta-bit reward and surface a `[init] graceful shutdown` console line; full crashes still forfeit bits.
- **Boss dev menu (12.14).** Polygon overlay gains a dedicated **Boss** tab (`is_boss` species only). When `KQ_DEV=1` is set in the environment, a hidden **Boss Test Range** entry appears in the main menu.
- **Synthesized menu music (12.15).** New 4-bar A-minor / 80 BPM chiptune loop with sub-bass + saw-pad + arp lead, wired to the menu and quit-confirm states.
- **Tabbed menu hubs (12.6).** Top-level main menu collapses to **Launch / Manual / Records** plus Shop / Settings / Quit. Each hub is a tabbed sub-menu (`MANUAL_HUB`, `LAUNCH_HUB`, `RECORDS_HUB`) with TAB / 1..n / arrow navigation.
- **Boot Map main menu (12.5).** `init(0)` now walks between labelled kiosks across the bottom of the menu screen. Toggleable in Settings → "Main Menu Layout" → `Boot Map` / `Classic`.
- **Vendor reskin (12.10).** CRT-styled `/var/run/vendor` storefront with ASCII banner, three shelves grouped by kind, hover-lift cards, bit-style price tags, rarity glow, inline `explain()` panel, NPC portrait. Reroll renamed to `kill -HUP vendor`; leave renamed to `exit /var/run/vendor`.
- **Dialogue scenes (12.11).** New `ui/dialogue.py` module with five canonical scenes (`intro`, `first_kill`, `first_boss`, `first_distro_success`, `ending`) and a `UIManager.render_dialogue` helper that draws portrait + nameplate + typewriter body.
- **Arrow-key glyph fix (12.12).** All on-screen hints now use the `←/→/↑/↓` arrow glyphs instead of ASCII `UP/DN/LEFT/RIGHT`.
- **English-only OS terms (12.3).** i18n glossary guard ensures `RAM`, `CPU`, `cache`, `kernel`, `daemon`, `process`, `init(0)`, `sector` stay English in every locale.

### Changed

- Boot music switches from `safe` to the new `menu` loop on startup.
- Settings exposes a new `menu_layout` field (`map` / `classic`); persisted via `MetaRepository`.
- Top-level menu options are now resolved at runtime via `_menu_options()` so the dev `boss_test` entry can be inserted without touching call sites.

---

## [3.0.0] — 2026-05-05

> **The "Narrative + Distros + Bilingual" release.** Phases 7 through 11 land together: a full story arc with cinematic intro/ending, a 12-strong enemy roster with affixes and damage types, six bosses with scripted phases, an adaptive multi-stem music engine, an interactive tutorial range, six distros with structured Release → Milestone → Sector runs, a between-milestone vendor with skip-tag drops, English/Turkish localisation, and a top-to-bottom UI rework anchored by an animated character-driven main menu. Internally the engine has been refactored to the **State Pattern** (242 → 297 tests).

### Added — Phase 7: Narrative & Identity ("init(0)")

- **Story bible.** New `story_bible.md` defining the protagonist `init(0)`, the in-fiction OS (`/proc/legacy`), motivation, theme, and antagonist roster.
- **Protagonist redesign.** Player is now `init(0)` — recovery process. New player sprite (`ui/sprites.py::draw_player_sprite`) with palette variants (Kernel default, Phosphor, Amber, Mono) selectable in Settings; tile glyph replaced with an animated 3-frame sprite (idle bob + halo).
- **Enemy redesign (visual layer only).** Each species gets a unique sprite + animation cycle in `ui/sprites.py::draw_enemy_sprite` — `SyntaxError`, `LogicBomb`, `KernelPanic`, `SegFault`, `BufferOverflow`, `RootkitHydra`, `DeadlockTwin`, `TheLeak`, `ZeroDayBoss`, `ZombieProcess`. Combat behaviour is unchanged.
- **In-run lore.** New `lore_catalog.py` (`CATALOG`, `for_condition`) — short flavour blurbs surfaced via the in-game `ConsoleLog` on first-kill / first-pickup / first-descent / first-boss / first-crash beats. Persisted in the `lore_unlocks` table and replayable from the new **Codex** menu entry.
- **Cinematic intro & ending.** New `ui/cinematics.py::CinematicPlayer` plus `INTRO_FRAMES` / `ENDING_FRAMES` script blocks. First-launch automatically plays the intro; clearing the final boss plays the ending. Skippable with `Space` / `Esc`.
- **Stack Trace beats.** Mid-run "memory fragment" pop-ups (`STACK_TRACE_LINES`) deliver story breadcrumbs as a dedicated `GameState.STACK_TRACE` overlay.
- **Naming & flavour unification.** OS metaphors propagated end-to-end (`process_id`, `ram`, `cpu_cycles`, `sector`, `cache`, `crash_cause`).

### Added — Phase 8: Enemy Variety, Recognition & Adaptive Music

- **Roster expansion.** New `entities/malware_registry.py` (`SPECIES`, `maybe_get`) with archetypes `patroller`, `bomber`, `summoner`, `sniper`, `tank`, `swarm`. New mobs `Phisher`, `Worm`, `Daemon-Imp`, `Kernel-Trace`, plus elite variants flagged in the Bestiary.
- **Affix system.** `Malware` instances roll one of: `armoured`, `swift`, `vampiric`, `volatile`, `corrupted`. Affixes mutate stats, drop tables, and damage interactions. Procedural rolls are deterministic per seed.
- **Damage types & resistances.** New `entities/damage.py::DamageType` (`PHYSICAL`, `ENERGY`, `LOGIC`). Programs/daemons advertise a damage type; enemies have per-type resistance multipliers. Hit-feedback console messages call out resists/weaknesses.
- **Scout / "Recognition" mechanic.** Inspect mode (`X`) lets the player target a tile and reveal stats + lore + recommended counter; locked species require N kills in `intel` table before details unlock. New `IntelRepository`.
- **Bestiary.** New `GameState.BESTIARY` page lists every species seen this run/lifetime with kill count, weakness/resist colour bars, and lore blurb.
- **Damage analytics.** `CombatLogRepository` records per-(program, species) hit/kill counts; surfaced in the post-run summary as a top-3 "what worked" panel.
- **Adaptive music engine.** New `ui/music.py::StemMixer` blends four stems (`bed`, `tension`, `combat`, `boss`) by tracking enemy proximity, recent damage, and boss state. Crossfades smoothly via `SoundManager.apply_stem_volumes`.

### Added — Phase 9: Boss Spectacle & Pantheon

- **Boss framework.** Common base in `entities/malware.py` for HP-gated phase scripts, telegraphed attacks, arena spawners, and Daemon drops. Six bosses now ship: `KernelPanic`, `SegFault`, `BufferOverflow`, `RootkitHydra`, `DeadlockTwin`, `TheLeak`.
- **`BufferOverflow`** — periodically floods the arena with stack-frame walls; HP-phase 2 collapses the arena from the edges inward.
- **`RootkitHydra`** — splits into smaller copies on phase transition; killing one without the others heals the rest.
- **`DeadlockTwin`** — two linked bosses that share damage; defeating one paralyses the other for two turns.
- **`TheLeak`** — final boss that drains player RAM each turn until a "memory fragment" tile is reached. Dedicated boss arena with corruption tiles.
- **Boss arenas.** `world/generator.py` recognises `kind=boss` and produces purpose-built rooms with locked exits and themed tile palettes.
- **Pantheon progression.** `MetaRepository` tracks first-kill timestamps per boss; ending unlocks gated on full clears.

### Added — Phase 10: Interactive Tutorial Range ("/dev/sandbox")

- **The Range.** New `world/tutorial_range.py` builds a sandbox arena (`RangeArena`, `build_range_world`, `load_range_arena`) with no fail state.
- **Curriculum.** 8-lesson `CURRICULUM` covering movement, attack, cache use, programs, daemons, patches, boss telegraphs, recognition. `LessonProgress` checks fire from the gameplay handler.
- **The Polygon (free-play sandbox).** Press `` ` `` (or `Tab`) to open a kind-switching overlay (enemy / item / program / daemon / patch). Spawn anything on demand with `F1` god mode, `F2` infinite cycles, `F3` full FOV.
- **Hint system.** `ui/explain.py::explain` provides contextual one-liners surfaced inside the range and the Bestiary.
- **Tests.** Lesson tracking, polygon spawning, and arena loading covered.

### Added — Phase 11: Distros & Structured Runs

- **Run structure.** New `core/run_progress.py::RunProgress` defines a run as **8 Releases × 3 Milestones (NORMAL → BOSS → BOSS) × N Sectors**, each with a score target. Reaching the exit always **clears** a milestone; hitting the score target awards a `target_hit` bonus (+5 bits, doubled if `double_bits_pending`). Milestone bookkeeping persisted via `MilestoneRepository` and migration `008_phase11_distros`.
- **Distros (six "decks").** New `data/distros_catalog.py` with `vanilla`, `minimal`, `hardened`, `realtime`, `bleeding_edge`, `recovery`. Each distro adjusts starting RAM/cycles, starter programs, and run-wide modifiers. Unlock chain: clearing a distro unlocks the next. Backed by `DistroRepository`.
- **Distro select screen.** New `GameState.DISTRO_SELECT` shown before every fresh run; renders bonus stats, signature, and unlock hint.
- **Vendor.** New `GameState.VENDOR` between milestones — buy programs / daemons / patches with `bits` currency. Stock rolled from per-distro tables; `free_vendor` skip tag waives all costs once.
- **Skip tags.** New `entities/skip_tag.py` (`CATALOG`) — random debuffs offered at run start in exchange for bonus rewards (`double_bits`, `extra_daemon_slot`, `bonus_score`, `free_vendor`). Persisted via `SkipTagRepository`.
- **Milestone result screen.** New `GameState.MILESTONE_RESULT` summarising kills, bits earned, target_hit bonus.
- **Run summary.** New `GameState.RUN_SUMMARY` rolls up the full release: distros cleared, total bits, top combat-log entries, daemons surfaced.
- **Soft milestone gate.** Reaching the exit always clears the milestone; missing the score target only forfeits the bonus instead of ending the run.

### Added — Internationalisation (English / Turkish)

- **i18n module.** New `ui/i18n.py` with `t(key, **kwargs)`, `set_language`, `cycle_language`, and full `_EN` / `_TR` dictionaries (~150 keys covering menu, settings, vendor, milestone, summary, distros).
- **Per-distro translations.** Six distros × four fields (name / desc / signature / unlock hint) routed through `engine._distro_rows()` with catalog fallback.
- **Menu options.** `_MENU_OPTIONS` switched to stable keys (`new_run`, `daily_run`, `training`, `howtoplay`, `codex`, `high_scores`, `daily_board`, `stats`, `shop`, `settings`, `quit`); render path translates per frame so the language toggle takes effect immediately.
- **Settings toggle.** Language row in Settings cycles `EN ↔ TR`; persisted via `MetaRepository`.

### Added — Interactive Main Menu

- **Animated character avatar.** Pixel `init(0)` sprite slides between menu rows with a critically damped lerp; idle bob driven by `sin(_menu_phase)`. Halo glow + neon arrow point at the active option.
- **Cyber-grid backdrop.** Slow-scrolling translucent grid behind the menu.
- **Highlight bar.** Active row gets a translucent neon-cyan bar + underline, pulsing title with green offset glow.
- **Translated footer hint.** `t("menu.hint")` — `[↑/↓] navigate  [ENTER] select  [ESC] quit`.

### Added — Architecture: State Pattern Refactor

- **`core/states/` package.** New base class `GameStateHandler` (`enter` / `exit` / `handle_event` / `update` / `render` hooks) and per-state subclasses split across `menu_states.py`, `playing_states.py`, `shop_state.py`, `tutorial_state.py`, `cinematic_states.py`, `game_over_state.py`. Registry built by `core/states/registry.py::build_state_registry()`.
- **`GameEngine` slimmed.** The 160-line `if/elif` chain in `_render` and the matching dispatch in `_handle_events` collapse to `handler.render(self, ui)` / `handler.handle_event(self, event)`. Engine retains global hotkeys (`F11`, `M`) and is the single owner of game data.
- **Public helpers exposed for handlers.** `GameEngine.start_new_run`, `reset_to_menu`, `compute_bonus`.
- **55 new state-pattern unit tests** (`tests/core/test_states.py`) asserting registry coverage, mapping, default no-op contract, delegation, and render targets. Total suite: **297 passing**.

### Added — Documentation

- `docs/PRD_AND_ARCH.md` §4 updated with the State Pattern delegation rule and new §A.1.
- `CLAUDE.md` updated to list `core/states/` in the architecture diagram and module-boundary section.
- `AGENTS.md` updated to require tests for new logic in `core/states/`.

### Changed

- **`GameEngine`** registers a `_state_handlers` registry on init; `_active_state` property dispatches per-frame work. All previous private helpers (`_handle_*_key`, `_render_inspect_overlay`, etc.) preserved for backward compatibility and used by handlers.
- **Boss-down ending.** Killing `KernelPanic` mid-run no longer hijacks structured runs. The cinematic ending fires via `_finish_run(success=True)` once `RunProgress` reports completion.
- **Vendor flow.** Unconditional vendor entry between milestones (when the run is incomplete) — removes a dead branch that previously skipped vendor after boss + SECTOR_A combos.
- **Milestone result wording.** Replaced cleared/failed labels with `target_hit` / `target_missed` semantics in both languages so the soft gate reads correctly.
- **Music director.** Crossfades wired through `StemMixer.step(dt)` and `SoundManager.apply_stem_volumes`.

### Fixed

- Boss kill on `KernelPanic` no longer triggers the cinematic ending in mid-run structured runs (`_start_ending()` now guarded by `self._run_progress is None`).
- Soft milestone gate: reaching the exit always clears; missing the score target no longer triggers `_enter_game_over`.
- Distro descriptions in the picker now actually translate when the language toggle changes (previously hardcoded English).
- `t("milestone.target_hit")` / `t("milestone.target_missed")` strings present in EN and TR (no more raw key bleed-through on the milestone result screen).

### Tests

- **+55 unit tests** for the State Pattern (`tests/core/test_states.py`).
- Phase 7–11 work shipped with: `test_phase4_repositories.py` (already), `test_phase5_*` (5 files), `test_phase6.py`, `test_phase11_repositories.py`, plus targeted updates in `test_smoke.py`, `test_world.py`.
- Full suite: **297 passing** (was 242 at v2.0.0).

### Quality Gate

- `ruff check .` ✓
- `black --check .` ✓
- `mypy --strict src` ✓ (66 source files, no issues)
- `pytest` ✓ (297 passed)

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
