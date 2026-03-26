# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-03-26)
> **Status**: Phases 0-5 complete. Phase 6 (text editor + TUI apps) next. Browser GUI deferred to Phase 7.
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
    terminal.py                       # WebSocket terminal session manager (Phase 3)
    shell/                            # CLI shell package (Phase 1-5)
      __init__.py                     # Exports InputSource, Shell
      __main__.py                     # Entry point: python -m recursive_neon.shell
      builtins.py                     # cd, exit, export (modify shell state) + BUILTIN_COMPLETERS
      completion.py                   # CompletionContext, CompletionFn, per-command completers (Phase 5a)
      glob.py                         # Shell-level glob expansion against virtual FS (Phase 5b)
      output.py                       # ANSI output abstraction + CapturedOutput + QueueOutput
      parser.py                       # Tokenizer (Token, tokenize_ext), pipeline parser (Phase 5b/5c)
      path_resolver.py                # Virtual path → FileNode resolution
      session.py                      # ShellSession (cwd, env, history)
      shell.py                        # REPL loop, pipeline dispatch, InputSource protocol, completion
      keys.py                         # Platform-specific raw keystroke reading (shared by CLI + WS client)
      tui/                            # TUI framework (Phase 4)
        __init__.py                   # ScreenBuffer, TuiApp protocol, RawInputSource protocol
        runner.py                     # run_tui_app() lifecycle: mode switching, keystroke routing
      programs/
        __init__.py                   # ProgramRegistry + ProgramContext + Program protocol
        chat.py                       # NPC conversation sub-REPL with /commands
        codebreaker.py                # Mastermind-style TUI minigame (Phase 4)
        filesystem.py                 # ls, pwd, cat, mkdir, touch, rm, cp, mv, grep, find, write
        notes.py                      # note list/show/create/edit/delete
        tasks.py                      # task lists/list/add/done/undone/delete
        utility.py                    # help, clear, echo, env, whoami, hostname, date, save
    wsclient/                         # WebSocket CLI client (Phase 3)
      __init__.py
      __main__.py                     # Entry point: python -m recursive_neon.wsclient
      client.py                       # Interactive WS client using prompt_toolkit
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
    unit/test_main.py                 # HTTP endpoints + WebSocket /ws tests
    unit/test_npc_manager.py          # NPC registration, chat, persistence, think-tag tests
    unit/test_terminal.py             # WebSocket terminal: session manager, QueueOutput, /ws/terminal
    unit/shell/__init__.py
    unit/shell/conftest.py            # Shell test fixtures (test_container, make_ctx, output)
    unit/shell/test_builtins.py       # cd, exit, export tests
    unit/shell/test_completion.py     # Tab completion helper tests (cursor parsing, quoting)
    unit/shell/test_context_completion.py  # Context-sensitive per-command completion (Phase 5a)
    unit/shell/test_glob.py           # Glob expansion: tokenize_ext, expand_globs (Phase 5b)
    unit/shell/test_pipeline.py       # Pipes, redirection, parse_pipeline (Phase 5c)
    unit/shell/test_filesystem_enhanced.py  # grep, find, write tests
    unit/shell/test_note_program.py   # Note CLI program tests
    unit/shell/test_parser.py         # Tokenizer tests
    unit/shell/test_path_resolver.py  # Path resolution tests
    unit/shell/test_programs.py       # Filesystem + utility program tests
    unit/shell/test_shell_integration.py  # Shell.execute_line dispatch tests
    unit/shell/test_task_program.py   # Task CLI program tests
    unit/shell/test_tui.py            # TUI framework: ScreenBuffer, runner lifecycle (Phase 4)
    unit/shell/test_codebreaker.py    # CodeBreaker: game logic, TUI app, key handling (Phase 4)
    integration/__init__.py
    integration/conftest.py           # Integration test fixtures (shell, tmp_game_dir)
    integration/test_full_flows.py    # End-to-end workflow tests

docs/
  ARCHITECTURE.md                     # Why Ollama, system architecture
  BACKEND_CONVENTIONS.md              # Python style, DI, testing patterns
  QUICKSTART.md                       # Setup guide
  SHELL_DESIGN.md                     # CLI shell architecture and design
  TECH_DEBT.md                        # Tech debt tracker (workarounds, deferred fixes)

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

3. ~~**`npc_manager.py` uses LangChain ConversationChain**~~ — **Resolved.** Migrated to direct LLM invocation via `langchain_core.messages`. `ConversationChain` and `ConversationBufferWindowMemory` removed; the NPC model's own conversation history is used directly.

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

### Phase 3: WebSocket Terminal Protocol + CLI Client — **COMPLETE**
**Goal**: The shell runs over WebSocket with a structured protocol. Both Claude Code and humans can drive it from a terminal client, exercising the exact same code path the browser will use later.

**Design decisions**:
- **Separate `/ws/terminal` endpoint** — the existing `/ws` handles NPC/app queries (request/response); terminal sessions are long-lived and stream output. Clean separation.
- **Client-side line editing** — server receives complete command lines, not keystrokes. Tab completion is a separate request/response message type. Lower latency sensitivity, simpler protocol.
- **No prompt_toolkit over WebSocket** — prompt_toolkit is used only by the local CLI entry point. The WebSocket path uses its own input abstraction.
- **ANSI codes pass through** — programs emit ANSI via `Output.styled()`, both xterm.js and real terminals render them natively. No translation layer.
- **No new dependencies** — FastAPI + websockets (already installed) handles everything.
- **Session manager owns sessions** — sessions are decoupled from WebSocket connection lifecycle, enabling future persistent/named sessions without architectural changes.

Completed:
1. **Transport abstraction**: `InputSource` protocol decouples Shell from prompt_toolkit. `PromptToolkitInput` for CLI, `WebSocketInput` for WS, test mocks possible. prompt_toolkit imports are fully lazy.
2. **`QueueOutput` adapter**: `Output` subclass that pushes messages to an `asyncio.Queue` for WebSocket delivery. ANSI codes preserved.
3. **`TerminalSessionManager`**: Owns Shell instances by UUID, independent of WebSocket lifecycle. Creates/removes sessions, manages auto-save background task.
4. **`/ws/terminal` endpoint**: JSON protocol with `input`, `output`, `prompt`, `complete`/`completions`, `exit`, `error` message types. Concurrent reader/writer tasks per connection.
5. **WebSocket CLI client** (`python -m recursive_neon.wsclient`): Interactive prompt_toolkit-based client with `--host`/`--port` flags. Tab completion via `_WebSocketCompleter` (async generator). ANSI colors rendered correctly via `patch_stdout(raw=True)` + Windows VT processing. `--command` batch mode deferred (architecture supports it; persistent sessions needed first for it to be useful).
6. **Periodic auto-save**: Background task saves game state every 60s while WebSocket sessions are active. Also saves on session disconnect.
7. **`ProgramContext.get_line`**: Programs can read user input through the shell's `InputSource`, so sub-REPLs (like `chat`) work over both CLI and WebSocket.
8. **Chat UX improvements**: All slash commands use `/` prefix (`/exit`, `/help`, `/relationship`, `/status`). Animated typing indicator ("NPC is typing...") while waiting for LLM response.
9. **Tests**: 28 new tests — QueueOutput, WebSocketInput, session manager lifecycle, shell start/stop/feed/exit, tab completion (incl. `get_completions_ext`), WebSocket completer, auto-save, and 8 WebSocket integration tests. 345 total tests, all passing.

### Phase 4: TUI Apps (Raw Mode) — **COMPLETE**
**Goal**: Interactive full-screen apps that run inside the terminal, driven by keystroke input. Testable via both the local CLI and the WebSocket client from Phase 3.

Completed:
1. **Raw mode protocol**: Server sends `{"type": "mode", "mode": "raw"|"cooked"}` to switch modes. Client sends `{"type": "key", "key": "..."}` for keystrokes in raw mode. Mode-aware message routing ignores wrong-mode messages.
2. **TUI framework** (`shell/tui/`): `ScreenBuffer` (2D text grid with cursor), `TuiApp` protocol (`on_start`/`on_key`/`on_resize`), `RawInputSource` protocol, `run_tui_app()` lifecycle manager.
3. **CodeBreaker minigame**: Mastermind-style TUI game with ANSI-colored rendering, arrow key navigation, symbol cycling, win/loss detection. Registered as `codebreaker` shell command.
4. **Local terminal support**: `LocalRawInput` for platform-specific keystroke reading + alternate screen buffer.
5. **WebSocket client raw mode**: Platform-specific raw key reading (Windows `msvcrt` / Unix `tty.setraw`). Headless mode (`--headless`) for automation.
6. **Tests**: 57 new tests — TUI framework (19), CodeBreaker (27), terminal raw mode + WS integration (11). 402 total tests, all passing.

### Phase 5: Context-Sensitive Completion + Shell Improvements — **COMPLETE**
**Goal**: Make the shell genuinely pleasant to use. Invest in completion infrastructure, glob expansion, and I/O redirection before adding new features — depth over breadth.

**Design decisions**:
- **Hybrid static + dynamic completion** — `CompletionFn` callbacks receive a `CompletionContext` with parsed args, partial text, and service access. Static subcommand lists and dynamic service queries (NPC IDs, note indices) use the same callback interface.
- **Glob expansion in the pipeline** — `tokenize_ext()` returns `Token(value, quoted)` with quoting metadata. Expansion runs after tokenization, before dispatch. Quoted tokens are never expanded. Unmatched globs pass through as literals (POSIX).
- **Buffered pipe semantics** — `CapturedOutput(color=False)` captures stdout as plain text. Piped text is passed via `ProgramContext.stdin`. Stderr always goes to real output. Builtins don't participate in pipes (deferred).
- **`**` recursive globs deferred** — single-level patterns (`*`, `?`, `[...]`) cover 95% of use cases.
- **Stderr redirection (`2>`, `2>&1`) out of scope** — only stdout redirection implemented.

Completed:
1. **Context-sensitive completion** (5a): New `shell/completion.py` with `CompletionContext`, `CompletionFn`, shared helpers. `ProgramRegistry` gains optional `completer` param. Per-command completers for all commands: `cd` (dirs-only), `ls`/`rm`/`grep`/`find` (flags + paths), `note`/`task` (subcommands + dynamic refs), `chat` (NPC IDs), `help` (all command names). Builtin completers via `BUILTIN_COMPLETERS` dict. `ShellCompleter` simplified to delegate to `get_completions_ext`. Works over WebSocket unchanged.
2. **Shell-level glob expansion** (5b): `Token` dataclass with `quoted` flag in `tokenize_ext()`. New `shell/glob.py` with `expand_globs()`. Pipeline: `tokenize_ext → expand_globs → dispatch`. Single-level patterns (`*`, `?`, `[...]`) matched via `fnmatch` against virtual filesystem children. Directories get trailing `/` in results.
3. **Pipes and output redirection** (5c): `parse_pipeline()` splits at unquoted `|`, `>`, `>>`. Pipeline segments execute sequentially with `CapturedOutput` for piping. `ProgramContext.stdin` added; `cat` and `grep` read from it. Redirect writes to virtual files (create or overwrite/append). Pipe-aware completion via `_last_pipe_segment()`.
4. **Tests**: 125 new tests — context-sensitive completion (58), glob expansion (33), pipes/redirection (34). Post-Phase 5 deep review added hardening and tests across the codebase. 568 total tests, all passing. Lint and type checks clean.

### Phase 6: Text Editor + TUI Apps
**Goal**: A capable TUI text editor ("neon-edit") and additional TUI apps that leverage it. The editor should work both in the terminal and (later) as a GUI app, making it a key investment before the browser phase.

#### 6a. Text editor ("neon-edit")
A lightweight Emacs-inspired TUI editor that the player can extend with Python scripts. This is a substantial feature — design carefully before implementing.

Tasks:
1. **Core editor model** — buffer abstraction (text + cursor + selection + undo), gap buffer or rope for efficient editing.
   *Design needed*: the editor model should be independent of the TUI framework so it can later be driven by a GUI. Consider a model-view split: `EditorBuffer` (pure logic, testable) + `EditorView` (TuiApp rendering).
2. **Basic editing** — cursor movement, insert/delete, line operations, scrolling, word wrap or horizontal scroll.
3. **Keybindings** — Emacs-like defaults (C-f/b/n/p for movement, C-a/e for line start/end, C-k for kill line, C-y for yank, C-x C-s for save, C-x C-c for quit). Keybinding table should be configurable.
4. **File I/O** — open/save virtual filesystem files. `neon-edit <path>` shell command.
5. **Python extension API** — player can write `.py` scripts that register commands, keybindings, or modes. Scripts run in a sandboxed environment with access to the editor buffer API.
   *Design needed*: how much of Emacs do we replicate? Start minimal (buffer, basic commands, configurable keybindings). Extension API can grow iteratively. Security boundary: scripts access the virtual filesystem, not the real one.
6. **Syntax highlighting** — at minimum for Python and the game's own scripting. Can start with a regex-based highlighter.
7. Tests for buffer operations, cursor movement, keybindings, file I/O round-trips.

#### 6b. Improved notes integration
With an editor available, the notes workflow improves dramatically.

Tasks:
1. `note edit <id>` opens the note in neon-edit instead of requiring inline `-c` flag
2. `note create` with no `-c` flag opens a blank editor
3. Optional: an editor "notes mode" that shows the note list as a sidebar/buffer
   *Design needed*: how tightly coupled should the editor and notes system be? Loose coupling via command-line args is simplest.

#### 6c. Additional TUI apps
More minigames and utilities to flesh out the game world.

Tasks (scope TBD — pick based on what's fun and tests the framework):
- File browser TUI (navigate virtual filesystem, preview files, open in editor)
- Port scanner minigame (network puzzle)
- Memory dump minigame (hex viewer puzzle)
- System monitor (fake htop showing game processes)

### Phase 7: Browser Terminal + Desktop GUI
**Goal**: The browser renders the same terminal experience, wrapped in the desktop UI.

Tasks:
1. Set up xterm.js connecting to `/ws/terminal` (same protocol as CLI client)
2. Cooked mode (shell) rendering in the browser
3. Raw mode (TUI apps) rendering in the browser
4. Desktop chrome: window manager, taskbar, desktop icons
5. Restore and refine the cyberpunk CSS theme from v1
6. Optionally add GUI-native apps (chat, file browser, editor) that reuse the backend app core

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
