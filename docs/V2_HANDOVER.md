# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-03-24)
> **Status**: Phases 0-2 complete. Phase 3 (WebSocket terminal protocol + CLI client) not started. Phases 4-5 planned.
> **Branch**: `master` (orphan branch, initial commit: `384e373`)

---

## 1. Context: What Is This Project?

**Recursive://Neon** is a futuristic RPG prototype where the player interacts with a simulated desktop environment. The game features LLM-powered NPCs (via Ollama), a virtual filesystem, and a terminal/shell as the primary interaction mechanism. It uses a Python (FastAPI) backend and React (TypeScript) frontend.

The project was originally built as an experiment in agentic coding with Claude Code. The v1 iteration produced ~25K lines of code with good architecture but many broken features: 14 desktop apps and 4 minigames were created, but most didn't actually work despite passing their unit tests. The terminal had a fundamentally flawed two-pane design.

## 2. What Was Decided

After a thorough evaluation of the v1 codebase, the following decisions were made:

### 2.1 Iterate, Don't Rewrite
The architecture (DI pattern, interfaces, models) is solid. The visual CSS theme is polished. The problems are specific integration failures and a flawed terminal design, not fundamental architecture issues.

### 2.2 CLI-First Development
Instead of building the browser UI first, the new approach is:

```
Layer 1: Application Core (Python)
  Game state, filesystem, NPC conversations, commands
  Pure logic, no I/O assumptions, fully testable

Layer 2: CLI Interface (Python, stdin/stdout)
  Real terminal, real readline, runs in any terminal
  Claude Code can interact with this directly for testing

Layer 3: Terminal Emulator (Browser)
  Connects to backend session via WebSocket
  Renders the same experience as the CLI

Layer 4: Desktop GUI (Browser, optional)
  Window manager, icons, taskbar
  Terminal windows + optional native GUI apps
```

**Rationale**: Every feature works in CLI before touching the browser. Claude Code becomes a playtester. Forces proper separation of concerns. The game narrative (hacking into a remote system) fits a terminal-first experience perfectly.

### 2.3 Terminal Redesign
The v1 terminal had a split output/input design that doesn't match how real terminals work. The v2 terminal should take inspiration from the real terminal architecture:

```
Real terminal stack:          Our simplified version:
─────────────────────         ─────────────────────
Terminal emulator             Terminal emulator (xterm.js or custom)
  ↕ escape sequences            ↕ escape sequences
PTY                           Virtual PTY (session buffer + modes)
  ↕ raw bytes                   ↕ structured messages
Line discipline               Line discipline (cooked/raw modes)
  ↕ edited lines                ↕ edited lines
Shell                         Shell (command parser + dispatch)
  ↕ stdio                      ↕ stdio-like interface
Programs                      Apps (CLI commands, TUI apps, games)
```

Key requirement: **two input modes**:
- **Cooked mode** (normal shell): line editing, history, tab completion, submit on Enter
- **Raw mode** (TUI apps/minigames): every keystroke goes directly to the app, which controls the full screen

**xterm.js** is the leading candidate for the browser-side terminal emulator.

### 2.4 Orphan Branch
Created a new `main` orphan branch with curated files. The old code is preserved on `legacy/v1` for reference (especially CSS styling and design ideas).

## 3. What Was Done (Phase 0)

### 3.1 Branch Setup
- Stashed uncommitted changes on `claude/improve-terminal-input-*`
- Renamed `master` → `legacy/v1`
- Created orphan branch `main`, later renamed to `master`
- Old `master` (v1 code) renamed to `legacy` on the remote
- Cleared working tree, selectively restored files from `legacy/v1`

### 3.2 Files Kept and Cleaned

**Backend models** — stripped BrowserPage, MediaViewerConfig, TextMessage, Calendar, Notification models. Kept: NPC, FileNode, Note, Task, GameState, SystemState.
- `backend/src/recursive_neon/models/app_models.py` — cleaned
- `backend/src/recursive_neon/models/game_state.py` — rewritten, removed notification/calendar/browser/media_viewer imports
- `backend/src/recursive_neon/models/npc.py` — kept as-is (good quality)
- `backend/src/recursive_neon/models/__init__.py` — cleaned exports

**Backend interfaces** — stripped ICalendarService, INotificationService, ITimeService, ISettingsService. Kept: LLMInterface, INPCManager, IOllamaClient, IProcessManager.
- `backend/src/recursive_neon/services/interfaces.py` — rewritten (reduced from 779 to ~130 lines)

**Backend DI** — stripped all calendar/notification/time/settings service creation. Fixed incomplete test_container.
- `backend/src/recursive_neon/dependencies.py` — rewritten

**Backend main.py** — CRITICAL: fixed `manager.broadcast()` bug (was NameError at runtime). Removed all notification endpoints. Removed MessageHandler import (service file was deleted). Inlined WebSocket message handling as `handle_ws_message()` function. Changed `system_state.dict()` to `system_state.model_dump()`.
- `backend/src/recursive_neon/main.py` — rewritten

**Backend app_service.py** — stripped browser service (~40 lines), media viewer service (~200 lines, including default message initialization). Added `handle_action()` router method. Kept filesystem, notes, tasks CRUD.
- `backend/src/recursive_neon/services/app_service.py` — rewritten

**Backend services kept as-is** (good quality, no broken references):
- `backend/src/recursive_neon/services/npc_manager.py`
- `backend/src/recursive_neon/services/ollama_client.py`
- `backend/src/recursive_neon/services/process_manager.py`
- `backend/src/recursive_neon/config.py`

**Backend tests** — removed `test_message_handler.py` (tested deleted MessageHandler class). Removed `TestBrowserService` from `test_app_service.py` and cleaned BrowserPage import. Kept:
- `backend/tests/conftest.py` — mock LLM, sample NPCs, fixtures (good quality)
- `backend/tests/unit/test_app_service.py` — notes, tasks, filesystem tests
- `backend/tests/unit/test_filesystem_security.py` — security isolation tests
- `backend/tests/unit/test_npc_manager.py` — NPC registration, chat, relationships

**Frontend** — NO React components were kept. Only reference/config files:
- `frontend/src/styles/desktop.css` — cyberpunk theme CSS (2400+ lines, polished)
- `frontend/src/styles/calendar.css` — calendar CSS (kept for styling reference)
- `frontend/src/themes/themes.ts` — 6 theme presets with color definitions
- `frontend/src/types/index.ts` — TypeScript types mirroring backend models (cleaned)
- Build config: package.json, tsconfig, vite, vitest configs

**Other kept files**:
- `.gitignore` — updated to include `.venv/` and `.pytest_cache/`
- `LICENSE` (Apache 2.0), `.env.example`
- `docs/ARCHITECTURE.md`, `docs/QUICKSTART.md`
- `backend/FILESYSTEM_SECURITY.md`
- `scripts/setup.sh`, `scripts/setup.bat`, `scripts/download_ollama.py`
- `backend/src/recursive_neon/initial_fs/` — 8 sample files for virtual filesystem

### 3.3 What Was Deliberately Excluded
- **All notification system** — models, service, endpoints, tests, frontend components
- **Calendar system** — models, service, frontend components/CSS
- **Time service** — model, service, tests
- **Settings service** — model, service, tests, frontend components
- **Media viewer** — models, service, default messages
- **Browser** — models, service, tests
- **Message handler service** — deleted, inlined into main.py (will be redesigned)
- **All React components** — Desktop, Window, Taskbar, ChatApp, TerminalApp, NotesApp, TaskListApp, FileBrowserApp, CalendarApp, SettingsApp, etc.
- **All terminal system code** — CommandRegistry, CompletionEngine, TerminalSession, ShellParser, ArgumentParser, builtins, themes
- **All minigame code** — CodeBreaker, MemoryDump, PortScanner, CircuitBreaker
- **All frontend services** — WebSocket client, gameStore, contexts, providers
- **All frontend tests**
- **Feature-specific documentation** — terminal design/requirements, notification/calendar/settings/time docs, minigame docs

All of these are available on `legacy/v1` if needed for reference.

## 4. Current File Inventory

```
.env.example                          # Environment config template
.gitignore                            # Updated with .venv/, .pytest_cache/
LICENSE                               # Apache 2.0

backend/
  .gitignore                          # Backend-specific ignores
  FILESYSTEM_SECURITY.md              # Security design doc
  pyproject.toml                      # Python package config (hatchling)
  pytest.ini                          # Pytest markers config
  src/recursive_neon/
    __init__.py
    config.py                         # Pydantic Settings (host, port, ollama, paths)
    dependencies.py                   # ServiceContainer + ServiceFactory (DI)
    main.py                           # FastAPI app, WebSocket, HTTP endpoints
    models/
      __init__.py                     # Re-exports all models
      app_models.py                   # FileNode, Note, Task, TaskList + state models
      game_state.py                   # GameState, SystemState, StatusResponse
      npc.py                          # NPC, NPCMemory, ChatRequest/Response, enums
    npcs/__init__.py                  # Empty (for future NPC definitions)
    services/
      __init__.py
      app_service.py                  # Filesystem + Notes + Tasks CRUD + persistence
      interfaces.py                   # INPCManager, IOllamaClient, IProcessManager
      npc_manager.py                  # LangChain-based NPC conversation + persistence
      ollama_client.py                # httpx async client for Ollama API
      process_manager.py              # Ollama binary process lifecycle
    shell/                            # CLI shell package (Phase 1-2)
      __init__.py
      __main__.py                     # Entry point: python -m recursive_neon.shell
      builtins.py                     # cd, exit, export (modify shell state)
      output.py                       # ANSI output abstraction + CapturedOutput
      parser.py                       # Argv-style tokenizer (quoting, escaping)
      path_resolver.py                # Virtual path → FileNode resolution
      session.py                      # ShellSession (cwd, env, history)
      shell.py                        # REPL loop, dispatch, tab completion
      programs/
        __init__.py                   # ProgramRegistry + ProgramContext + Program protocol
        chat.py                       # NPC conversation sub-REPL with /commands
        filesystem.py                 # ls, pwd, cat, mkdir, touch, rm, cp, mv, grep, find, write
        notes.py                      # note list/show/create/edit/delete
        tasks.py                      # task lists/list/add/done/undone/delete
        utility.py                    # help, clear, echo, env, whoami, hostname, date, save
    initial_fs/                       # Sample files for virtual filesystem init
      welcome.txt
      Documents/{readme.txt, sample.txt, my test file.txt}
      My Folder/another file.txt
      Pictures/about.txt
      Projects/my-first-project.txt
      file with 'quotes'.txt
  tests/
    __init__.py
    conftest.py                       # Shared fixtures (mock LLM, NPCs, etc.)
    unit/__init__.py
    unit/test_app_service.py          # Notes, Tasks, FileSystem CRUD + persistence tests
    unit/test_filesystem_security.py  # Security isolation tests
    unit/test_npc_manager.py          # NPC registration, chat, persistence, think-tag tests
    unit/shell/__init__.py
    unit/shell/conftest.py            # Shell test fixtures (test_container, make_ctx, output)
    unit/shell/test_builtins.py       # cd, exit, export tests
    unit/shell/test_completion.py     # Tab completion tests
    unit/shell/test_filesystem_enhanced.py  # grep, find, write tests
    unit/shell/test_note_program.py   # Note CLI program tests
    unit/shell/test_parser.py         # Tokenizer tests
    unit/shell/test_path_resolver.py  # Path resolution tests
    unit/shell/test_programs.py       # Filesystem + utility program tests
    unit/shell/test_shell_integration.py  # Shell.execute_line dispatch tests
    unit/shell/test_task_program.py   # Task CLI program tests
    integration/__init__.py
    integration/conftest.py           # Integration test fixtures (shell, tmp_game_dir)
    integration/test_full_flows.py    # End-to-end workflow tests

docs/
  ARCHITECTURE.md                     # Why Ollama, system architecture
  QUICKSTART.md                       # Setup guide

frontend/
  .npmrc                              # npm config
  index.html                          # Vite entry HTML
  package.json                        # Dependencies (React 18, Zustand, etc.)
  package-lock.json
  tsconfig.json / tsconfig.node.json  # TypeScript strict config
  vite.config.ts                      # Vite build config
  vitest.config.ts                    # Vitest test config
  src/
    styles/desktop.css                # Main cyberpunk theme (~2400 lines)
    styles/calendar.css               # Calendar styles (reference)
    themes/themes.ts                  # 6 theme presets + applyTheme()
    types/index.ts                    # TS types: NPC, FileNode, Note, Task, etc.

scripts/
  setup.sh / setup.bat               # Setup scripts
  download_ollama.py                  # Ollama binary downloader
```

## 5. Known Issues in Current Code

1. ~~**No Python venv exists**~~ — **Resolved.** A `.venv` is created with `uv venv --python 3.14` and deps installed via `uv pip install -e "backend/.[dev]"`.

2. ~~**CLAUDE.md is outdated**~~ — **Resolved.** Rewritten for v2 with setup commands, quality tooling, and key entry points.

3. **`npc_manager.py` uses LangChain ConversationChain** — this was marked for potential simplification. ConversationBufferMemory has unbounded growth. Not blocking, but worth noting. (Uses `langchain_classic` compat shim after upgrade to langchain 1.x.)

4. **`app_service.py` uses O(n) list scans** — all get/update operations iterate the full node/note/task lists. Fine for now, but should use dict-based lookup if collections grow large.

5. **`main.py` WebSocket handling is inline** — the `handle_ws_message()` function was inlined when we removed MessageHandler. This should eventually be refactored back into a proper service when the message protocol stabilizes.

6. ~~**Remote `origin/master` still exists**~~ — **Resolved.** Remote reorganized: old `master` (v1) → `legacy`, `main` (v2) → `master` (default branch).

## 6. Implementation Plan (Phases 1-5)

### Phase 1: Build the Python CLI Shell — **COMPLETE**
**Goal**: A working command-line shell that runs in any terminal via `python -m recursive_neon.shell`.

Completed:
1. Shell architecture: `shell/` package with `session.py`, `shell.py`, `parser.py`, `path_resolver.py`, `output.py`, `builtins.py`, `programs/`
2. Builtins: `cd`, `exit`, `export`
3. Filesystem programs: `ls`, `cd`, `pwd`, `cat`, `mkdir`, `touch`, `rm`, `cp`, `mv`
4. Utility programs: `help`, `clear`, `echo`, `env`, `whoami`, `hostname`, `date`
5. Chat program: `chat <npc_id>` with sub-REPL conversation mode
6. Tab completion: command names + virtual filesystem paths (quoting-aware)
7. Command history via prompt_toolkit
8. 172 unit tests, all passing
9. `-h`/`--help` flag support for all commands

### Phase 2: Deepen Core Features — **COMPLETE**
**Goal**: The 3 core systems (filesystem, NPC chat, notes/tasks) work flawlessly in CLI.

Completed:
1. **Persistence**: Notes, tasks, NPC state, and shell history all persist to `game_data/` as JSON. Auto-save on shell exit + explicit `save` command. Production container loads all state from disk on startup; falls back to defaults for NPCs / initial filesystem.
2. **Note CLI**: `note list/show/create/edit/delete` with 1-based index references and UUID prefix support.
3. **Task CLI**: `task lists/list/add/done/undone/delete` with auto-created default list and `--list` flag for multi-list support.
4. **Filesystem enhancements**: `grep` (regex, recursive, `-i`), `find` (glob matching, `-name`), `write` (create/overwrite file content).
5. **NPC improvements**: Think-tag stripping (`<think>...</think>` removed from qwen3 output), refined system prompt (brevity, stay in character, no meta-commentary), chat slash commands (`/help`, `/relationship`, `/status`).
6. **Integration tests**: Full command workflows for notes, tasks, filesystem, persistence round-trips, and chat listing.
7. **TUI apps**: Deferred to Phase 3 (requires raw mode design, better co-designed with browser terminal).
8. 255 total tests (83 new), all passing. Lint and type checks clean.

### Phase 3: WebSocket Terminal Protocol + CLI Client
**Goal**: The shell runs over WebSocket with a structured protocol. Both Claude Code and humans can drive it from a terminal client, exercising the exact same code path the browser will use later.

**Design decisions**:
- **Separate `/ws/terminal` endpoint** — the existing `/ws` handles NPC/app queries (request/response); terminal sessions are long-lived and stream output. Clean separation.
- **Client-side line editing** — server receives complete command lines, not keystrokes. Tab completion is a separate request/response message type. Lower latency sensitivity, simpler protocol.
- **No prompt_toolkit over WebSocket** — prompt_toolkit is used only by the local CLI entry point. The WebSocket path uses its own input abstraction.
- **ANSI codes pass through** — programs emit ANSI via `Output.styled()`, both xterm.js and real terminals render them natively. No translation layer.
- **No new dependencies** — FastAPI + websockets (already installed) handles everything.

Tasks:
1. **Transport abstraction in Shell**: Extract an `InputSource` protocol from the prompt_toolkit coupling in `shell.py`. The Shell receives lines from any source — prompt_toolkit (CLI), a WebSocket queue, or a test mock.
2. **WebSocket output adapter**: `WebSocketOutput` subclass of `Output` that sends output as structured JSON messages instead of writing to a stream.
3. **Terminal session manager**: New `/ws/terminal` endpoint. Each connection gets its own `Shell` instance backed by the shared `ServiceContainer`. Manages lifecycle: connect → create session → exchange commands/output → disconnect.
4. **WebSocket message protocol** (cooked mode):
   - Client → Server: `{"type": "input", "line": "ls -la"}`
   - Server → Client: `{"type": "output", "text": "..."}`, `{"type": "prompt", "text": "user@neon:~$ "}`, `{"type": "exit"}`
   - Tab completion: `{"type": "complete", "line": "ls Doc"}` → `{"type": "completions", "items": [...]}`
5. **WebSocket CLI client** (`python -m recursive_neon.wsclient`): A readline-based terminal client that connects to the backend via WebSocket. Same experience as local shell, but through the network stack. Supports `--command` flag for non-interactive use (send one command, get output, disconnect).
6. **Periodic auto-save**: Save game state on a timer (in addition to save-on-exit and manual `save` command), so WebSocket sessions don't lose progress on unexpected disconnect.
7. **Tests**: WebSocket session lifecycle, command round-trips, tab completion over WS, concurrent sessions.

### Phase 4: TUI Apps (Raw Mode)
**Goal**: Interactive full-screen apps that run inside the terminal, driven by keystroke input. Testable via both the local CLI and the WebSocket client from Phase 3.

Tasks:
1. Design raw mode protocol (server tells client to switch modes; client sends individual keystrokes)
2. TUI framework: screen buffer, cursor management, input handling
3. Build TUI apps (minigames, file browser, etc. — scope TBD)
4. Tests for raw mode switching and TUI app behavior

### Phase 5: Browser Terminal + Desktop GUI
**Goal**: The browser renders the same terminal experience, wrapped in the desktop UI.

Tasks:
1. Set up xterm.js connecting to `/ws/terminal` (same protocol as CLI client)
2. Cooked mode (shell) rendering in the browser
3. Raw mode (TUI apps) rendering in the browser
4. Desktop chrome: window manager, taskbar, desktop icons
5. Restore and refine the cyberpunk CSS theme from v1
6. Optionally add GUI-native apps (chat, file browser) that reuse the backend app core

## 7. Key Design Decisions for Future Sessions

- **Don't add features beyond what's tested and working.** V1's mistake was breadth without depth.
- **Every feature must work in CLI before browser.** No browser-only code paths for core functionality.
- **Keep the DI pattern.** ServiceContainer/ServiceFactory is the right approach. Extend it, don't replace it.
- **Virtual filesystem isolation is sacred.** Never compromise the UUID-based FileNode system. See `FILESYSTEM_SECURITY.md`.
- **The legacy branch is reference, not a merge source.** Cherry-pick ideas and styling, don't merge code.

## 8. Reference: Legacy Branch

The full v1 codebase is available on `legacy/v1` (local) and `origin/legacy` (remote). Useful for:
- **CSS styling** — `frontend/src/styles/desktop.css` has the polished cyberpunk theme
- **Terminal design ideas** — `docs/terminal-design.md`, `docs/terminal-requirements.md`
- **Minigame designs** — `docs/minigames/` has detailed design docs for 4 games
- **Feature documentation** — notification, calendar, settings, time system docs
- **React component patterns** — Window.tsx, ChatApp.tsx had good architecture
