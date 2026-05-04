# Contributing to Kernel Quest

Thanks for your interest in contributing! This document covers everything you need to start hacking on the project.

> If you are an AI coding agent, please **also** read [CLAUDE.md](CLAUDE.md).

---

## Code of Conduct

Be respectful, inclusive, and constructive. Harassment of any kind is not tolerated.

## Getting Set Up

```bash
git clone https://github.com/<your-user>/KernelQuest-Game.git
cd KernelQuest-Game
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify the toolchain:

```bash
ruff check .
black --check .
mypy src
pytest
```

## Branching Model

- `main` — always green, releasable.
- `phase-<n>/<slug>` — feature branches tied to a ROADMAP item, e.g. `phase-2/enemy-ai`.
- `fix/<slug>` — bug fixes.
- `chore/<slug>` — tooling, docs, CI.

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

Common types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`.

Examples:

- `feat(world): procedural grid via cellular automata`
- `fix(entities): prevent negative cpu_cycles`
- `docs(readme): add controls table`

## Pull Requests

A good PR:

1. Closes one ROADMAP checkbox (link it in the description).
2. Keeps the diff focused — no drive-by refactors.
3. Adds/updates tests for any new logic.
4. Passes the full quality gate locally.
5. Updates `CHANGELOG.md` under `## [Unreleased]`.

PR title mirrors the main commit message.

## Coding Standards

See [CLAUDE.md §3](CLAUDE.md#3-coding-standards). TL;DR:

- `black` (line length 100), `ruff`, `mypy --strict`.
- Absolute imports under `kernelquest.*`.
- Constants in `core/config.py`.
- OS-themed naming (`ram`, `cpu_cycles`, `sector`, `cache`).

## Testing

- Framework: `pytest`.
- Place tests in `tests/`, mirroring `src/kernelquest/` structure.
- No live Pygame window or real DB file in tests — use headless surfaces and `:memory:` SQLite.
- Seed RNG explicitly in tests for determinism.

## Reporting Bugs

Open an issue with:

- Steps to reproduce
- Expected vs. actual behavior
- OS, Python version, Pygame version
- Stack trace / screenshot if relevant

## Suggesting Features

Open an issue tagged `enhancement` and describe:

- The problem you're trying to solve.
- A sketch of the proposed solution.
- Which ROADMAP phase it most naturally fits into.

## License

By contributing, you agree your contributions are licensed under the project's [MIT License](LICENSE).
