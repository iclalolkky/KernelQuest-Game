# Kernel Quest: The Memory Leak

> A grid-based, rogue-like RPG where you traverse a simulated operating system's memory, purging corrupted data and malware before the kernel panics.

![Status](https://img.shields.io/badge/status-v2.0.0-brightgreen)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Table of Contents

- [Overview](#overview)
- [Highlights](#highlights)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Gameplay](#gameplay)
- [Accessibility & Display](#accessibility--display)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Kernel Quest** is a turn-based, grid-based rogue-like inspired by *Tron* aesthetics, *Balatro*-style stacking modifiers, and classic Rogue mechanics — themed around operating-system internals. You play as a `Process` exploring procedurally generated memory sectors, managing **RAM** (health) and **CPU Cycles** (energy), stacking **Programs**, **Daemons**, and **Patch Notes** to outrun the next crash.

## Highlights

- **Procedural memory sectors** with seedable RNG and depth-scaled difficulty.
- **Programs (active abilities)** — `fork()`, `kill -9`, `sudo`, `grep`, `nice`, `nohup`, `chmod +x`, hot-keyed to **Q / E / R**.
- **Daemons (passive modifiers)** — up to 5 equipped slots with synergy tags (`arithmetic`, `io`, `network`, `memory`, `signal`) for combo bonuses.
- **20 Patch Notes** offered between sectors — pick run-shaping modifiers like `kernel-bypass`, `dark-mode`, `swap-thrash`, `root-kit`.
- **Combo / chain scoring** with a Balatro-style multiplier widget that pops on every kill → pickup → kill.
- **Two bosses** with radically different feel: `KernelPanic` (multi-phase bruiser) and `SegFault` (teleporting splitter). Both **lock the EXIT** until terminated, swap the BGM to a dedicated boss track, and trigger a screen-glitch theme.
- **Daily seed challenge** — same dungeon for everyone that day, local daily leaderboard.
- **Meta-progression shop** — spend `bits` between runs on permanent upgrades.
- **First-Boot tutorial** + in-repo `HOWTOPLAY.md` viewer (scrollable inside the game).
- **4 themes** (Kernel / Phosphor / Amber / High-Contrast), fullscreen toggle, UI scale slider, separate Music/SFX volumes, mute, reduce-motion, large-text mode, CRT scanlines.

## Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Language     | Python 3.12+                        |
| Game Engine  | Pygame                              |
| Persistence  | SQLite (`sqlite3` stdlib)           |
| Architecture | OOP, MVC-flavored                   |
| Tooling      | `ruff`, `black`, `pytest`, `mypy`   |

## Project Structure

```
KernelQuest-Game/
├── src/kernelquest/
│   ├── main.py              # Entry point
│   ├── core/                # GameEngine, GameState, config, settings
│   ├── world/               # MemoryGrid, generator, World, FOV
│   ├── entities/            # Player, malware, items, programs, daemons, patches
│   ├── systems/             # combat, ai, pathfinding, inventory
│   ├── ui/                  # renderer, themes, hud, console_log, fx, sfx
│   └── data/                # database, migrations, repositories
├── tests/                   # pytest suite (142 tests)
├── docs/PRD_AND_ARCH.md
├── ROADMAP.md
├── HOWTOPLAY.md
├── CHANGELOG.md
├── kernelquest.spec         # PyInstaller spec
└── pyproject.toml
```

## Getting Started

### Prerequisites

- Python **3.12** or later
- `pip` and `venv`
- A working audio/video stack (for Pygame)

### Installation

```bash
git clone https://github.com/<your-user>/KernelQuest-Game.git
cd KernelQuest-Game
python3 -m venv .venv
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

### Run

```bash
python -m kernelquest.main
```

### Tests / quality gate

```bash
ruff check . && black --check . && mypy src && pytest
```

### Pre-built binaries

GitHub Releases publishes one-file builds for **macOS (arm64)** and **Windows (x64)** on every `v*` tag. Download from the [Releases](../../releases) page; on macOS, right-click → **Open** the first time (the build is unsigned).

## Gameplay

### Resources

| Resource     | Role                                  |
|--------------|---------------------------------------|
| **RAM**      | Health. 0% → System Crash             |
| **CPU Cycle**| Energy per turn                       |
| **Cache**    | Inventory for collected data packets  |
| **Bits**     | Persistent meta-currency for the Shop |

### Enemies

- **SyntaxError** — weak, numerous, semi-random patrol.
- **LogicBomb** — charges and explodes in an AoE when adjacent.
- **ZombieProcess** — elite; revives once after death.
- **KernelPanic** *(boss)* — multi-phase, hits hard. Locks the EXIT.
- **SegFault** *(boss)* — teleports, splits the grid in half. Locks the EXIT.

### Default controls

| Action                | Key                          |
|-----------------------|------------------------------|
| Move                  | Arrow keys / WASD            |
| Wait                  | Space                        |
| Use cache slot 1–9    | `1` … `9`                    |
| Programs (loadout)    | **Q / E / R**                |
| Toggle help overlay   | `?` / `/` / `F1`             |
| Toggle fullscreen     | **F11**                      |
| Toggle mute           | **M**                        |
| Self-terminate        | `Esc` (during play)          |

A persistent mini help-bar at the bottom always shows the most relevant keys for your current state.

## Accessibility & Display

- **Themes** — Kernel (default), Phosphor Green, Amber CRT, High Contrast.
- **Fullscreen** + UI scale slider (0.75× – 1.5×) for hi-DPI displays.
- **Reduce motion** — disables screen shake and particle pops.
- **Large text** mode — bumps every font size by +25%.
- **CRT scanlines** toggle.
- Separate **Music** and **SFX** volume sliders, plus persistent **mute**.
- Screen-reader-friendly fallbacks: every HUD-relevant change is also written to the in-game `ConsoleLog`.

## Development

See [ROADMAP.md](ROADMAP.md) for the phased plan and [CLAUDE.md](CLAUDE.md) for AI-agent guidelines. Per-task workflow lives in [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
ruff check .
black .
mypy src
pytest
```

## Roadmap

- [x] **Phase 1 — Core Loop:** window, grid, player movement, SQLite scaffolding.
- [x] **Phase 2 — Procedural & Combat:** map generation, malware AI, combat.
- [x] **Phase 3 — UI & Polish:** Tron theme, HUD, console log, SFX, screen shake.
- [x] **Phase 4 — Persistence & Meta:** leaderboard, run history, persistent upgrades.
- [x] **Phase 5 — The Juice Update:** programs, daemons, combo scoring, patch notes, elites, daily seed.
- [x] **Phase 6 — Onboarding, UI Polish & Accessibility:** tutorial, themes, CRT, fullscreen, audio split, accessibility.

Full per-checkbox detail in [ROADMAP.md](ROADMAP.md).

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
