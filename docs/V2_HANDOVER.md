# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-04-04)
> **Status**: Phases 0-6k complete. 1433 tests. **Phase 6l (Emacs polish: keyboard-quit audit, keyboard-escape-quit + ESC-as-Meta, true incremental search, query-replace, and deferred items) is next**, then Phase 8 (browser terminal + desktop GUI). Detailed descriptions of phases 6b-6k have been moved to [V2_HANDOVER-archive.md](./V2_HANDOVER-archive.md).
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
      shell_mode.py                   # Shell-in-editor: BufferOutput, ShellState, comint commands, M-x shell (Phase 6j)
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
    unit/editor/test_shell_mode.py    # Shell-in-editor: setup, comint commands, history, completion, execution (66 tests, Phase 6j)
    unit/editor/test_tutorial_walkthrough.py  # Tutorial walk-through: every chapter exercised via EditorHarness (72 tests, Phase 6k)
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
Emacs-inspired TUI editor (Zwei/Hemlock lineage): `Buffer`/`Mark` text model, undo/kill ring, `@defcommand` + layered keymaps, `EditorView` TUI, shell `edit` command with virtual filesystem I/O. Enhancements E1-E5 added word movement, read-only buffers, minibuffer (M-x, C-x C-f, C-x b), search (C-s/C-r), and help system (C-h k, C-h a). 927 total tests. See archive for full 6a-1..6a-4 / E1..E5 breakdown.

#### 6b–6k. Editor expansion — **COMPLETE**
Phases 6b through 6k extended neon-edit from a basic buffer/keymap into a near-complete Emacs-style environment. Detailed notes for every sub-phase live in [V2_HANDOVER-archive.md](./V2_HANDOVER-archive.md). Summary of what shipped and the test count at the end of each:

- **6b. Notes integration** (946 tests) — `note edit` / `note create` open neon-edit with `# Title` convention.
- **6c. System monitor TUI** (980 tests) — `sysmon` fake htop with process model.
- **6d. Notes browser** (1031 tests) — buffer-local keymaps, callable targets, `on_focus`, `kill-buffer` (C-x k).
- **6e. Test harness + scrolling + tutorial** (1073 tests) — `EditorHarness`, `Viewport` protocol, `scroll-up`/`scroll-down`/`recenter`, `TUTORIAL.txt`, `help-tutorial` (C-h t).
- **6f. Sentence motion + help commands + save-some-buffers** (1120 tests) — M-a/M-e/M-k, C-x u, `describe-key-briefly` (C-h c), `describe-mode` (C-h m), `where-is` (C-h x), `save-some-buffers` (C-x s).
- **6g. Variable system + mode infrastructure** (1172 tests) — `EditorVariable`/`VARIABLES`/`defvar`, `Mode`/`MODES`/`defmode`, `fundamental-mode`/`text-mode`, `describe-variable` (C-h v), `set-variable`, buffer-local variables, keymap resolution through mode stack.
- **6h. Replace string + text filling** (1215 tests) — `replace-string`, `fill-paragraph` (M-q), `set-fill-column` (C-x f), `auto-fill-mode`, `Mode.indicator` field.
- **6i. Window system** (1281 tests) — `Window`/`WindowSplit`/`WindowTree`, dual-point sync via tracked marks, `C-x 2`/`C-x 3`/`C-x o`/`C-x 0`/`C-x 1`/`C-x 4` prefix, active/inactive modelines.
- **6j. Shell-in-editor** (1348 tests) — `M-x shell`, `BufferOutput`, `ShellState`, shell-mode keymap, `on_after_key` async bridge, direct-execution model.
- **6k. Tutorial verification + polish** (1433 tests) — tutorial walk-through integration tests, `describe-bindings` (C-h b), TUTORIAL.txt cleanup.

### Phase 6l: Emacs polish — **NEXT**
**Goal**: Make the editor genuinely *feel* like Emacs. Implement the cancellation, search, and replace workflows that are cornerstones of the Emacs experience, plus resolve a backlog of small deferred items carried forward from earlier phases. This is the final pre-browser polish pass on the editor.

#### 6l-1. `keyboard-quit` audit and hardening (C-g)
`keyboard-quit` already exists (`default_commands.py:282`), is bound to `C-g` in the global keymap (`default_commands.py:1210`), and the minibuffer handles `C-g` directly (`minibuffer.py:79`). Isearch installs its own `C-g` override (`default_commands.py:502-512`). The work here is to **audit, test, and harden**:
- C-g cancels a pending prefix keymap (mid-`C-x` sequence) and clears `_prefix_arg` / `_building_prefix`
- C-g cancels the minibuffer and restores pre-entry state (point, mark, buffer)
- C-g cancels `execute-extended-command` mid-typing
- C-g cancels `describe-key` / `describe-key-briefly` capture modes
- C-g cancels the new `query-replace` (see 6l-4) cleanly
- C-g clears the transient region/mark in all cases
- C-g consistently shows `"Quit"` in the message area

Add explicit unit tests for each cancellation path, grouped in `test_keyboard_quit.py`.

#### 6l-2. `keyboard-escape-quit` + ESC-as-Meta
New command `keyboard-escape-quit` — the "do everything C-g does, plus dismiss temporary windows". In our editor it should:
- Dismiss the `*Help*` buffer if currently displayed (switch back to previous buffer)
- Exit `query-replace` / `describe-key` capture modes
- Dismiss the minibuffer
- Clear mark/region, prefix-arg, pending keymap

Bind it to **`ESC ESC ESC`** (triple Escape). Also available as `M-ESC ESC` once ESC becomes a Meta prefix.

**ESC-as-Meta**: Today ESC is only handled inside the minibuffer/isearch as a cancel key. In real Emacs, ESC is a valid Meta prefix — `ESC f` is equivalent to `M-f`, `ESC x` to `M-x`, etc. Implement this in `Editor.process_key`:
- On bare ESC, set an internal `_meta_pending` flag.
- The next keystroke is rewritten as `M-<key>` before keymap lookup. Printable keys become `M-<char>` (e.g., `M-f`); `Ctrl-` keys become `C-M-<char>`; a second ESC transitions into an "escape-quit pending" state.
- A third ESC while escape-quit is pending triggers `keyboard-escape-quit`.
- Inside the minibuffer, a bare ESC with no follow-up still cancels (preserving current behaviour) — i.e., minibuffer's own ESC handling remains as the terminal case if no follow-up key arrives. Verify this works given the TUI's synchronous keystroke model.

Tests (`test_escape_meta.py`): ESC-f invokes forward-word; ESC-x opens M-x; ESC ESC ESC quits from normal mode / minibuffer / *Help* buffer; ESC inside minibuffer still cancels cleanly.

#### 6l-3. True incremental search (`isearch-forward` / `isearch-backward`)
The current C-s / C-r implementation (`default_commands.py:424-512`) advances point as the user types and moves to the next occurrence on repeat, but **does not highlight all occurrences** and **does not wrap around**. It behaves closer to Emacs's non-interactive `search-forward` than `isearch-forward`.

Plan:
1. **Rename** the current behaviour to `search-forward` / `search-backward` and keep it available via M-x (but unbind it from C-s / C-r). It serves as a simpler non-interactive alternative.
2. **Reimplement** `isearch-forward` / `isearch-backward` with:
   - **Match highlighting while active**: every occurrence of the current search string in visible buffer text is rendered with a highlight face (ANSI reverse video). The current match (the one point is on) gets a distinct "emphasised" highlight.
     - Mechanism: add `editor.highlight_term: str | None` and `editor.highlight_case_fold: bool` fields, checked in `EditorView._render_window()`. When rendering a line, find all matches and overlay them via `ScreenBuffer.set_region()` with a highlight ANSI sequence. The current match is rendered with a brighter sequence.
     - This is a lightweight alternative to a full face/overlay system — sufficient for isearch and reusable by `query-replace`.
   - **Wrap-around**: when `find_forward` fails at EOB, show `Failing I-search: <term>` in the prompt. On the next `C-s`, wrap to BOB and show `Wrapped I-search: <term>`. Symmetric for backward with BOB → EOB. The "Wrapped" message is a small UX nicety we should replicate.
   - **Keep existing UX**: C-g cancels and restores position; C-s / C-r repeats; Enter confirms; Backspace pops the position stack; printable chars extend the search; unknown keys exit-and-replay.
3. **Tests** (extend `test_isearch.py` or add `test_isearch_v2.py`): highlighting visible via harness screen accessors; wrap EOB → BOB with message progression "Failing" → "Wrapped"; multi-match highlighting on one line; rename behaviour (`search-forward` still reachable via M-x, not via C-s).

#### 6l-4. `query-replace` (M-%)
New command `query-replace` bound to `M-%`. Two sequential minibuffer prompts: "Query replace: " for the search string, then "Query replace <from> with: " for the replacement. After both prompts, enter query-replace mode:
- Highlight remaining matches using the isearch highlight mechanism (`editor.highlight_term`).
- Move point to the first match.
- Display `Query replacing <from> with <to>: (? for help) ` in the message area and capture single keystrokes via a new editor capture mode (similar to `_describing_key`).

**Supported keys** (deliberately a subset of Emacs):

| Key             | Action                                                      |
| --------------- | ----------------------------------------------------------- |
| `SPC` or `y`    | Replace current match, advance to next                      |
| `DEL` or `n`    | Skip current match, advance to next                         |
| `RET` or `q`    | Exit query-replace (do not replace current)                 |
| `.`             | Replace current match and exit                              |
| `!`             | Replace all remaining matches with no further prompting     |
| `u`             | Undo the previous replacement (stay in query-replace)       |
| `U`             | Undo all replacements made in this session, then exit       |
| `e`             | Edit the replacement string in the minibuffer, then resume  |
| `C-g`           | Cancel (restore point, do not apply current)                |
| `?`             | Show help with the above list                               |

The whole session is one undo group by default; `u` / `U` manipulate a per-session in-memory stack of applied replacements so they can be rolled back without leaving the session. On session exit, everything collapses into a single undoable group via `add_undo_boundary()`.

Tests (`test_query_replace.py`): every key path; undo one / undo all; edit replacement then resume; cancel via C-g; exit via RET; `!` replace-all; `?` help; interaction with highlighting; multi-line paragraph (depends on multi-line search — see 6l-5).

#### 6l-5. Deferred items pulled forward

Items carried from earlier phases, to be addressed **in this phase** where they support the core goals:

- **Multi-line search** — `find_forward` / `find_backward` are currently line-based (`buffer.py:996-1048`), preventing search patterns that contain `\n`. `query-replace` and `isearch` both benefit from fixing this. Implement buffer-wide scanning (e.g., search across a joined view with newline offsets).
- **Undo granularity bug** (6k deferred) — a second `C-/` after `Backspace` appears to redo rather than continue undoing. Root-cause and fix while we're in the editor.

Items **explicitly deferred again** (document but do not implement here):

- **Python configuration file / extension API** (from 6a "Future 6a extensions" and 6k deferred) — `~/.neon-edit.py` loader, sandboxed extension registration. Infrastructure (`defvar`, `defmode`, `@defcommand`) exists; loader and sandbox do not. Still out of scope for a polish pass.
- **Syntax highlighting** (from 6a "Future 6a extensions", 6k deferred) — the highlight mechanism added for isearch in 6l-3 could in principle carry syntax highlighting, but a proper regex-based system is a separate initiative.
- **Game-world integration hooks** (6k deferred) — NPC-triggered buffer events, editor↔game-state bridge.
- **Raw-mode TUI apps inside shell buffer** (6j deferred) — requires raw-mode passthrough architecture.
- **Interactive programs (chat) in shell buffer** (6j deferred) — `ShellBufferInput` stub (`shell_mode.py:82-100`) still raises `EOFError`. Needs a minibuffer↔`get_line` bridge. Revisit in a shell-mode follow-up phase.
- **Output region protection in shell buffer** (6j deferred) — per-region read-only.
- **ANSI rendering in shell buffer** (6j deferred) — attributed-text model.
- **TD-003: TUI framework timer/auto-refresh** — `on_tick()` so `sysmon` updates without keypresses. Unrelated to editor; belongs to a small TUI-framework phase.

#### 6l-6. Files likely to be modified

- `editor/default_commands.py` — new `keyboard-escape-quit`, `query-replace`, rename old isearch → `search-forward`/`search-backward`, reimplemented `isearch-forward`/`isearch-backward`, key bindings (`M-%`, ESC handling)
- `editor/editor.py` — ESC-as-Meta state machine, `highlight_term` field, query-replace capture mode, keyboard-quit audit fixes
- `editor/view.py` — render `highlight_term` matches per visible line via `set_region`
- `editor/buffer.py` — multi-line `find_forward` / `find_backward` (new or enhanced), match-iteration helper for highlighting, undo-granularity fix
- `editor/minibuffer.py` — verify and adjust C-g / ESC cancellation paths to play nicely with ESC-as-Meta
- `shell/tui/__init__.py` — potentially `set_region` highlight helpers (if needed)
- `initial_fs/Documents/TUTORIAL.txt` — update the search chapter to describe true isearch behavior; add a short query-replace section
- New test files: `tests/unit/editor/test_keyboard_quit.py`, `tests/unit/editor/test_escape_meta.py`, `tests/unit/editor/test_query_replace.py`; extensions to `tests/unit/editor/test_isearch.py`

#### 6l-7. Success criteria

- All 1433 existing tests still pass.
- C-g reliably cancels every interactive mode listed in 6l-1; `keyboard-escape-quit` works from normal mode, minibuffer, *Help* buffer, and query-replace.
- ESC acts as a Meta prefix: `ESC f` === `M-f`, `ESC x` === `M-x`, `ESC ESC ESC` === `keyboard-escape-quit`.
- `isearch-forward` visibly highlights all matches in the visible region (harness-verifiable) and wraps at EOB with the "Failing" → "Wrapped" progression.
- `query-replace` (M-%) supports SPC/y, DEL/n, RET/q, `.`, `!`, `u`, `U`, `e`, `C-g`, `?`; undo-one and undo-all function correctly.
- The tutorial document reflects the new search and query-replace behaviour.

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
