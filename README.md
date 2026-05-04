# Kernel Quest: The Memory Leak

> A grid-based, rogue-like RPG where you traverse a simulated operating system's memory, purging corrupted data and malware before the kernel panics.

![Status](https://img.shields.io/badge/status-in%20development-orange)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Table of Contents

- [Overview](#overview)
- [Core Concept](#core-concept)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Gameplay](#gameplay)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Kernel Quest** is a turn-based, grid-based rogue-like inspired by *Tron* aesthetics and classic Rogue mechanics, themed around operating system internals. You play as a `Process` exploring procedurally generated memory sectors, managing **RAM** (health) and **CPU Cycles** (energy) while fighting back against rogue malware threatening to crash the system.

## Core Concept

- **Theme:** Operating-system memory as a dungeon. Every block is a memory cell; every enemy is a faulty process.
- **Genre:** Rogue-like / Strategy / Grid-based Puzzle
- **Visual Style:** Tron-inspired neon-on-dark UI, glassmorphism panels, console log feed at the bottom of the screen.
- **Loop:** Explore → manage resources → defeat malware → descend into deeper memory sectors → save score on crash.

## Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Language     | Python 3.12+                        |
| Game Engine  | Pygame                              |
| UI / Launcher| CustomTkinter *(optional)*          |
| Persistence  | SQLite (`sqlite3` stdlib)           |
| Architecture | OOP, MVC-flavored                   |
| Tooling      | `ruff`, `black`, `pytest`, `mypy`   |

## Project Structure

```
KernelQuest-Game/
├── src/
│   └── kernelquest/
│       ├── __init__.py
│       ├── main.py                # Entry point
│       ├── core/
│       │   ├── engine.py          # GameEngine, main loop, state machine
│       │   ├── state.py           # GameState enum (MENU, PLAYING, GAMEOVER)
│       │   └── config.py          # Constants, tunables
│       ├── world/
│       │   ├── grid.py            # MemoryGrid, procedural generation
│       │   ├── tile.py            # Tile types (empty, system data, bad sector)
│       │   └── fog.py             # Fog-of-war / scan range
│       ├── entities/
│       │   ├── entity.py          # Base Entity
│       │   ├── player.py          # Player (Process)
│       │   └── malware.py         # SyntaxError, LogicBomb, KernelPanic
│       ├── systems/
│       │   ├── combat.py
│       │   ├── ai.py              # Pathfinding, enemy behaviors
│       │   └── inventory.py       # Cache management
│       ├── ui/
│       │   ├── renderer.py        # UIManager, draw calls
│       │   ├── hud.py             # RAM bar, CPU meter, side panel
│       │   ├── console_log.py     # Bottom log feed
│       │   └── theme.py           # Colors, fonts
│       ├── data/
│       │   ├── database.py        # SQLite connection, migrations
│       │   └── repositories.py    # Score / Run history repos
│       └── assets/
│           ├── sprites/
│           ├── sfx/
│           └── fonts/
├── tests/
│   ├── test_grid.py
│   ├── test_player.py
│   └── test_database.py
├── docs/
│   └── PRD_AND_ARCH.md
├── ROADMAP.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
├── pyproject.toml
└── README.md
```

## Getting Started

### Prerequisites

- Python **3.12** or later
- `pip` and `venv`
- A working audio/video stack (for Pygame)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-user>/KernelQuest-Game.git
cd KernelQuest-Game

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -e ".[dev]"
```

### Run the game

```bash
python -m kernelquest.main
```

### Run tests

```bash
pytest
```

## Gameplay

### Resources

| Resource     | Role                                  | Depletes On                     |
|--------------|---------------------------------------|---------------------------------|
| **RAM**      | Health. 0% → System Crash             | Taking damage                   |
| **CPU Cycle**| Energy per turn                       | Moving / attacking              |
| **Cache**    | Inventory for collected data packets  | —                               |

### Enemies

- **SyntaxError** — weak, numerous, semi-random patrol.
- **Logic Bomb** — explodes in an AoE when adjacent.
- **Kernel Panic** — boss with multi-phase attack patterns.

### Controls (default)

| Action          | Key            |
|-----------------|----------------|
| Move            | Arrow keys / WASD |
| Wait / Idle     | Space          |
| Use item        | E              |
| Inventory       | I              |
| Pause           | Esc            |

## Development

See [ROADMAP.md](ROADMAP.md) for the phased plan and [CLAUDE.md](CLAUDE.md) for AI-agent guidelines.

Style:

```bash
ruff check .
black .
mypy src
```

## Roadmap

High-level milestones (full detail in [ROADMAP.md](ROADMAP.md)):

- [ ] **Phase 1 — Core Loop:** window, grid, player movement, SQLite scaffolding.
- [ ] **Phase 2 — Procedural & Combat:** map generation, malware AI, combat.
- [ ] **Phase 3 — UI & Polish:** Tron theme, HUD, console log, SFX, screen shake.
- [ ] **Phase 4 — Persistence & Meta:** leaderboard, run history, persistent upgrades.

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
