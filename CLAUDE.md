# CLAUDE.md — Recursive://Neon

## Project

Futuristic RPG prototype: player interacts with a simulated desktop via a terminal/shell. LLM-powered NPCs (Ollama), virtual filesystem, Python (FastAPI) backend. React/TypeScript frontend planned but not yet built.

**Status**: V2 reboot. Phases 0-2 complete. Phase 3 (browser terminal + desktop GUI) not started.
Read `docs/V2_HANDOVER.md` for full context, decisions, and implementation plan.

## V2 Direction

- **CLI-first**: every feature works in a real terminal before touching the browser
- **Layer stack**: Application Core → CLI Interface → Browser Terminal → Desktop GUI
- Legacy code preserved on `legacy/v1` branch (reference only, never merge)

## Essential Commands

```bash
# Backend setup (uses uv for fast dependency management)
uv venv --python 3.14 .venv       # Create venv (from repo root)
uv pip install -e "backend/.[dev]" # Install project + dev deps

# Run tests (from backend/)
cd backend
../.venv/Scripts/pytest
../.venv/Scripts/pytest --cov
../.venv/Scripts/pytest -m unit

# Code quality (from backend/)
../.venv/Scripts/ruff check .              # Lint
../.venv/Scripts/ruff check --fix .        # Lint + auto-fix
../.venv/Scripts/ruff format .             # Format
../.venv/Scripts/mypy                      # Type check

# Pre-commit hooks (from repo root)
../.venv/Scripts/pre-commit install        # Set up hooks (once after clone)
../.venv/Scripts/pre-commit run --all-files # Run all hooks manually
```

## Critical Rules

1. **Virtual filesystem isolation is sacred.** All in-game files are UUID-based `FileNode` objects in memory. Never use real file paths in game logic. See `backend/FILESYSTEM_SECURITY.md`.
2. **Use dependency injection.** All services go through `ServiceContainer`/`ServiceFactory` in `dependencies.py`. Never instantiate services directly.
3. **Don't add features beyond what's tested and working.** V1's mistake was breadth without depth.
4. **Write tests** for all new functionality.

## Shell Commands

**Builtins** (modify shell state): `cd`, `exit`, `export`

**Filesystem**: `ls`, `pwd`, `cat`, `mkdir`, `touch`, `rm`, `cp`, `mv`, `grep`, `find`, `write`

**Notes/Tasks**: `note` (list/show/create/edit/delete), `task` (lists/list/add/done/undone/delete)

**NPC**: `chat` (list NPCs or enter conversation; supports `/help`, `/relationship`, `/status`)

**Utility**: `help`, `clear`, `echo`, `env`, `whoami`, `hostname`, `date`, `save`

**Persistence**: Game state auto-saves on exit to `game_data/`. Manual save via `save` command. Files: `filesystem.json`, `notes.json`, `tasks.json`, `npcs.json`, `history.txt`.

## Key Entry Points

- Shell entry: `backend/src/recursive_neon/shell/__main__.py` (`python -m recursive_neon.shell`)
- Shell REPL: `backend/src/recursive_neon/shell/shell.py`
- Shell programs: `backend/src/recursive_neon/shell/programs/` (filesystem, notes, tasks, chat, utility)
- Backend main: `backend/src/recursive_neon/main.py`
- DI container: `backend/src/recursive_neon/dependencies.py`
- Models: `backend/src/recursive_neon/models/`
- Services: `backend/src/recursive_neon/services/`
- Interfaces: `backend/src/recursive_neon/services/interfaces.py`
- Config: `backend/src/recursive_neon/config.py`
- Tests: `backend/tests/`

## Reference Docs

- `docs/V2_HANDOVER.md` — V2 decisions, what was kept/removed, implementation phases
- `docs/SHELL_DESIGN.md` — CLI shell architecture, commands, path resolution
- `docs/BACKEND_CONVENTIONS.md` — Python code style, testing patterns, DI walkthrough
- `docs/ARCHITECTURE.md` — Why Ollama, system architecture
- `backend/FILESYSTEM_SECURITY.md` — Virtual filesystem security design
- `frontend/src/styles/desktop.css` — Cyberpunk CSS theme (preserved from v1 for future use)
