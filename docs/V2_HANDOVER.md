# V2 Handover Document

> **Date**: 2025-03-23
> **Status**: Phase 0 complete (branch setup & file curation). Phase 1 not started.
> **Branch**: `main` (orphan branch, 1 commit: `384e373`)

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
- Created orphan branch `main`
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
  .coveragerc                         # Coverage config
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
      app_service.py                  # Filesystem + Notes + Tasks CRUD, persistence
      interfaces.py                   # INPCManager, IOllamaClient, IProcessManager
      npc_manager.py                  # LangChain-based NPC conversation manager
      ollama_client.py                # httpx async client for Ollama API
      process_manager.py              # Ollama binary process lifecycle
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
    unit/test_app_service.py          # Notes, Tasks, FileSystem CRUD tests
    unit/test_filesystem_security.py  # Security isolation tests
    unit/test_npc_manager.py          # NPC registration, chat, relationship tests
    integration/__init__.py

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

1. **No Python venv exists** — the old `.venv` was stale (referenced Python 3.13 which is no longer installed). System Python is 3.14.3. A new venv needs to be created: `python -m venv .venv && .venv/Scripts/pip install -e "backend[dev]"`

2. **CLAUDE.md is outdated** — it describes the v1 architecture extensively. It should be rewritten for v2 once the new architecture stabilizes. For now, this handover document is the primary reference.

3. **`npc_manager.py` uses LangChain ConversationChain** — this was marked for potential simplification. ConversationBufferMemory has unbounded growth. Not blocking, but worth noting.

4. **`app_service.py` uses O(n) list scans** — all get/update operations iterate the full node/note/task lists. Fine for now, but should use dict-based lookup if collections grow large.

5. **`main.py` WebSocket handling is inline** — the `handle_ws_message()` function was inlined when we removed MessageHandler. This should eventually be refactored back into a proper service when the message protocol stabilizes.

6. **Remote `origin/master` still exists** — the remote hasn't been updated. The `main` branch hasn't been pushed yet. When ready: `git push -u origin main` and consider cleaning up old remote branches.

## 6. Implementation Plan (Phases 1-3)

### Phase 1: Build the Python CLI Shell
**Goal**: A working command-line shell that runs in any terminal via `python -m recursive_neon.shell`.

Tasks:
1. Create a new venv and verify all existing tests pass
2. Design the shell architecture:
   - `backend/src/recursive_neon/shell/` — new package
   - `session.py` — terminal session state (cwd, env vars, history)
   - `shell.py` — REPL loop, line editing (use Python's `readline` or `prompt_toolkit`)
   - `commands/` — command implementations (ls, cd, cat, mkdir, rm, cp, mv, echo, etc.)
   - `commands/chat.py` — `chat <npc_name>` drops into conversation mode
3. Implement filesystem commands first (ls, cd, pwd, cat, mkdir, touch, rm, cp, mv)
   - These operate on the virtual filesystem via `AppService`
   - Output should use ANSI colors for a polished terminal feel
4. Implement `help`, `clear`, `echo`, `env` utility commands
5. Implement `chat <npc>` command — enters conversation mode with an NPC
6. Add tab completion (command names, file paths)
7. Add command history (up/down arrows)
8. Write tests for each command
9. **Verify Claude Code can run the shell** and interact with it programmatically

### Phase 2: Deepen Core Features
**Goal**: The 3 core systems (filesystem, NPC chat, notes/tasks) work flawlessly in CLI.

Tasks:
1. Add `note` and `task` CLI commands for managing notes and tasks
2. Add more filesystem features (file content editing, grep/find within virtual FS)
3. Improve NPC conversations — test with actual Ollama, refine prompts
4. Add integration tests for full command flows
5. Consider TUI apps using `rich` or `textual` for richer terminal UI (e.g., a notes editor, task board)
6. Add persistence — save/load shell history, game state survives restart

### Phase 3: Browser Terminal + Desktop GUI
**Goal**: The CLI experience runs in the browser, wrapped in the desktop UI.

Tasks:
1. Set up xterm.js (or equivalent) in the frontend
2. Create a WebSocket protocol for terminal sessions:
   - Backend manages a virtual PTY/session
   - Frontend sends keystrokes, receives screen updates
3. Support cooked mode (shell) and raw mode (TUI apps) switching
4. Add the desktop chrome: window manager, taskbar, desktop icons
5. Terminal windows can run the same commands as the CLI
6. Optionally add GUI apps (chat, file browser) that reuse the backend app core
7. Restore and refine the CSS theme from v1

## 7. Key Design Decisions for Future Sessions

- **Don't add features beyond what's tested and working.** V1's mistake was breadth without depth.
- **Every feature must work in CLI before browser.** No browser-only code paths for core functionality.
- **Keep the DI pattern.** ServiceContainer/ServiceFactory is the right approach. Extend it, don't replace it.
- **Virtual filesystem isolation is sacred.** Never compromise the UUID-based FileNode system. See `FILESYSTEM_SECURITY.md`.
- **The legacy branch is reference, not a merge source.** Cherry-pick ideas and styling, don't merge code.

## 8. Reference: Legacy Branch

The full v1 codebase is available on `legacy/v1` (local) and `origin/master` (remote). Useful for:
- **CSS styling** — `frontend/src/styles/desktop.css` has the polished cyberpunk theme
- **Terminal design ideas** — `docs/terminal-design.md`, `docs/terminal-requirements.md`
- **Minigame designs** — `docs/minigames/` has detailed design docs for 4 games
- **Feature documentation** — notification, calendar, settings, time system docs
- **React component patterns** — Window.tsx, ChatApp.tsx had good architecture
