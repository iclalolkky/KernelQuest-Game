# AGENTS.md

This repository follows the [agents.md](https://agents.md) convention. AI coding agents should read the documents below **in this order** before making changes:

1. [docs/PRD_AND_ARCH.md](docs/PRD_AND_ARCH.md) — product requirements and high-level architecture.
2. [ROADMAP.md](ROADMAP.md) — current phase, open checkboxes, exit criteria.
3. [CLAUDE.md](CLAUDE.md) — coding standards, architectural boundaries, definition of done.
4. [CONTRIBUTING.md](CONTRIBUTING.md) — branching, commits, PR rules.

## Quickstart for Agents

```bash
# install
pip install -e ".[dev]"

# run the game
python -m kernelquest.main

# quality gate (must pass before opening a PR)
ruff check . && black --check . && mypy src && pytest
```

## Operating Principles

- **Pick one ROADMAP checkbox per task.** Do not bundle unrelated changes.
- **Respect module boundaries** (see [CLAUDE.md §4](CLAUDE.md#4-architectural-boundaries)).
- **Use OS-themed names** (`ram`, `cpu_cycles`, `sector`, `cache`, `crash_cause`).
- **Tests are not optional** for new logic in `world/`, `entities/`, `systems/`, `data/`.
- **Never commit** `*.db`, `.venv/`, `__pycache__/`, or generated assets.
- **Conventional Commits** for every commit message.

## When You're Unsure

Leave a `# TODO(agent): <question>` comment and surface it in the PR description rather than inventing behavior.
