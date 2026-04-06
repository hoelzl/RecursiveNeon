# CLAUDE.md — Recursive://Neon

## Project

Futuristic RPG prototype: player interacts with a simulated desktop via a terminal/shell. LLM-powered NPCs (Ollama), virtual filesystem, Python (FastAPI) backend. React/TypeScript frontend planned but not yet built.

**Status**: V2 reboot. Phases 0-7d complete. 1978 passing tests, 0 xfail. **Phase 7e (game-world hooks) is next**, followed by 7f (TUI apps), then Phase 8 (browser terminal + desktop GUI).
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
5. **Editor: Emacs is the ground truth.** For neon-edit features, match real GNU Emacs exactly. If a design doc or spec contradicts Emacs, the doc is almost certainly wrong — treat as a bug and match Emacs. Only deviate when Emacs behaviour is disproportionately complex to implement in our synchronous TUI model, and document the deviation next to the diverging code. When in doubt, ask for clarification. See `docs/V2_HANDOVER.md` for details.

## Shell Commands

**Builtins** (modify shell state): `cd`, `exit`, `export`

**Filesystem**: `ls`, `pwd`, `cat`, `mkdir`, `touch`, `rm`, `cp`, `mv`, `grep`, `find`, `write`

**Notes/Tasks**: `note` (list/show/create/edit/delete/browse), `task` (lists/list/add/done/undone/delete)

**NPC**: `chat` (list NPCs or enter conversation; supports `/exit`, `/help`, `/relationship`, `/status`)

**TUI Apps**: `edit` (Emacs-inspired text editor — neon-edit), `codebreaker` (Mastermind-style minigame), `sysmon` (system monitor); all require raw mode — work in local CLI and WebSocket client

**Utility**: `help`, `clear`, `echo`, `env`, `whoami`, `hostname`, `date`, `save`

**Shell features**: Glob expansion (`*.txt`, `Documents/*.txt`, `**/*.txt` recursive), pipes (`cat file | grep pattern`), output redirection (`echo hello > file.txt`, `>> file.txt`), stderr redirection (`2> err.txt`, `2>> err.txt`, `2>&1`). Tab completion is context-sensitive (per-command flags, subcommands, dynamic note/task/NPC refs).

**Persistence**: Game state auto-saves on exit to `game_data/`, and periodically during WebSocket sessions. Manual save via `save` command. Files: `filesystem.json`, `notes.json`, `tasks.json`, `npcs.json`, `history.txt`.

## Key Entry Points

- Shell entry: `backend/src/recursive_neon/shell/__main__.py` (`python -m recursive_neon.shell`)
- Shell REPL: `backend/src/recursive_neon/shell/shell.py` (transport-agnostic via `InputSource` protocol)
- Shell programs: `backend/src/recursive_neon/shell/programs/` (filesystem, notes, tasks, chat, codebreaker, sysmon, utility)
- Completion: `backend/src/recursive_neon/shell/completion.py` (`CompletionContext`, per-command completers)
- Glob expansion: `backend/src/recursive_neon/shell/glob.py` (`expand_globs`, `**` recursive matching)
- Pipeline parser: `backend/src/recursive_neon/shell/parser.py` (tokenizer, `Token`, `parse_pipeline`, `Redirect` with fd/stderr, `Pipeline.stderr_redirect`)
- Raw key input: `backend/src/recursive_neon/shell/keys.py` (platform-specific keystroke reading, shared by CLI and WS client)
- TUI framework: `backend/src/recursive_neon/shell/tui/` (`ScreenBuffer`, `TuiApp` protocol, `run_tui_app` runner)
- Editor: `backend/src/recursive_neon/editor/` (`Buffer`, `Mark`, `Editor`, `EditorView`, `Viewport`, `Minibuffer`, commands, keymaps, variables, modes, `Window`, `WindowTree`)
- Config loader: `backend/src/recursive_neon/editor/config_loader.py` (`ConfigNamespace`, `load_config`, sandboxed `~/.neon-edit.py` execution)
- Faces: `backend/src/recursive_neon/editor/faces.py` (`FACES`, `resolve_face` — named face→ANSI mapping)
- Language modes: `backend/src/recursive_neon/editor/modes/` (`python_mode`, `markdown_mode`, `sh_mode`, `AUTO_MODE_ALIST`, `detect_mode`)
- Shell-in-editor: `backend/src/recursive_neon/editor/shell_mode.py` (`BufferOutput`, `ShellState`, `ShellBufferInput`, `setup_shell_buffer`, comint commands, `execute_shell_command`)
- Text attributes: `backend/src/recursive_neon/editor/text_attr.py` (`TextAttr` — frozen SGR attribute type)
- ANSI parser: `backend/src/recursive_neon/editor/ansi_parser.py` (`parse_ansi` — ANSI text to `(text, attr)` runs)
- Editor shell host: `backend/src/recursive_neon/shell/programs/edit.py` (file I/O callbacks, path completion, shell factory, config loader)
- WS terminal: `backend/src/recursive_neon/terminal.py` (session manager, `WebSocketInput`, `QueueOutput`, raw mode)
- WS client: `backend/src/recursive_neon/wsclient/` (`python -m recursive_neon.wsclient`, `--command` batch mode)
- Backend main: `backend/src/recursive_neon/main.py` (includes `/ws/terminal` endpoint)
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
- `docs/TECH_DEBT.md` — Tech debt tracker (workarounds, deferred fixes)
- `docs/PHASE_7A_DESIGN.md` — Phase 7a design (read-only regions, text attrs, async bridge, interactive programs, TUI passthrough)
- `frontend/src/styles/desktop.css` — Cyberpunk CSS theme (preserved from v1 for future use)
