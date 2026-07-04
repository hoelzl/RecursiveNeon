# AGENTS.md — Recursive://Neon

This file is the single source of truth for AI coding agents working on Recursive://Neon. It describes the project as it exists today — not as it is planned to be. When in doubt, prefer the files and tooling described here over any design doc; when a design doc contradicts working code, treat the code as correct and update the doc.

---

## 1. Project Overview

**Recursive://Neon** is a CLI-first futuristic RPG. The player interacts with a simulated remote computer through a terminal shell that feels like SSH. The game features:

- A **virtual filesystem** with Unix-like commands (`ls`, `cd`, `cat`, `grep`, `find`, `mkdir`, `rm`, `cp`, `mv`, `write`, ...).
- **Notes and tasks** managed through shell commands (`note`, `task`).
- **LLM-powered NPC chat** via a local Ollama server (`chat <npc>`).
- A full-screen **TUI text editor** called *neon-edit* (`edit`), modelled on GNU Emacs.
- Additional **TUI apps/minigames** (`codebreaker`, `sysmon`, `fsbrowse`, `portscan`, `memdump`).
- A **WebSocket terminal protocol** (`/ws/terminal`) that serves the same shell to a Python CLI client and to a React/xterm.js browser terminal.

**Current status**: V2 reboot. Phases 0-7f are complete. Phase 8 tasks 1-3 (xterm.js browser terminal over `/ws/terminal`) are implemented. Phase 9a (flag/quest state), 9b (NPC perception filter), 9c (knowledge gates in NPC prompts), and 9d (NPC initiative + queued messages) are complete. Phase 8 tasks 4-6 (desktop chrome, GUI apps) and the remaining Phase 9 sub-phases (9e Director/Fate, 9f vertical slice) are the next work. The legacy v1 code lives on the `legacy/v1` branch and should never be merged.

**Test counts (as of the latest collect)**:

- Backend pytest suite: **2,642 tests** collected (1 skipped).
- Frontend vitest suite: **42 tests** across 3 files.
- Editor parity harness: **32 scenarios** validated side-by-side against GNU Emacs 29.3.

---

## 2. Technology Stack

### Backend

- **Language**: Python 3.11+ (long-term target is 3.14; currently use 3.13 because the pinned Pydantic 2.13.4 is incompatible with CPython 3.14.0rc2).
- **Package manager**: `uv` (lock file at `backend/uv.lock`).
- **Web framework**: FastAPI + Uvicorn.
- **WebSocket library**: `websockets`.
- **Settings**: Pydantic Settings, loaded from `.env` (template: `.env.example`).
- **LLM/NPC stack**: LangChain + `langchain-ollama`, with an async `httpx` client for Ollama's REST API.
- **CLI shell**: `prompt_toolkit` for the local REPL; a custom raw-mode keystroke layer in `shell/keys.py`.
- **Build backend**: `hatchling` (configured in `backend/pyproject.toml`).

### Frontend

- **Language**: TypeScript (strict mode).
- **Framework**: React 18.
- **Build tool / dev server**: Vite (port 5173, proxies `/api` and `/ws` to `localhost:8000`).
- **Terminal emulator**: `@xterm/xterm` + `@xterm/addon-fit`.
- **State management**: Zustand.
- **Window drag/resize**: `react-draggable`, `react-rnd`.
- **Test runner**: Vitest with `jsdom` and `@testing-library/react`.

### Quality & CI tooling

- **Python lint/format**: Ruff (`py311` target, line length 88).
- **Python type check**: mypy (runs native + `--platform linux` in pre-commit to catch cross-platform issues).
- **Python tests**: pytest + pytest-asyncio + pytest-cov.
- **Pre-commit**: `ruff-pre-commit`, generic hooks, and local mypy hooks (`.pre-commit-config.yaml`).
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) runs Ruff lint/format, mypy, pytest with coverage, and the editor parity harness on every push/PR to `master`.

---

## 3. Repository Layout

```
.
├── .env.example                  # Environment variable template
├── .pre-commit-config.yaml       # Pre-commit hooks
├── AGENTS.md                     # This file
├── CLAUDE.md                     # Concise project cheat-sheet
├── README.md                     # Human-facing quick start
├── backend/
│   ├── pyproject.toml            # Python package, deps, pytest/ruff/mypy config
│   ├── uv.lock                   # uv lock file
│   ├── FILESYSTEM_SECURITY.md    # Virtual filesystem security design
│   ├── game_data/                # Runtime save files (gitignored)
│   ├── src/recursive_neon/
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings
│   │   ├── dependencies.py       # ServiceContainer + ServiceFactory (DI)
│   │   ├── main.py               # FastAPI app, HTTP endpoints, /ws/terminal
│   │   ├── terminal.py           # WebSocket terminal session manager
│   │   ├── models/               # Pydantic models (FileNode, NPC, GameState, ...)
│   │   ├── services/             # Business logic (AppService, NPCManager, ...)
│   │   ├── shell/                # CLI shell package
│   │   │   ├── __main__.py       # Entry point: python -m recursive_neon.shell
│   │   │   ├── shell.py          # REPL, pipeline dispatch, completion
│   │   │   ├── builtins.py       # cd, exit, export
│   │   │   ├── completion.py     # Context-sensitive tab completion
│   │   │   ├── glob.py           # Glob expansion against the virtual FS
│   │   │   ├── parser.py         # Tokenizer + pipeline parser
│   │   │   ├── output.py         # Output abstraction
│   │   │   ├── path_resolver.py  # Path string → FileNode resolution
│   │   │   ├── session.py        # ShellSession (cwd, env, prompt)
│   │   │   ├── keys.py           # Raw keystroke reading
│   │   │   ├── tui/              # TUI framework (ScreenBuffer, runner)
│   │   │   └── programs/         # Shell programs (filesystem, notes, tasks, ...)
│   │   ├── editor/               # neon-edit TUI editor
│   │   │   ├── buffer.py, mark.py, undo.py, killring.py
│   │   │   ├── editor.py, view.py, viewport.py, window.py
│   │   │   ├── minibuffer.py, commands.py, keymap.py
│   │   │   ├── default_commands.py, isearch_commands.py, replace_commands.py
│   │   │   ├── shell_mode.py     # Shell-in-editor (M-x shell)
│   │   │   ├── dired.py          # dired-mode over the virtual FS
│   │   │   ├── app_host.py       # Host TUI apps inside editor windows
│   │   │   ├── game_bridge.py    # Game-world commands (open-note, ...)
│   │   │   ├── ansi_parser.py, text_attr.py, faces.py
│   │   │   └── modes/            # Language modes (python, markdown, sh)
│   │   ├── wsclient/             # WebSocket CLI client
│   │   └── initial_fs/           # Default virtual filesystem contents
│   └── tests/
│       ├── conftest.py           # Shared fixtures
│       ├── unit/                 # Unit tests
│       │   ├── shell/            # Shell program tests
│       │   └── editor/           # Editor tests
│       └── integration/          # End-to-end workflow tests
├── frontend/
│   ├── package.json              # npm scripts and dependencies
│   ├── vite.config.ts            # Vite dev server + /ws proxy
│   ├── vitest.config.ts          # Vitest config
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx
│       ├── terminal/             # Browser terminal (xterm.js + protocol)
│       ├── themes/
│       └── styles/
├── docs/                         # Design and handover documents
├── parity/                       # Emacs parity harness (see docs/PARITY_HARNESS.md)
└── scripts/                      # download_ollama.py, legacy setup.sh/setup.bat
```

---

## 4. Build, Run, and Test Commands

All commands assume a virtual environment at the repo root (`.venv`). The recommended way to create it is `uv`.

### Setup

```bash
# Create the venv and install the backend (run from repo root)
uv venv --python 3.13 .venv
uv pip install -e "backend/.[dev]"

# Install frontend dependencies (run from frontend/)
cd frontend
npm install
```

> The legacy `scripts/setup.sh` and `scripts/setup.bat` files still exist but they reference `requirements.txt` and `backend/venv`; they are not the recommended setup path today.

### Running the game

```bash
# Interactive local shell (no Ollama required unless you use `chat`)
.venv/Scripts/python -m recursive_neon.shell          # Windows
.venv/bin/python -m recursive_neon.shell              # Linux/macOS

# Full backend server (starts Ollama and exposes /ws/terminal)
.venv/Scripts/python -m recursive_neon.main           # Windows
.venv/bin/python -m recursive_neon.main               # Linux/macOS
# Alternative explicit Uvicorn run:
uvicorn recursive_neon.main:app --port 8000

# WebSocket CLI client (connects to ws://localhost:8000/ws/terminal)
.venv/Scripts/python -m recursive_neon.wsclient
# Batch mode: .venv/Scripts/python -m recursive_neon.wsclient --command "ls"

# Browser terminal dev server
# 1. Start the backend on port 8000.
# 2. In another terminal:
cd frontend
npm run dev           # http://localhost:5173
```

### Backend tests

Run from the `backend/` directory:

```bash
# All tests (with coverage, as configured in pyproject.toml)
../.venv/Scripts/pytest

# Filter by marker
../.venv/Scripts/pytest -m unit
../.venv/Scripts/pytest -m integration
../.venv/Scripts/pytest -m "not slow"

# Without coverage / faster iteration
../.venv/Scripts/pytest --no-cov
```

Coverage configuration lives in `backend/pyproject.toml`. The default run produces terminal, HTML (`backend/htmlcov/`), and XML (`backend/coverage.xml`) reports.

### Backend quality checks

Run from the `backend/` directory:

```bash
../.venv/Scripts/ruff check .
../.venv/Scripts/ruff check --fix .
../.venv/Scripts/ruff format .
../.venv/Scripts/ruff format --check .
../.venv/Scripts/mypy
```

mypy must be run from inside `backend/` because `mypy_path = "src"` is relative to that directory.

### Frontend tests

```bash
cd frontend
npm test -- run              # run once
npm run test:ui              # vitest UI mode
npm run test:coverage        # with coverage
npm run lint                 # ESLint
npm run build                # tsc + production build
```

### Pre-commit hooks

```bash
# From repo root
.venv/Scripts/pre-commit install
.venv/Scripts/pre-commit run --all-files
```

The local mypy hook runs both native and `--platform linux` passes.

### Editor parity harness

The parity harness is Unix-only (it uses `pexpect` + `pyte`) and compares `neon-edit` against GNU Emacs 29.3.

```bash
# Install extra harness dependencies (not in pyproject dev deps)
uv pip install -e "./backend[dev]" pyte pexpect

# Run all scenarios (exit nonzero on any unexpected divergence)
.venv/bin/python -m parity.run

# Run a subset or list them
.venv/bin/python -m parity.run 09
.venv/bin/python -m parity.run --list

# Unit tests for the verdict logic (no pty/Emacs needed)
.venv/bin/python -m pytest parity/tests -q -o addopts=""
```

On a Windows checkout, run the harness inside WSL with a separate Linux venv and set `NEON_PARITY_PYTHON` to that venv's Python binary. See `docs/PARITY_HARNESS.md` for details.

---

## 5. Architecture

The project follows a strict layered, CLI-first architecture:

```
Layer 4: Desktop GUI (Browser)        ← planned (Phase 8 tasks 4-6)
Layer 3: Terminal Emulator (Browser)  ← xterm.js via /ws/terminal (Phase 8 tasks 1-3)
Layer 2: CLI Shell (Python)           ← complete
Layer 1: Application Core (Python)    ← complete
```

Every feature works in the CLI before it is exposed in the browser.

### Layer 1 — Application Core

Pure game logic and models, independent of any I/O transport.

- `models/` — Pydantic models: `FileNode`, `Note`, `Task`, `NPC`, `GameState`, `SystemState`.
- `services/app_service.py` — virtual filesystem, notes, tasks, persistence.
- `services/npc_manager.py` — LangChain NPC conversation manager with memory and relationship tracking.
- `services/ollama_client.py` — async httpx client for the Ollama REST API.
- `services/process_manager.py` — Ollama binary lifecycle.
- `services/game_event_bus.py` — pub/sub event bus for game-world events.
- `dependencies.py` — `ServiceContainer` and `ServiceFactory` provide dependency injection. Production and test containers are created here.

### Layer 2 — CLI Shell

- `shell/shell.py` — the REPL loop and command dispatcher.
- `shell/builtins.py` — commands that mutate shell state (`cd`, `exit`, `export`).
- `shell/programs/` — standalone programs that receive a restricted `ProgramContext` and cannot mutate shell state.
- `shell/parser.py` + `shell/glob.py` — tokenizer, pipeline parser (`|`), glob expansion.
- `shell/completion.py` — context-sensitive tab completion.
- `shell/tui/` — raw-mode TUI framework (`ScreenBuffer`, `TuiApp`, `run_tui_app`).

### Editor subsystem

`editor/` implements *neon-edit*, an Emacs-inspired TUI editor. It is a first-class host for the rest of the game:

- `M-x shell` opens a shell-mode buffer inside the editor.
- `C-x d` runs *dired* over the virtual filesystem.
- `M-x codebreaker`, `M-x sysmon`, `M-x fsbrowse`, `M-x portscan`, `M-x memdump` run those TUI apps inside editor windows via `app_host.py`.
- Game-world commands (`open-note`, `open-task-list`, `list-npcs`) live in `game_bridge.py`.

**Critical design principle**: for neon-edit features, **GNU Emacs is the ground truth**. If a design doc contradicts real Emacs behaviour, match Emacs and treat the doc as a bug. Document any intentional deviation next to the diverging code.

### Layer 3 — Browser Terminal

The browser terminal lives in `frontend/src/terminal/`:

- `protocol.ts` — JSON message schema shared with the backend.
- `session.ts` — protocol brain (cooked line editor, raw-mode frames, mode switching).
- `keys.ts` — DOM key event → protocol key encoding.
- `lineEditor.ts` — cooked-mode readline.
- `NeonTerminal.tsx` — xterm.js binding.

Vite proxies `/ws` to `localhost:8000`, so the frontend dev server and backend can run on their usual ports.

---

## 6. Code Style and Conventions

### Python

- **Formatting/linting**: Ruff, line length 88, target Python 3.11.
- **Imports**: stdlib → third-party → local, alphabetical within groups.
- **Naming**: `PascalCase` classes, `snake_case` functions/variables, `UPPER_SNAKE_CASE` constants, leading underscore for private members.
- **Interfaces**: prefix with `I` (e.g., `INPCManager`).
- **Type hints**: required on function parameters and return values.
- **Docstrings**: Google style (`Args`, `Returns`, `Raises`).
- **Async**: all I/O-bound operations must be `async`; use `asyncio.to_thread()` for blocking calls.
- **No real file paths in game logic** — see Security below.

### Type-checker notes

- mypy is configured in `backend/pyproject.toml`.
- Several lint rules are intentionally deferred: `UP006`/`UP007`/`UP035` (typing generics vs. built-in unions). The codebase still uses `typing.List`, `Optional`, etc. in many places. Do not bulk-modernize unless you are prepared to fix every occurrence.

### TypeScript / React

- Strict TypeScript (`strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`).
- ES2020 target, React JSX transform.
- Vite path alias `@/` resolves to `frontend/src/`.

### Dependency injection

Never instantiate services directly. Always obtain them from the `ServiceContainer`:

```python
# Good
ctx.services.app_service.create_file(...)

# Bad
app_service = AppService(...)  # never do this in game code
```

To add a new service:

1. Define the interface in `services/interfaces.py`.
2. Implement it in `services/my_service.py`.
3. Add a field to `ServiceContainer` in `dependencies.py`.
4. Wire construction in `ServiceFactory.create_production_container()`.
5. Add mock/stub support in `ServiceFactory.create_test_container()`.

### Adding a new shell command

1. Create `async def prog_mycommand(ctx: ProgramContext) -> int` in an appropriate file under `shell/programs/`.
2. Use services through `ctx.services` and write output to `ctx.stdout` / `ctx.stderr`.
3. Return `0` for success, nonzero for error.
4. Register via `registry.register_fn("mycommand", prog_mycommand, "Help text", completer=my_completer)`.
5. Call the registration function from `Shell.__init__` in `shell/shell.py`.
6. Write tests using `make_ctx` from `tests/unit/shell/conftest.py`.

Only commands that *must* modify shell state (`cd`, `exit`, `export`) are builtins; everything else is a program.

### Adding a new TUI app

1. Create a class implementing `TuiApp` (`on_start`, `on_key`, `on_resize`).
2. Render with `ScreenBuffer`.
3. Return an exit code from `on_key` to signal termination.
4. Register a shell command that calls `ctx.run_tui(my_app)`.
5. If the app should also run inside an editor window, wire a factory in `editor/app_host.py`.

---

## 7. Testing Strategy

- **Unit tests** are fast and have no external dependencies. Mark with `@pytest.mark.unit`.
- **Integration tests** may exercise multiple services or the full shell pipeline. Mark with `@pytest.mark.integration`.
- **Slow tests** are marked `@pytest.mark.slow`.
- **Async tests** use pytest-asyncio auto mode — do not add `@pytest.mark.asyncio`.
- **DI-first mocking**: prefer injecting mocks through `ServiceFactory.create_test_container()` rather than monkey-patching.
- **Shell program tests** create a `ProgramContext` via the `make_ctx` fixture and assert on `CapturedOutput`.
- **Editor tests** use `EditorHarness` (`tests/unit/editor/harness.py`) for TUI-level tests.
- **Parity harness** prevents Emacs divergences and runs in CI on a pinned `ubuntu-24.04` image with `emacs-nox` 29.3.

### CI pipeline

`.github/workflows/ci.yml` runs four jobs on push/PR to `master`:

1. **Lint & Format** — Ruff check + format check on Python 3.11.
2. **Type Check** — install `backend/.[dev]` and run `mypy`.
3. **Test** — pytest with coverage; uploads `coverage.xml` as an artifact.
4. **Editor Parity (Emacs)** — install `emacs-nox`, install backend + `pyte pexpect`, run parity unit tests, then run the full parity scenario suite.

---

## 8. Security Considerations

The virtual filesystem is the project's most sensitive security boundary. Read `backend/FILESYSTEM_SECURITY.md` for the full design.

Summary:

- All in-game files are UUID-based `FileNode` objects stored **in memory** during play.
- Game logic must never use real file paths. Paths are display strings only.
- The real filesystem is touched only in two controlled ways:
  1. Read-only initial state load from `backend/src/recursive_neon/initial_fs/`.
  2. Save/load game state to/from `backend/game_data/` as JSON.
- No path traversal is possible: parent-child relationships are UUID references, not directory paths.
- NPC chat requires a local Ollama server; no external API keys or network calls are made by the game.

**Critical rule**: virtual filesystem isolation is sacred. Never add a feature that lets shell programs or editor code read from or write to arbitrary host paths.

---

## 9. Configuration

Runtime configuration is loaded from `.env` (template: `.env.example`) via `backend/src/recursive_neon/config.py`. Key settings:

- `HOST`, `PORT` — backend bind address (default `127.0.0.1:8000`).
- `OLLAMA_HOST`, `OLLAMA_PORT`, `DEFAULT_MODEL` — local LLM endpoint (default model `qwen3:4b`).
- `DATA_DIR` — game save directory (default `backend/game_data`).
- `INITIAL_FS_PATH` — default virtual filesystem source (default `backend/src/recursive_neon/initial_fs`).
- `OLLAMA_BINARY_PATH`, `MODELS_DIR`, `CHROMADB_DIR` — Ollama-related paths.

Frontend dev server proxies `/api` and `/ws` to `localhost:8000` via `vite.config.ts`.

---

## 10. Key Entry Points and Reference Files

| Purpose | Path |
|---------|------|
| Backend package config | `backend/pyproject.toml` |
| Settings / `.env` loader | `backend/src/recursive_neon/config.py` |
| DI container | `backend/src/recursive_neon/dependencies.py` |
| FastAPI app + WebSocket | `backend/src/recursive_neon/main.py` |
| WebSocket terminal sessions | `backend/src/recursive_neon/terminal.py` |
| Local shell entry point | `backend/src/recursive_neon/shell/__main__.py` |
| Shell REPL + dispatch | `backend/src/recursive_neon/shell/shell.py` |
| Program registry / context | `backend/src/recursive_neon/shell/programs/__init__.py` |
| Shell builtins | `backend/src/recursive_neon/shell/builtins.py` |
| Completion framework | `backend/src/recursive_neon/shell/completion.py` |
| Pipeline parser | `backend/src/recursive_neon/shell/parser.py` |
| Glob expansion | `backend/src/recursive_neon/shell/glob.py` |
| TUI framework | `backend/src/recursive_neon/shell/tui/` |
| Editor coordinator | `backend/src/recursive_neon/editor/editor.py` |
| Editor view | `backend/src/recursive_neon/editor/view.py` |
| Editor window system | `backend/src/recursive_neon/editor/window.py` |
| Shell-in-editor | `backend/src/recursive_neon/editor/shell_mode.py` |
| Dired | `backend/src/recursive_neon/editor/dired.py` |
| TUI app host in editor | `backend/src/recursive_neon/editor/app_host.py` |
| Game bridge commands | `backend/src/recursive_neon/editor/game_bridge.py` |
| Browser terminal component | `frontend/src/terminal/NeonTerminal.tsx` |
| Browser terminal protocol | `frontend/src/terminal/protocol.ts` |
| Backend test fixtures | `backend/tests/conftest.py`, `backend/tests/unit/shell/conftest.py` |
| Editor test harness | `backend/tests/unit/editor/harness.py` |
| Parity harness | `parity/run.py` |

---

## 11. What's Next

- **Phase 8 tasks 4-6**: desktop chrome, GUI apps, window manager. Re-evaluate scope after the editor-as-shell work; the roadmap in `docs/EDITOR_SHELL_ROADMAP.md` argues that a fullscreen xterm.js pane running neon-edit may satisfy most of the "desktop" need.
- **Phase 9**: game-reactive systems. 9a (flags), 9b (NPC perception), 9c (knowledge gates), and 9d (NPC initiative + queued messages) are complete; 9e (Director/Fate system) and 9f (Act 1 vertical slice) remain. See `docs/PHASE_9_PLAN.md`.

---

## 12. Reference Documents

- `CLAUDE.md` — concise cheat-sheet for day-to-day work.
- `docs/V2_HANDOVER.md` — V2 decisions, phase history, implementation plan.
- `docs/ARCHITECTURE.md` — why Ollama, system architecture.
- `docs/BACKEND_CONVENTIONS.md` — Python style, DI walkthrough, testing patterns.
- `docs/SHELL_DESIGN.md` — shell architecture.
- `docs/EDITOR_SHELL_ROADMAP.md` — editor-as-shell roadmap and recent Phase 8 editor work.
- `docs/PARITY_HARNESS.md` — editor parity harness methodology.
- `docs/GAME_EVENTS.md` — game event bus schema.
- `docs/PHASE_9_PLAN.md` — planned game-reactive systems.
- `backend/FILESYSTEM_SECURITY.md` — virtual filesystem security.
