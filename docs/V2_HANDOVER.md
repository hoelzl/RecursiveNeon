# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-04-04)
> **Status**: Phases 0-6i complete (shell, persistence, WebSocket, TUI, completion/globs/pipes, editor + enhancements, notes integration, system monitor, notes browser, test harness + scrolling + tutorial, sentence motion + help commands + save-some-buffers, variable system + mode infrastructure, replace string + text filling, window system). 1282 tests. Phase 6j (shell-in-editor) next. Browser GUI deferred to Phase 8.
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
      process.py                      # Process, ProcessState models for system monitor (Phase 6c)
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
      editor.py                       # Editor coordinator: buffer list, key dispatch, prefix arg, help, remove_buffer
      default_commands.py             # 50+ Emacs-style commands + global/C-x/C-h keymaps (incl. scroll, tutorial)
      minibuffer.py                   # Single-line input widget with completion (M-x, C-x C-f, etc.)
      view.py                         # EditorView (TuiApp): rendering, scrolling, modeline, Viewport protocol
      viewport.py                     # Viewport protocol: scroll_top, text_height, scroll_to (Phase 6e)
      variables.py                    # EditorVariable, VARIABLES registry, defvar, built-in variables (Phase 6g)
      modes.py                        # Mode, MODES registry, defmode, fundamental-mode, text-mode (Phase 6g)
      window.py                       # Window, WindowSplit, WindowTree: Emacs-style window splitting (Phase 6i)
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
        notes.py                      # note list/show/create/edit/delete/browse (6b + 6d)
        sysmon.py                     # System monitor TUI: fake htop with process model (Phase 6c)
        tasks.py                      # task lists/list/add/done/undone/delete
        utility.py                    # help, clear, echo, env, whoami, hostname, date, save
    wsclient/                         # WebSocket CLI client (Phase 3)
      __init__.py
      __main__.py                     # Entry point: python -m recursive_neon.wsclient
      client.py                       # Interactive WS client using prompt_toolkit
    initial_fs/                       # Sample files for virtual filesystem init
      welcome.txt
      Documents/{readme.txt, sample.txt, my test file.txt, TUTORIAL.txt}
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
    unit/shell/test_note_program.py   # Note CLI program tests + notes browser (Phase 6d)
    unit/shell/test_sysmon.py         # System monitor TUI tests (Phase 6c)
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
    unit/editor/test_commands.py      # Command registry, dispatch, prefix arg (41 tests)
    unit/editor/test_minibuffer.py    # Minibuffer input, completion, callbacks, kill-buffer (38+17 tests)
    unit/editor/test_buffer_keymap.py # Buffer-local keymaps, callable targets, on_focus (Phase 6d)
    unit/editor/test_view.py          # EditorView rendering, scrolling, modeline (26 tests)
    unit/editor/test_word_movement.py # Word movement, additional keys, read-only buffers (30 tests)
    unit/editor/test_isearch.py       # Incremental search: find, isearch dispatch (21 tests)
    unit/editor/test_help.py          # Help system: describe-key, apropos, tutorial (14 tests)
    unit/editor/harness.py            # EditorHarness: TUI-level test driver (Phase 6e)
    unit/editor/test_harness.py       # Harness self-tests (14 tests, Phase 6e)
    unit/editor/test_scroll.py        # Viewport scroll commands + recenter (22 tests, Phase 6e)
    unit/editor/test_sentence.py      # Sentence motion + kill (22 tests, Phase 6f)
    unit/editor/test_phase6f.py       # Phase 6f commands: keybindings, help, save-some-buffers (25 tests)
    unit/editor/test_variables.py     # Variable system: defvar, validation, cascade, commands (29 tests, Phase 6g)
    unit/editor/test_modes.py         # Mode system: registry, switching, keymaps, modeline (23 tests, Phase 6g)
    unit/editor/test_replace.py       # Replace string: basic, from-point, undo, cancel (13 tests, Phase 6h)
    unit/editor/test_fill.py          # Fill paragraph, set-fill-column, auto-fill-mode (30 tests, Phase 6h)
    unit/editor/test_window.py        # Window/WindowTree: create, split, delete, navigate, point tracking (30 tests, Phase 6i)
    unit/editor/test_window_view.py   # Window rendering: compat, splits, modelines, dividers, resize (15 tests, Phase 6i)
    unit/editor/test_window_commands.py # Window commands: split, navigate, delete, scroll-other, find-file-other (22 tests, Phase 6i)
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

#### 6c. System monitor TUI — **COMPLETE**
A fake "htop"-style system monitor showing in-game processes. `Process` and `ProcessState` models in `models/process.py`. `sysmon` shell command launches the TUI with animated CPU/memory bars, process list, and sort/kill key bindings. 980 total tests.

Future 6c candidates (not yet scheduled):
- File browser TUI (navigate virtual filesystem, preview files, open in editor)
- Port scanner minigame (network puzzle)
- Memory dump minigame (hex viewer puzzle)

#### 6d. Notes browser in neon-edit — **COMPLETE**
Interactive notes browser inside the editor. Loose coupling approach: a `*Notes*` read-only buffer with buffer-local keymap lists notes; Enter opens a note in a new buffer with `# Title` convention and save callback.

- `note browse` command opens neon-edit with the `*Notes*` buffer
- Buffer-local keymaps: `Buffer.keymap` field, checked first by `_resolve_keymap()`, falls through to global via parent
- Callable keymap targets: `BindingTarget` now accepts `Callable[..., Any]` alongside command name strings
- `Buffer.on_focus` callback: triggered on `switch_to_buffer` / `remove_buffer`, used to auto-refresh the note list
- `kill-buffer` command (C-x k): remove a buffer with minibuffer prompt
- Improved prefix key display: "C-x z is undefined" instead of "z is undefined"
- Windows C-h / Backspace disambiguation via `_win_ctrl_pressed()`
- 1031 total tests (51 new: 12 notes browser, 8 buffer-local keymaps, 7 callable targets, 5 kill-buffer, 3 prefix display, 3 on_focus, plus supporting tests).

#### 6e. Test harness + viewport scrolling + tutorial document — **COMPLETE**
Programmatic test harness for TUI-level editor testing, viewport scrolling commands, game-themed tutorial document, and a bugfix for C-u prefix digit parsing.

- `EditorHarness` class (`tests/unit/editor/harness.py`): `send_keys(*keys)`, `type_string(s)`, `screen_text(row)`, `screen_lines()`, `cursor_position()`, `message_line()`, `modeline()`, `buffer_text()`, `point()`. Factory: `make_harness(text, width, height)`. ANSI auto-stripping on all screen accessors.
- `Viewport` protocol (`editor/viewport.py`): `scroll_top`, `text_height`, `scroll_to`. EditorView implements it and sets `editor.viewport = self`. Commands fall back gracefully when viewport is None (headless).
- `scroll-up` (C-v / PageDown): forward one screenful, move point to top of new viewport
- `scroll-down` (M-v / PageUp): backward one screenful, move point to bottom of new viewport
- `recenter` (C-l): center viewport around point; consecutive presses cycle center/top/bottom
- Tutorial document (`initial_fs/Documents/TUTORIAL.txt`): ~280-line game-themed tutorial (Apache 2.0), Emacs tutorial pedagogical structure, 14 chapters. Chapters 10-14 marked `[NOT YET IMPLEMENTED]`.
- `help-tutorial` (C-h t): opens the tutorial in a read-only buffer; re-opening switches to existing buffer
- Bugfix: C-u prefix digit parsing — `_prefix_has_digits` now properly initialized and reset, fixing a bug where digits after C-u failed to replace the default 4 after any prior command had executed
- 1073 total tests (42 new: 14 harness, 22 scroll/viewport, 5 tutorial, 1 prefix-arg fix)

#### 6f. Sentence motion, undo alias, help commands, save-some-buffers — **COMPLETE**
**Goal**: Implement the "easy" missing tutorial commands — straightforward features that don't require new infrastructure.

- Sentence motion on Buffer: `forward_sentence`, `backward_sentence`, `kill_sentence` (sentence ends at `.`/`?`/`!` followed by whitespace or end-of-line)
- `backward-sentence` (M-a), `forward-sentence` (M-e), `kill-sentence` (M-k)
- `C-x u` → undo (keybinding alias in C-x prefix keymap)
- `describe-key-briefly` (C-h c): show binding in message area (not *Help* buffer)
- `describe-mode` (C-h m): show current mode and key bindings in *Help* buffer, recurses into prefix keymaps
- `where-is` (C-h x): prompt for command name, show which key(s) it's bound to (reverse keymap lookup via `Keymap.reverse_lookup()`)
- `save-some-buffers` (C-x s): iterate modified buffers with y/n minibuffer prompt, save confirmed ones via chained callbacks
- 1120 total tests (47 new: 22 sentence motion/kill, 25 commands/keybindings/help/save-some-buffers/reverse-lookup)

#### 6g. Variable system + mode infrastructure — **COMPLETE**
**Goal**: Implement an editor variable system with Python-based configuration and a mode infrastructure. Foundation for fill-column, auto-fill-mode, and per-mode keymaps. Also enables future in-game extensibility.

- `EditorVariable` dataclass (`editor/variables.py`): `name`, `default`, `doc`, `type`. Global `VARIABLES` registry. `defvar()` registration function. Type validation with coercion (int, bool, float, str).
- `Editor.get_variable(name)`: checks buffer-local → minor mode → major mode → global default
- `Editor.set_variable(name, value)`, `Buffer.set_variable_local(name, value)`, `Buffer.local_variables` dict
- Built-in variables: `fill-column` (70), `tab-width` (8), `indent-tabs-mode` (False), `truncate-lines` (True), `auto-fill` (False)
- `describe-variable` (C-h v): prompt with completion, show value + docs + buffer-local status in *Help* buffer
- `set-variable` (M-x set-variable): two-step minibuffer prompts (name + value), validate type, set global default
- `Mode` dataclass (`editor/modes.py`): `name`, `keymap`, `is_major`, `variables`, `on_enter`/`on_exit`, `doc`. Global `MODES` registry. `defmode()` registration function.
- `Editor.set_major_mode(name)`: switches major mode with lifecycle hooks. `Editor.toggle_minor_mode(name)`: enable/disable minor modes.
- `Buffer.major_mode`, `Buffer.minor_modes`. Keymap resolution updated: buffer-local > minor mode > major mode > global.
- Built-in modes: `fundamental-mode` (default, auto-assigned to new buffers), `text-mode` (sets auto-fill True)
- `describe-mode` (C-h m) updated: shows major mode name + doc, minor modes list, then key bindings
- Modeline updated: shows mode name (e.g., `(Fundamental)`, `(Text)`) and minor mode indicators, with smart truncation for narrow windows
- Python-based configuration file support deferred — the variable/mode API is fully functional via commands and programmatic access
- 1172 total tests (52 new: 29 variable system, 23 mode system)

#### 6h. Replace string + text filling — **COMPLETE**
**Goal**: Implement the text manipulation commands the tutorial covers: interactive find/replace and paragraph filling.

- `replace-string` (M-x replace-string): two sequential minibuffer prompts (search, replacement), replaces all from point to end of buffer, reports count, undoable as one group
- `fill-paragraph` (M-q): rewrap current paragraph to `fill-column` width, paragraph boundaries at blank lines. Helpers: `_find_paragraph_bounds()` (blank-line delimited), `_fill_lines()` (word-wrap reflow)
- `set-fill-column` (C-x f): with prefix arg sets to that value, without sets to current column
- `auto-fill-mode` (M-x auto-fill-mode): minor mode toggle, auto-breaks lines at fill-column during self-insert via `_auto_fill_break()` hook in `self-insert-command`. Modeline shows "Fill" when active.
- `Mode.indicator` field: optional short modeline string for minor modes (falls back to name-derived string if empty)
- 1215 total tests (43 new: 13 replace-string, 5 paragraph bounds, 6 fill-lines, 9 fill-paragraph, 3 set-fill-column, 7 auto-fill-mode)

#### 6i. Window system — **COMPLETE**
**Goal**: Emacs-style window splitting so a single frame displays multiple buffers simultaneously. The prerequisite for shell-in-editor and the "desktop environment" vision.

**Architecture**:
- `Window` class (`editor/window.py`): `buffer`, `_point` (tracked Mark), `scroll_top`, layout fields (`_height`, `_width`, `_top`, `_left`). Implements `Viewport` protocol (`scroll_top`, `text_height`, `scroll_to`). Factory `Window.for_buffer(buf)` creates a window with a tracked mark at the buffer's point.
- `SplitDirection` enum: `HORIZONTAL` (C-x 2, top/bottom), `VERTICAL` (C-x 3, left/right)
- `WindowSplit` dataclass: `direction`, `first` (WindowNode), `second` (WindowNode). `WindowNode = Window | WindowSplit`.
- `WindowTree` class: manages the binary split tree. `root: WindowNode`, `active: Window`. Methods: `split()`, `delete_window()`, `next_window()`, `windows()` (depth-first leaf list), `delete_other_windows()`, `is_single()`, `other_window()`.

**Dual-point sync**: `Window._point` is a tracked Mark in the buffer (maintained by mark tracking during insert/delete). Movement commands only move `buffer.point`, so EditorView syncs after each key: `active._point ← buffer.point`. On window switch: save old `buffer.point → old._point`, restore `new._point → buffer.point`, update `editor.viewport` to new window, switch editor's current buffer. Existing 1215+ headless tests see `_window_tree = None` and are unaffected.

**EditorView refactored**: creates a `WindowTree` on init (single root window). `_render()` walks the tree: `_compute_layout()` assigns regions, `_render_window()` draws text + modeline per window, `_render_dividers()` draws `│` columns for vertical splits. Active modeline: `\033[7m` (reverse), inactive: `\033[2;7m` (dim reverse). Message line is global (last screen row). `ScreenBuffer.set_region()` added for column-range writes.

**Single-window equivalence**: window height = `total - 1` (message), text_height = `height - 1` (modeline), so text_height = `total - 2`. Identical to current layout. All existing TUI tests produce same output.

**Commands**: `split-window-below` (C-x 2), `split-window-right` (C-x 3), `other-window` (C-x o), `delete-window` (C-x 0), `delete-other-windows` (C-x 1), `scroll-other-window` (C-M-v), `find-file-other-window` (C-x 4 C-f). New `C-x 4` prefix keymap.

**Files**: new `editor/window.py`, modified `editor/editor.py` (+1 field), `editor/view.py` (refactored), `editor/default_commands.py` (+7 commands), `shell/tui/__init__.py` (+`set_region`), `editor/__init__.py` (exports). Tests: `test_window.py`, `test_window_view.py`, `test_window_commands.py` (~65 new tests).

#### 6j. Shell-in-editor (shell mode)
**Goal**: Run the game's shell inside an editor window, like Emacs `M-x shell`. The keystone feature that makes neon-edit the game's "desktop environment."

- Shell mode (`editor/shell_mode.py`): major mode with `shell-mode-map` keymap. Output region read-only, input region after prompt editable.
- Comint model with in-process Shell: `ShellBufferInput` (asyncio queue, feeds lines on Enter) and `ShellBufferOutput` (appends text to buffer at output marker). No subprocess — our Shell is a Python object.
- `shell` (M-x shell): creates `*shell*` buffer in shell mode, wires to Shell instance
- `comint-send-input` (Enter in shell mode): send input line to shell
- `comint-previous-input` (M-p) / `comint-next-input` (M-n): history navigation
- Tab completion in shell buffer reuses shell's completion infrastructure
- Raw-mode TUI apps inside the shell buffer are **deferred** — only cooked-mode shell interaction in this phase

#### 6k. Tutorial verification + polish
**Goal**: Verify every feature in the tutorial works end-to-end. Fix gaps, polish UX.

- Integration test: programmatic walk-through of entire tutorial using EditorHarness, verifying expected behavior for every exercise
- Remove all `[NOT YET IMPLEMENTED]` tags from TUTORIAL.txt
- `describe-bindings` (C-h b): show all active keybindings in *Help* buffer
- Modeline improvements: show major mode name, minor mode indicators
- Edge case fixes discovered during walk-through
- Documentation updates (handover, CLAUDE.md, SHELL_DESIGN.md)
- Add neon-edit-specific sections to tutorial (shell mode, Python config, game world integration)

### Phase 8: Browser Terminal + Desktop GUI
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
