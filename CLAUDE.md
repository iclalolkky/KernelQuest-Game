# CLAUDE.md — Guidance for AI Coding Agents

This file is the **source of truth** for any AI agent (Claude, Copilot, Cursor, etc.) contributing to **Kernel Quest: The Memory Leak**. Read this *before* writing or modifying code. For product/architecture context, also read [docs/PRD_AND_ARCH.md](docs/PRD_AND_ARCH.md) and [ROADMAP.md](ROADMAP.md).

---

## 1. Project Snapshot

- **Name:** Kernel Quest: The Memory Leak
- **Type:** Grid-based rogue-like RPG (Pygame)
- **Language:** Python 3.12+
- **Persistence:** SQLite (`sqlite3` stdlib)
- **Architecture:** OOP, MVC-flavored. Code lives under `src/kernelquest/`.
- **Run:** `python -m kernelquest.main`
- **Test:** `pytest`

## 2. Golden Rules

1. **Stay in scope.** Implement only what the current task / roadmap item requires. Do not refactor unrelated modules.
2. **Follow the existing structure.** New code goes in the appropriate subpackage (`core/`, `core/states/`, `world/`, `entities/`, `systems/`, `ui/`, `data/`).
3. **Domain naming.** Use OS/architecture metaphors:
   - `process_id` (not `player_id`)
   - `ram` (not `health`)
   - `cpu_cycles` (not `energy`)
   - `sector` (not `level`)
   - `cache` (not `inventory`)
   - `crash_cause` (not `death_reason`)
4. **Never commit secrets** or local DB files. `database.db` and `*.sqlite*` are gitignored.
5. **Ask, don't guess.** If a requirement is ambiguous, leave a `# TODO(agent):` note rather than inventing behavior.

## 3. Coding Standards

- **Formatting:** `black` (line length 100).
- **Linting:** `ruff` (with `E`, `F`, `I`, `B`, `UP`, `SIM` rule sets).
- **Typing:** `mypy --strict` on `src/kernelquest/`. All public functions and methods are type-annotated.
- **Docstrings:** Google style on public classes and non-trivial functions.
- **Imports:** Absolute (`from kernelquest.world.grid import MemoryGrid`).
- **No magic numbers.** Constants live in `core/config.py`.
- **No global state.** Pass dependencies explicitly; the only singleton is `GameEngine`.
- **Logging:** use the `logging` module, not `print`. The in-game console log uses its own `ConsoleLog` class.

## 4. Architectural Boundaries

```
ui/  ────────────► reads from   core/, world/, entities/   (never writes game state)
systems/ ────────► mutates       world/, entities/
core/ ───────────► orchestrates  everything
core/states/ ────► State Pattern dispatch for GameEngine
data/ ───────────► owns          SQLite I/O                (no other module touches sqlite3)
```

- **UI layer is render-only.** No game-logic decisions inside `ui/`.
- **Data layer is the only place** that imports `sqlite3`.
- **Entities** never know about Pygame. Rendering is handled by `ui/renderer.py`.
- **`GameEngine` delegates** per-state event handling and rendering to `GameStateHandler` subclasses in `core/states/`. Handlers are stateless singletons keyed by `GameState`; the engine remains the single owner of game data and global hotkeys.

## 5. Database Conventions

- All schema changes go through `data/database.py::run_migrations()`.
- Migrations are append-only and numbered (`001_init.sql`, `002_add_runs.sql`, …).
- Use parameterized queries — **never** string-format SQL with user input.
- Wrap multi-statement writes in transactions.
- Required tables (see `docs/PRD_AND_ARCH.md`):
  - `scores(id, player_name, depth_reached, total_score, crash_cause, timestamp)`
  - `runs` and `upgrades` come in Phase 4.

## 6. Testing Expectations

- New logic in `world/`, `entities/`, `systems/`, `data/` ships **with** unit tests.
- Use `pytest` + fixtures; no real Pygame window in tests.
- For randomness, inject a `random.Random` seed; tests assert deterministic outcomes.
- Database tests use an in-memory SQLite (`":memory:"`).

## 7. Git & PR Workflow

- **Branch names:** `phase-<n>/<short-slug>`, e.g. `phase-2/logic-bomb-ai`.
- **Commit messages:** Conventional Commits.
  - `feat(world): add cellular-automata grid generator`
  - `fix(entities): clamp player ram at zero`
  - `chore(ci): add ruff to workflow`
- **One PR = one roadmap checkbox** whenever possible.
- PR description must reference the ROADMAP item it closes.

## 8. Performance Targets

- 60 FPS at 1080p on a 2020-era laptop.
- Grid updates are O(visible tiles), not O(grid size).
- Pathfinding uses A* with early-exit; avoid recomputing when player hasn't moved.

## 9. Definition of Done (per task)

A task is **done** when:

1. Code compiles and `python -m kernelquest.main` still launches.
2. `ruff check .`, `black --check .`, `mypy src` all pass.
3. `pytest` passes; new logic has new tests.
4. Public APIs are typed and documented.
5. The relevant ROADMAP checkbox is ticked in the same PR.
6. No new `print`, no commented-out code, no unused imports.

## 10. Things Agents Should NOT Do

- Do **not** add new third-party dependencies without justification in the PR description.
- Do **not** introduce async / threads unless solving a concrete profiled problem.
- Do **not** rename existing public APIs without updating all call sites and tests.
- Do **not** commit generated assets, `*.db`, `__pycache__`, or `.venv/`.
- Do **not** silently swallow exceptions. Log and re-raise, or handle explicitly.

## 11. Quick Reference Commands

```bash
# install
pip install -e ".[dev]"

# run
python -m kernelquest.main

# quality gate
ruff check . && black --check . && mypy src && pytest
```

---

When in doubt: prefer **clarity over cleverness**, **small PRs over big ones**, and **tests over assumptions**.
