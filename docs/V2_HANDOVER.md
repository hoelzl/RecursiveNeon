# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-03-27)
> **Status**: Phases 0-5 + 6a (editor) + E1-E5 (editor enhancements) + 6b (notes integration) complete. Phase 6c (additional TUI apps) or 6d (notes mode) next. Browser GUI deferred to Phase 7.
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

> **Archive**: Detailed descriptions of completed phases have been moved to [V2_HANDOVER-archive.md](./V2_HANDOVER-archive.md).

## 3. What Was Done (Phase 0) — **COMPLETE**
Created orphan branch `master` from curated v1 files. Stripped broken features (notifications, calendar, browser, media viewer, all React components, all minigames), kept solid architecture (DI, models, services, CSS theme). Old code preserved on `legacy/v1`.

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
    editor/                           # TUI text editor — neon-edit (Phase 6a + E1-E5)
      __init__.py                     # Package exports (Buffer, Mark, Editor, EditorView, etc.)
      buffer.py                       # Buffer class: text storage, primitives, movement, undo, kill, search
      mark.py                         # Mark class: position tracking with left/right-inserting kinds
      undo.py                         # Undo entry types (UndoInsert, UndoDelete, UndoBoundary)
      killring.py                     # Kill ring: push, append_to_top, yank, rotate
      commands.py                     # Command dataclass, @defcommand decorator, COMMANDS registry
      keymap.py                       # Keymap class: key bindings with parent inheritance
      editor.py                       # Editor coordinator: buffer list, key dispatch, prefix arg, help
      default_commands.py             # 40+ Emacs-style commands + global/C-x/C-h keymaps
      minibuffer.py                   # Single-line input widget with completion (M-x, C-x C-f, etc.)
      view.py                         # EditorView (TuiApp): rendering, scrolling, modeline
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
        edit.py                       # Shell `edit` command: TUI editor host, file I/O callbacks
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
    unit/editor/__init__.py
    unit/editor/test_buffer.py        # Buffer primitives, insertion, deletion, movement (101 tests)
    unit/editor/test_mark.py          # Mark comparison, copying, move_to (22 tests)
    unit/editor/test_undo.py          # Undo/redo round-trips, boundaries, chains (22 tests)
    unit/editor/test_killring.py      # Kill ring: push, rotate, append, kill merging (37 tests)
    unit/editor/test_keymap.py        # Keymap bind, lookup, parent inheritance (13 tests)
    unit/editor/test_commands.py      # Command registry, dispatch, prefix arg (40 tests)
    unit/editor/test_minibuffer.py    # Minibuffer input, completion, callbacks (38 tests)
    unit/editor/test_view.py          # EditorView rendering, scrolling, modeline (26 tests)
    unit/editor/test_word_movement.py # Word movement, additional keys, read-only buffers (30 tests)
    unit/editor/test_isearch.py       # Incremental search: find, isearch dispatch (21 tests)
    unit/editor/test_help.py          # Help system: describe-key, apropos (9 tests)
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

1. **`app_service.py` uses O(n) list scans** — all get/update operations iterate the full node/note/task lists. Fine for now, but should use dict-based lookup if collections grow large.

2. **`main.py` WebSocket handling is inline** — the `handle_ws_message()` function was inlined when we removed MessageHandler. This should eventually be refactored back into a proper service when the message protocol stabilizes.

## 6. Implementation Plan (Phases 1-5)

### Phase 1: Build the Python CLI Shell — **COMPLETE**
Shell package with REPL, builtins (`cd`/`exit`/`export`), filesystem programs, utility programs, NPC chat, tab completion, and command history. 172 tests.

### Phase 2: Deepen Core Features — **COMPLETE**
Persistence (JSON to `game_data/`), `note` and `task` CLI programs, filesystem enhancements (`grep`/`find`/`write`), NPC think-tag stripping, integration tests. 255 tests.

### Phase 3: WebSocket Terminal Protocol + CLI Client — **COMPLETE**
`/ws/terminal` endpoint with JSON protocol, `InputSource` abstraction, `QueueOutput`, `TerminalSessionManager`, WebSocket CLI client (`python -m recursive_neon.wsclient`), periodic auto-save. 345 tests.

### Phase 4: TUI Apps (Raw Mode) — **COMPLETE**
Raw/cooked mode protocol, TUI framework (`ScreenBuffer`, `TuiApp`, `run_tui_app`), CodeBreaker minigame, platform-specific raw key reading, headless WS client mode. 402 tests.

### Phase 5: Context-Sensitive Completion + Shell Improvements — **COMPLETE**
Per-command tab completers, shell-level glob expansion (`*`/`?`/`[...]`), pipes (`|`), output redirection (`>`/`>>`), `ProgramContext.stdin`. 568 tests.

### Phase 6: Text Editor + TUI Apps
**Goal**: A capable TUI text editor ("neon-edit") and additional TUI apps that leverage it. The editor should work both in the terminal and (later) as a GUI app, making it a key investment before the browser phase.

#### 6a. Text editor ("neon-edit") — **COMPLETE**
Emacs-inspired TUI editor (Zwei/Hemlock lineage): `Buffer`/`Mark` text model, undo/kill ring, `@defcommand` + layered keymaps, `EditorView` TUI, shell `edit` command with virtual filesystem I/O. Enhancements E1-E5 added word movement, read-only buffers, minibuffer (M-x, C-x C-f, C-x b), incremental search (C-s/C-r), and help system (C-h k, C-h a). 927 total tests.

##### 6a-5. Modes (optional, not yet implemented)
- `Mode` dataclass: `name`, `keymap`, `is_major`, `variables`, `on_enter`/`on_exit`
- Fundamental mode (default), Text mode as examples
- Buffer-local variable overrides

##### Future 6a extensions (not yet scheduled)
- Python extension API (player scripts register commands/keybindings/modes in sandboxed env)
- Syntax highlighting (regex-based, at minimum for Python)

#### 6b. Improved notes integration — **COMPLETE**
With the editor available, notes commands open neon-edit for interactive editing using a `# Title` first-line convention.

- `note edit <ref>` opens the note in neon-edit (first line `# Title`, rest is content). On save, title and content are parsed back. Inline flags (`-t`/`-c`) still work for backward compatibility.
- `note create <title>` without `-c` opens the editor pre-filled with `# Title`. On save, the note is created. The `-c` flag still creates immediately without the editor.
- When TUI mode is unavailable, `note edit` shows an error suggesting flags; `note create` falls back to creating an empty note.
- 946 total tests (19 new: format/parse helpers, editor integration for both create and edit, fallback paths).

#### 6c. Additional TUI apps
More minigames and utilities to flesh out the game world.

Tasks (scope TBD — pick based on what's fun and tests the framework):
- File browser TUI (navigate virtual filesystem, preview files, open in editor)
- Port scanner minigame (network puzzle)
- Memory dump minigame (hex viewer puzzle)
- System monitor (fake htop showing game processes)

#### 6d. Editor "notes mode"
An editor mode that surfaces the note list inside neon-edit, so the player can browse, open, and manage notes without leaving the editor.

*Design needed*: how tightly coupled should the editor and notes system be? Options:
- Loose coupling: a special `*Notes*` read-only buffer that lists notes; pressing Enter opens the selected note. Notes are just buffers with a save callback.
- Tighter coupling: a sidebar/split view showing the note list alongside the active note buffer.

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
