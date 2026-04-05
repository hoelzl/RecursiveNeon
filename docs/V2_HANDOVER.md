# V2 Handover Document

> **Date**: 2025-03-23 (updated 2026-04-05)
> **Status**: Phases 0-6k complete, Phase 6l-1 complete. 1452 tests. **Phase 6l-2 (`keyboard-escape-quit` + ESC-as-Meta) is next**, followed by the rest of Phase 6l (true incremental search, query-replace, deferred items), Phase 7 (deferred-items cleanup: shell buffer, pipeline, tech debt, extensibility, game hooks, TUI apps) and Phase 8 (browser terminal + desktop GUI). Detailed descriptions of phases 6b-6k have been moved to [V2_HANDOVER-archive.md](./V2_HANDOVER-archive.md).
> **Branch**: `master` (orphan branch, initial commit: `384e373`)

> **Editor design principle: Emacs is the ground truth.** For every
> neon-edit feature, the goal is to match the behaviour of real GNU Emacs
> exactly. If the prose in any design doc (this one, phase plans, comments)
> contradicts real Emacs, the prose is almost certainly wrong — treat it as
> a bug and match Emacs instead. The only sanctioned deviation is when
> faithful Emacs behaviour would be disproportionately complex to implement
> in our synchronous TUI model; in that case, document the deviation next
> to the code that diverges. When uncertain whether a difference is a prose
> bug or a complexity deviation, **ask for clarification** rather than
> guessing. (Introduced after Phase 6l-1 — see that section for the
> specific deviations that were resolved in favour of Emacs.)

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

### Phase 6l: Emacs polish — **IN PROGRESS**
**Goal**: Make the editor genuinely *feel* like Emacs. Implement the cancellation, search, and replace workflows that are cornerstones of the Emacs experience, plus resolve a backlog of small deferred items carried forward from earlier phases. This is the final pre-browser polish pass on the editor.

> **Editor design principle: Emacs is the ground truth.** For every editor
> feature, the goal is to match the behaviour of real GNU Emacs exactly.
> The prose in this handover is *trying* to describe Emacs; if the prose
> and real Emacs disagree, the prose is wrong. Treat such disagreements
> as bugs in the handover and match Emacs instead.
>
> The only sanctioned deviation is when faithful Emacs behaviour would be
> disproportionately complex to implement in our synchronous TUI model.
> In that case, document the deviation next to the code that diverges and
> explain why. When in doubt whether a difference is a prose bug or a
> complexity deviation, **ask for clarification** rather than guessing.

#### 6l-1. `keyboard-quit` audit and hardening (C-g) — **DONE** (1452 tests)
Added `Editor._reset_transient_state()` as the shared foundation for C-g and (the upcoming) `keyboard-escape-quit`; promoted previously-dynamic describe-key state (`_describing_key_prefix`, `_describing_key_map`, `_dkb_prefix`, `_dkb_map`) to explicit `__init__` fields; added a top-level C-g intercept in `Editor.process_key` so C-g short-circuits any pending prefix keymap (mirroring Emacs's `quit` signal) rather than falling through as "C-x C-g is undefined". New `tests/unit/editor/test_keyboard_quit.py` with 19 tests covering every cancellation path.

Deviations from the *original* 6l-1 prose, resolved to match Emacs:

- **Describe-key C-g is not cancelled**: `C-h k C-g` describes the `keyboard-quit` binding instead of cancelling the capture (Emacs behaviour).
- **Minibuffer cancel preserves the mark**: `C-SPC C-x b C-g` leaves the mark active (Emacs behaviour). The "clears the transient region/mark in all cases" wording in the original prose was a bug.

Still handled as specified:
- C-g cancels a pending prefix keymap (mid-`C-x`) and clears `_prefix_arg`, `_building_prefix`, `_prefix_has_digits`, `_prefix_keys`.
- C-g cancels an in-progress `C-u` prefix argument.
- C-g cancels the minibuffer and `execute-extended-command` mid-typing.
- C-g cancels incremental search and restores pre-entry point (existing behaviour, verified by test).
- C-g clears an active region at top level.
- C-g consistently shows `"Quit"` in the message area.

Query-replace cancellation is deferred to 6l-4 (the command doesn't exist yet).

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

Items **explicitly deferred again** (document but do not implement here). This list is the consolidated backlog of known deferrals from every prior phase. It is intentionally exhaustive so nothing gets forgotten between handovers.

**Editor / shell-mode (from Phase 6 sub-phases)**:

- **Python configuration file / extension API** (from 6a "Future 6a extensions" and 6k deferred) — `~/.neon-edit.py` loader, sandboxed extension registration. Infrastructure (`defvar`, `defmode`, `@defcommand`) exists; loader and sandbox do not. Still out of scope for a polish pass.
- **Syntax highlighting** (from 6a "Future 6a extensions", 6k deferred) — the highlight mechanism added for isearch in 6l-3 could in principle carry syntax highlighting, but a proper regex-based system is a separate initiative.
- **Game-world integration hooks** (6k deferred) — NPC-triggered buffer events, in-game script callbacks, editor↔game-state bridge. A tutorial chapter covering this would require those hooks to be designed and implemented first.
- **Raw-mode passthrough for TUI apps inside the shell buffer** (6j deferred) — running `codebreaker`/`sysmon`/`edit` from the `*shell*` buffer currently can't work because shell-mode drives output into a `Buffer` and expects cooked-mode line input. A proper fix needs the shell buffer to temporarily hand control of the underlying TUI frame to a raw-mode app and restore it on exit. Requires raw-mode passthrough architecture.
- **Interactive programs (chat) in shell buffer** (6j deferred) — `ShellBufferInput` stub (`shell_mode.py:82-100`) still raises `EOFError`. Needs a minibuffer↔`get_line` bridge. Revisit in a shell-mode follow-up phase.
- **Output region protection in shell buffer** (6j deferred) — per-region read-only so the user can't clobber historical output. Currently the whole buffer is writable and the shell reads input only from `input_start` to EOB.
- **ANSI rendering in shell buffer** (6j deferred) — shell output is currently ANSI-stripped before insertion. Rendering attributes requires an attributed-text model in `Buffer`.
- **`on_after_key` general async bridge** (6j deferred) — the pattern introduced for shell-mode execution could support other async features (background NPC responses, long-running commands, timed events). No current consumers beyond shell-mode.

**Future TUI apps (Future 6c candidates, not scheduled)**:

- **File browser TUI** — navigate the virtual filesystem, preview files, open in editor.
- **Port scanner minigame** — network-puzzle minigame.
- **Memory dump minigame** — hex-viewer puzzle minigame.

**Shell / WebSocket leftovers from Phases 3 & 5**:

- **WS client `--command` batch mode** (Phase 3) — architecture supports it; persistent/named sessions need to land first for it to be useful.
- **`**` recursive globs** (Phase 5) — single-level patterns (`*`, `?`, `[...]`) cover 95% of use cases; the recursive form is a nice-to-have.
- **Stderr redirection (`2>`, `2>&1`)** (Phase 5) — only stdout redirection is implemented. Out of scope for the polish pass.
- **Builtins participating in pipes** (Phase 5) — currently builtins don't read from `ProgramContext.stdin` or feed `CapturedOutput`. Low practical impact but inconsistent.

**Tech debt (from TECH_DEBT.md)**:

- **TD-003: TUI framework timer / auto-refresh** — `on_tick()` so `sysmon` updates without keypresses. Belongs to a small TUI-framework phase rather than editor polish.
- **TD-004: Mark tracking identity vs `Mark.__eq__` value-equality footgun** — `Buffer.track_mark()` uses identity, but `Mark.__eq__` compares by position. Latent risk if any future code uses `in` / `==` against `_tracked_marks`. Current decision is "document the invariant"; revisit only if the footgun actually bites.
- **TD-001: `pydantic.v1` warning on Python 3.14+** — intentional workaround until `langchain-core` drops the `pydantic.v1` import or `pydantic ≥ 2.13` ships stable. Not an action item; just tracked.

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

### Phase 7: Deferred items cleanup — **AFTER 6l**

**Goal**: Close out every item that was "explicitly deferred again" in Phase 6l-5. This is the last pre-browser phase. Phase 7 is large and naturally splits into six sub-phases (7a–7f), each a standalone commit. The order below reflects dependency ordering: 7a introduces the general async bridge used by 7e's NPC events, 7c ships `on_tick` before 7f's TUI apps want to use it, and 7d's Python API underlies nothing that 7e needs (game-world hooks are native API, not user-script callbacks).

After Phase 7, every deferral carried forward from Phases 3–6 is either landed or consciously withdrawn. Nothing goes into Phase 8 (browser) unless it can work in the CLI first.

#### 7a. Shell buffer completions (consolidates 6j deferrals)

**Goal**: Make the `*shell*` buffer (M-x shell) a first-class interactive environment — not just a place to run `ls`. Consolidates the five 6j deferrals plus the generalised async bridge.

##### 7a-1. Output region protection
Make historical shell output read-only so the user can't clobber it while editing the current input. New primitives on `Buffer`:

- `Buffer.add_read_only_region(start: Mark, end: Mark) -> None`
- `Buffer.clear_read_only_regions() -> None`
- `Buffer.is_read_only_at(pos: Mark) -> bool`
- Insert/delete primitives check the list of regions and refuse modifications whose span intersects any read-only range.
- Regions use tracked marks so they follow edits correctly (reusing Phase 6i tracked-mark infrastructure).

Shell-mode on command submit: mark the range `[command_start, output_end]` read-only, then move `input_start` past it.

Tests (`test_read_only_regions.py`): insert inside region fails with message; delete crossing region boundary fails; delete at exact boundary is allowed; user can still edit the current prompt; existing `Buffer.read_only` flag (whole-buffer) still works independently.

##### 7a-2. Attributed-text model + ANSI rendering
The biggest single change. Shell output currently goes through `strip_ansi()` (`shell_mode.py:43`) before insertion — all colour is lost. Fix:

- New `Buffer.attrs: list[list[Attr | None]]` parallel to `lines`, where `Attr` carries `fg`, `bg`, `bold`, `reverse`, etc. `None` means default.
- Insert/delete primitives maintain `attrs` in lockstep with `lines` — every mutation has a matching attribute mutation.
- `AnsiParser` converts an ANSI-bearing string into `list[(text, Attr)]` runs; `BufferOutput.write()` uses it instead of `strip_ansi`.
- `EditorView._render_window()` reads `buffer.attrs[line_idx][col]` when emitting characters and emits the corresponding ANSI sequence via `ScreenBuffer.set_region` or a new per-character variant.
- Undo/redo snapshot attributes alongside text (extend `UndoInsert`/`UndoDelete` records).
- Backwards compatibility: buffers with `attrs=None` behave exactly as today; only `shell-mode` (and, later, syntax-highlighted modes from 7d-2) opts in.

Tests (`test_buffer_attrs.py`, `test_ansi_parser.py`, extensions to `test_shell_mode.py`): ANSI colour codes produce correct attribute runs; mixed attributes on a single line; line splits/joins preserve attributes; undo/redo round-trips restore attributes; `strip_ansi` path is only used as a fallback.

**Design risk**: This is the most invasive 7a change. A pre-work sketch in `docs/EDITOR_ATTRS.md` before writing code is strongly recommended.

##### 7a-3. General `on_after_key` async bridge
Generalise the shell-mode-specific `_pending_async` mechanism into an editor-wide primitive:

- `Editor.after_key(callback: Callable[[], Awaitable[None]]) -> None` — queue an async callback to run after the current keystroke finishes processing.
- Multiple callbacks queued from a single key execute in FIFO order before the next render.
- The TUI runner's `on_after_key()` drains the queue.
- Errors in callbacks are logged to `*Messages*` but do not crash the editor.

Used in 7a-4 (chat `get_line`), 7a-5 (TUI passthrough), and 7e (NPC events).

Tests (`test_async_bridge.py`): single callback runs; multiple callbacks run in order; error in callback is caught and logged; callback scheduling from within a callback defers to the next key.

##### 7a-4. Interactive programs in shell buffer
Replace the `EOFError`-raising `ShellBufferInput` stub (`shell_mode.py:86-100`) with a real implementation:

- When a shell program calls `ctx.get_line(prompt)`, shell-mode pops the editor minibuffer with that prompt.
- The `await`-ing program is suspended via the async bridge (7a-3); when the minibuffer returns, its result is fed back to the program.
- `chat` then works from the shell buffer: `/help`/`/relationship`/`/status` slash commands are just regular lines fed through the minibuffer bridge.
- Cancellation (C-g inside the minibuffer) raises `KeyboardInterrupt` into the program, which `chat` catches to cleanly exit the conversation.

Tests (`test_shell_buffer_interactive.py`): `chat` runs from shell buffer, messages appear in buffer; slash commands work; C-g in the prompt cancels cleanly.

##### 7a-5. Raw-mode TUI app passthrough
Let `codebreaker`, `sysmon`, and `edit` run from the shell buffer. The architectural trick: when the shell buffer detects a TUI-app command, it temporarily hands the underlying `run_tui_app` frame over to the child app, then resumes when the child exits.

- New `TuiApp.pause()` / `TuiApp.resume()` hooks on the runner: save the current screen, let the child app take over the raw-mode loop, restore on exit.
- A registry of "TUI commands" on `ShellState` — when a recognised command (`codebreaker`/`sysmon`/`edit`) is submitted, shell-mode invokes the passthrough rather than running the command through `BufferOutput`.
- On return, the child app's screen is discarded; the editor redraws fully (no attempt to preserve child output as buffer text).
- Edge case: nested `edit` from shell-in-editor is valid but should be guarded against infinite recursion — the nested editor has no `M-x shell` binding unless the user explicitly enables it.

Tests (harness-only, since raw input is mocked): run `codebreaker` from shell buffer, feed a mock key sequence, exit; run `sysmon`, tick a few times (using 7c-1 `on_tick`), exit; verify editor screen restored.

##### 7a-6. Acceptance criteria
- Read-only regions work and protect shell history from accidental modification.
- `*shell*` buffer shows ANSI colours (e.g., `ls` output, `grep --color`).
- `on_after_key` async bridge is general and usable from any mode.
- `chat` and other `get_line`-using programs run cleanly from the shell buffer.
- `codebreaker`, `sysmon`, `edit` run from the shell buffer and return control cleanly.
- ~100 new tests.

---

#### 7b. Shell pipeline completeness

**Goal**: Close the gaps Phase 5 left in the cooked shell pipeline. Four small deferrals, one sub-phase.

##### 7b-1. Recursive globs (`**`)
Extend `expand_globs()` in `shell/glob.py` so `**` matches zero-or-more directories:

- `**/*.txt` — every `.txt` anywhere under `cwd`.
- `Documents/**/notes.md` — every `notes.md` under any depth of `Documents/`.
- `**` alone — every file and directory under `cwd`.
- Recursive traversal stays bounded to the virtual filesystem via `AppService`; no escape to real paths.
- Quoted `**` still passes through literally.

Tests (`test_glob.py` extensions): basic `**/*.txt`; `**` at root vs subdirectory; `**` between literal segments; `**` combined with `?` and `[...]`; unmatched `**` passes through; quoted `**` not expanded.

##### 7b-2. Stderr redirection
Extend the parser (`shell/parser.py:parse_pipeline`) to recognise three new redirect forms:

- `cmd 2> file` — stderr to file, stdout unaffected.
- `cmd 2>> file` — append stderr.
- `cmd > out 2> err` — split streams.
- `cmd > all 2>&1` — merge stderr into stdout, then redirect both.
- `cmd 2>&1 | grep` — merge into the pipe.

Requires:
- `Redirect` dataclass gains a `fd` field (`1` for stdout, `2` for stderr).
- `CapturedOutput` separates stdout and stderr buffers.
- `ProgramContext.output` already exposes both (`output.error()` is the stderr path); the change is in parser + capture, not programs.

Tests (`test_redirection.py` extensions): every form above; append variants; interaction with pipes.

##### 7b-3. Builtins participating in pipes
Audit the three builtins (`cd`, `exit`, `export`). Most don't produce output, but the current implementation *ignores* `ProgramContext.stdin` and `output`, which means `echo foo | cd` can crash or silently misbehave. Fix:

- Builtins drain (or discard) `ProgramContext.stdin` if present instead of ignoring it.
- Builtins write status/error through `ProgramContext.output`, not directly to `stdout`.
- `export VAR=$(cmd)` — out of scope; command substitution is a separate feature, not a Phase 5/7 deferral.

Tests (`test_builtins.py` extensions): `echo foo | cd bar` does not crash; `cd bar 2> err` captures cd's error; `export FOO=bar | wc -l` produces nothing on stdout.

##### 7b-4. WS client `--command` batch mode
The Phase 3 deferral. Implement:

- `python -m recursive_neon.wsclient --command "ls Documents"` — connects, opens a temporary session, runs the command, prints output, disconnects.
- `--session <name>` — attach to a named persistent session instead of temporary. Persistent sessions do not exist yet. **Decision**: ship `--command` with a temporary session only; persistent sessions remain deferred to a later phase driven by an actual need.
- Exit code reflects the shell command's success/failure.
- ANSI output is stripped when stdout is not a TTY (so `wsclient --command "ls" | grep foo` works in pipelines).

Tests (`test_wsclient_batch.py`): round-trip against a mock server; exit code propagation; TTY vs pipe detection.

##### 7b-5. Acceptance criteria
- `**` recursive globs work end-to-end.
- Stderr redirection forms all work.
- Builtins don't crash in pipelines.
- `python -m recursive_neon.wsclient --command "..."` works.
- ~50 new tests.

---

#### 7c. Tech debt cleanup

**Goal**: Resolve the four tracked tech debt items. Small, fast sub-phase that unblocks 7f.

##### 7c-1. TD-003 — TUI framework `on_tick`
Add optional tick callbacks to the TUI framework:

- `TuiApp.on_tick(self, dt_ms: int) -> ScreenBuffer | None` — default implementation returns `None` (no update).
- `TuiApp.tick_interval_ms: int = 0` — `0` disables ticks.
- `run_tui_app()` uses the keystroke read timeout to fire ticks at the requested interval.
- `sysmon` sets `tick_interval_ms = 1000` and refreshes metrics in `on_tick`.
- Local raw input (`LocalRawInput`) and WebSocket raw input both support the keystroke-read timeout.

Tests (`test_tui_runner.py` extensions, `test_sysmon.py` extensions): tick fires at expected intervals; keyboard input during ticks remains responsive; sysmon updates over time.

##### 7c-2. TD-004 — Mark tracking identity enforcement
Current decision (Option 3, "document and keep identity checks") is the right one, but harden it:

- Add a tiny `_MarkSet` wrapper in `buffer.py` that uses `id()` internally — purely to make the intent obvious at call sites and prevent `in`/`==` accidents.
- `track_mark` / `untrack_mark` use `_MarkSet` rather than a raw list.
- Add a debug assertion in `track_mark` that fails if the same `Mark` object is tracked twice. This would have caught the Phase 6i bug earlier.
- Close out TD-004 in `TECH_DEBT.md` as "resolved via `_MarkSet` wrapper".

Tests (`test_mark_set.py`): identity-based `contains`; duplicate tracking asserts; removal via identity.

##### 7c-3. TD-001 — `pydantic.v1` warning re-audit
Just run the check with current pinned dependencies:

```bash
../.venv/Scripts/python -W error::UserWarning -m recursive_neon.shell
```

If no `pydantic.v1` warning appears, delete `warnings.filterwarnings` from `recursive_neon/__init__.py` and close out TD-001. If the warning still fires, leave the filter and re-check in a future phase.

No new tests unless the filter is removed — in that case, add a test that imports `recursive_neon` with `-W error` and does not raise.

##### 7c-4. TD-005 — TUI terminal size detection and resize handling

**Problem**: Every TUI app (neon-edit, `sysmon`, `codebreaker`) launches into a fixed 80×24 region in the top-left of the terminal, because `run_tui_app()` defaults `width=80, height=24` (see `shell/tui/runner.py:28-29`) and no caller passes the real dimensions. Resizing the terminal while an app is running never dispatches `TuiApp.on_resize` — the protocol method exists and every app already implements it (`editor/view.py:102`, `shell/programs/sysmon.py:99`, `shell/programs/codebreaker.py:125`), but the runner never calls it.

**Fix plan**:

1. **Measure on entry.**
   - Add a small helper `shell/tui/runner.py::_measure_terminal() -> tuple[int, int]` that calls `shutil.get_terminal_size(fallback=(80, 24))`. If `sys.stdout.isatty()` is `False`, keep the fallback — piped/captured output should stay deterministic for tests.
   - `shell.py::_make_run_tui` measures right before `run_tui_app(...)` and passes the result as `width=` / `height=`. Same for the WebSocket path in `terminal.py::_run_tui_factory`.
   - The `run_tui_app` default stays 80×24 so existing tests continue to work without change.

2. **Resize event channel — local (POSIX)**.
   - In `LocalRawInput` (`shell/shell.py:653`), install a `signal.SIGWINCH` handler at `run_tui_app` entry and uninstall it on exit (use a try/finally around the handler swap — never leave it installed outside TUI mode).
   - The handler writes a pending flag (`self._resize_pending = True`); it must not call async code directly.
   - The runner loop checks the flag between keystrokes — before `get_key()` returns the next key, if `_resize_pending` is set, clear it, call `_measure_terminal()`, and dispatch `app.on_resize(w, h)`, deliver the screen, then continue to the key read.
   - Races: if SIGWINCH fires *during* a keystroke read, the flag is set and handled on the next iteration — acceptable latency.

3. **Resize event channel — local (Windows)**.
   - `signal.SIGWINCH` does not exist on Windows. Two options:
     a. **Poll on tick** — once 7c-1 (`on_tick`) lands, re-measure on each tick and dispatch `on_resize` if dimensions changed. Natural fit; costs one `get_terminal_size()` call per tick.
     b. **Poll on keystroke** — re-measure on every `get_key()` return. Cheaper but no update while the user is idle.
   - **Decision**: ship 7c-4 with option (b) for Windows (works without 7c-1), then upgrade to option (a) once 7c-1 is in place. Implement the check in `run_tui_app`, not in the raw input class, so the same code works for both `LocalRawInput` on Windows and anywhere else.

4. **Resize event channel — WebSocket**.
   - Extend the WS terminal protocol with a `{"type": "resize", "width": N, "height": M}` client → server message. See `terminal.py::handle_ws_message` (referenced in `main.py`) for the message-handling style.
   - `TerminalSessionManager` stores the latest `(width, height)` and pushes a resize event into a new `resize_queue: asyncio.Queue[tuple[int, int]]` on the session.
   - `WebSocketRawInput` exposes `drain_resize()` that returns the latest pending size (or `None`). The runner checks this between keystrokes, same as the local flag.
   - The `wsclient` sends a `resize` message immediately after connecting (using `shutil.get_terminal_size()`) and again whenever it detects a local SIGWINCH.
   - The browser terminal client (Phase 8) will follow the same contract: send `resize` on connect and on every `window.resize` event.

5. **Runner integration.**
   - `run_tui_app` becomes a single loop: each iteration first drains any resize event (local flag or WS queue), calling `on_resize` + delivering the screen, then reads the next keystroke. No duplication between paths.
   - Errors in `on_resize` are logged but do not crash the app; the previous screen stays on-screen.

6. **Tests** (`test_tui_runner.py` extensions):
   - `run_tui_app` passes the measured size to `app.on_start`.
   - A mock raw input that also delivers a resize event triggers `on_resize` with the new dimensions and the app gets a fresh screen.
   - Resize before the first keystroke works (edge case: resize arrives immediately after `on_start`).
   - POSIX SIGWINCH path uses a fake signal module to avoid flakiness.
   - Windows polling path tests with a mocked `shutil.get_terminal_size`.
   - WS resize message round-trip through `TerminalSessionManager`.

**Files modified**:
- `backend/src/recursive_neon/shell/tui/runner.py` — measurement, resize drain loop
- `backend/src/recursive_neon/shell/shell.py` — measure and pass size in `_make_run_tui`
- `backend/src/recursive_neon/terminal.py` — WS resize message handling, pass measured size
- `backend/src/recursive_neon/shell/keys.py` or `shell.py` — SIGWINCH handler on POSIX
- `backend/src/recursive_neon/wsclient/client.py` — send resize on connect and on SIGWINCH
- `backend/src/recursive_neon/main.py` — route `resize` message type
- `backend/tests/unit/shell/test_tui.py` or new `test_tui_runner.py` — test coverage
- `docs/TECH_DEBT.md` — close out TD-005

**Acceptance criteria for 7c-4**:
- Launching `edit` / `sysmon` / `codebreaker` in a 120×40 terminal fills the whole terminal from the first frame.
- Resizing the terminal while an app is running reflows the display within one keystroke (POSIX) or one tick/keypress (Windows).
- WebSocket client sends `resize` on connect and on host-terminal SIGWINCH; the server dispatches to the running TUI.
- Tests cover both POSIX and Windows paths with mocked signal/polling.

##### 7c-5. Acceptance criteria
- `sysmon` auto-refreshes every second without keypresses.
- TUI apps fill the whole terminal and reflow on resize (both CLI and WebSocket paths).
- TD-004 closed out with `_MarkSet` wrapper.
- TD-001 either closed out or re-confirmed with a dated note.
- TD-005 closed out.
- ~30 new tests (15 for tick/mark-set/pydantic + 15 for resize).

---

#### 7d. Editor extensibility (Python config + syntax highlighting)

**Goal**: Make the editor extensible by users, not just by editing `default_commands.py`. Two major features: a user config file and regex-based syntax highlighting.

##### 7d-1. `~/.neon-edit.py` config loader
On editor startup, execute the user's config file in a curated namespace:

- Path: `~/.neon-edit.py` by default, overridable via `RECURSIVE_NEON_CONFIG_PATH` env var.
- Exposed API: `defcommand`, `defvar`, `defmode`, `bind(key, command, keymap=global)`, `unbind(key, keymap=global)`, `editor` (the running instance — risky but necessary), `Buffer`, `Mark`, `Keymap` classes.
- **Sandboxing**: Execute with a restricted `__builtins__` that excludes `open`, `exec`, `eval`, `compile`, `__import__`, `globals`, `locals`. Pure-Python operations are allowed. This is *accidental-mistake protection*, not adversarial protection — document this clearly. A determined attacker running their own Python process has already won; the goal is to make copy-pasted snippets from untrusted sources less dangerous.
- Errors in user config are caught, written to `*Messages*` buffer, and do not crash the editor. The editor still starts cleanly with an empty or missing config.
- `M-x reload-config` re-runs the loader.

Tests (`test_config_loader.py`): load a minimal config that adds a command; syntax error in config surfaces in `*Messages*` and does not crash the editor; `open()` in user config raises `NameError`; reload picks up changes; env var override works; missing config file is a no-op.

Design note: The legacy branch's `docs/terminal-requirements.md` had a "user scripting" discussion — worth skimming for prior design lessons before starting.

##### 7d-2. Regex-based syntax highlighting
Build on the highlight mechanism introduced for isearch in Phase 6l-3 and the attributed-text model from 7a-2:

- `SyntaxRule` dataclass: `pattern: re.Pattern`, `face: str` (e.g., `keyword`, `string`, `comment`, `number`).
- `Mode.syntax_rules: list[SyntaxRule]` — new field on the existing `Mode` class from Phase 6g.
- Three starter language modes, each in its own file:
  - `editor/modes/python_mode.py` — keywords, strings (triple and single), comments, numbers, decorators.
  - `editor/modes/markdown_mode.py` — headers, bold, italic, code spans, links.
  - `editor/modes/sh_mode.py` — syntax highlighting for `.sh`/`.bash` file *content* (distinct from M-x shell's `shell-mode` major mode).
- Auto-detect mode from file extension in `find-file`; fall back to `text-mode`.
- Rendering: `EditorView._render_window()` scans each visible line for matches from the current mode's `syntax_rules` and calls `ScreenBuffer.set_region()` with face ANSI.
- Performance: cache the per-line match list keyed by line content hash; invalidate on line mutation.
- Face → ANSI mapping: new `FACES: dict[str, str]` in `editor/faces.py`; user can override via `defvar("face-keyword", "\033[36m")`.

Tests (`test_syntax_python.py`, `test_syntax_markdown.py`, `test_syntax_sh.py`, `test_faces.py`): each language highlights its keywords/strings/comments; face override works; mode auto-detection picks the right mode; performance cache hits; edits correctly invalidate the line cache.

##### 7d-3. Acceptance criteria
- `~/.neon-edit.py` can add commands, rebind keys, define variables.
- Config errors don't crash editor; they surface in `*Messages*`.
- Python files open with syntax highlighting visible in the terminal.
- Markdown and shell-script files also highlight correctly.
- ~80 new tests.

---

#### 7e. Game-world integration hooks

**Goal**: Stop treating the editor as an isolated text tool — wire it into the game state and NPCs. This is what makes the editor feel like *part of Recursive://Neon* rather than a generic Emacs clone.

##### 7e-1. Editor ↔ GameState bridge
- `Editor.game_state: GameState | None` — injected at construction by the `edit` shell program.
- `M-x open-note <name>` — opens a Note as a buffer. Save writes back to the game Note.
- `M-x open-task-list <list>` — opens a task list as a structured buffer (`- [ ] foo` / `- [x] bar`), where save parses the lines back into task state.
- `M-x list-npcs` — shows all known NPCs in a read-only buffer, with `RET` on a line opening a `*chat-<npc>*` buffer.
- Save hooks: `Buffer.on_save: Callable | None` fires after a successful save; bridge commands install a hook that propagates changes back to game state.

Tests (`test_editor_game_bridge.py`): open-note round-trip; task toggle via editor save; edge case where game state mutates externally while buffer is open.

##### 7e-2. NPC-triggered buffer events
NPCs can push messages into the editor:

- New buffer kind: `*npc-<id>*` — per-NPC conversation log, auto-created on first message.
- `editor.on_npc_event(npc_id: str, text: str)` appends to the buffer, using the async bridge from 7a-3 so appends can happen while the user is typing elsewhere.
- `NPCManager` gains `on_message_callback` that the editor sets at startup (when an editor is active).
- Flash the modeline / ring the bell (via `ScreenBuffer`) on new message; configurable via `defvar("editor.npc-notify", "flash" | "silent")`.

Tests (`test_editor_npc_events.py`): NPC event creates buffer; subsequent events append; notify flash triggers; silent mode works; concurrent events don't corrupt buffer state.

##### 7e-3. In-game script callbacks
Save hooks (introduced in 7e-1) drive game events:

- `GameEventBus` — simple pub/sub in `services/`.
- Editor saves publish `editor.buffer_saved` events with `(buffer_name, filepath, contents)`.
- Future game scripts subscribe to this to trigger quests, unlock NPCs, etc. No scripts shipped in 7e — just the plumbing.
- Document the event schema in `docs/GAME_EVENTS.md`.

Tests (`test_game_event_bus.py`, `test_editor_save_events.py`): save fires event; multiple subscribers all receive; unsubscribed handlers don't fire.

##### 7e-4. Acceptance criteria
- Opening a note in the editor and saving round-trips correctly.
- Opening a task list and toggling items via editor save updates the game state.
- NPC messages arriving while the player is in the editor surface in a dedicated buffer without interrupting typing.
- Save hooks publish events that future game scripts can subscribe to.
- ~50 new tests.

---

#### 7f. New TUI apps

**Goal**: Three new `TuiApp` implementations that round out the game's interactive surface. Each is a standalone commit.

##### 7f-1. File browser TUI (`fsbrowse`)
Full-screen file browser for the virtual filesystem:

- Two-pane layout: directory tree (left 40%) + preview (right 60%).
- Navigation: arrows, Enter to enter a directory or open a file in preview, Backspace to go up, `q` to quit, `e` to open the current file in `neon-edit`.
- Preview: text files rendered inline (first 200 lines, truncated with an indicator).
- Integration: backspace from root returns to shell; opening the editor suspends via the 7a-5 passthrough (and therefore also works from M-x shell).
- Registered as the `fsbrowse` shell command.

Tests (`test_fsbrowse.py`): navigate directory; preview file; open in editor; quit cleanly.

##### 7f-2. Port scanner minigame (`portscan`)
Port from legacy branch `docs/minigames/portscanner-design.md` and `portscanner-requirements.md`:

- Grid of N ports; scan reveals whether each is open/closed/decoy.
- Player deduces which sequence triggers the target system.
- Win condition: correct sequence entered.
- Lose condition: too many wrong guesses (lockout).
- Uses `on_tick` (from 7c-1) for a lockout countdown animation.

Tests (`test_portscan.py`): win path; lose path; scan reveals correct state; tick-based animation frames render.

##### 7f-3. Memory dump minigame (`memdump`)
Port from legacy branch `docs/minigames/memorydump-design.md` and `memorydump-requirements.md`:

- Hex viewer of a generated memory region.
- Player searches for patterns (a hidden string, a signature).
- Find-as-you-type highlights matches.
- Win: find all required patterns within a time/move budget.

Tests (`test_memdump.py`): hex rendering; pattern search; win/lose conditions.

##### 7f-4. Acceptance criteria
- Three new `TuiApp` implementations, each registered as a shell command.
- Each works in both local CLI and WebSocket client.
- ~90 new tests (~30 per app).

---

#### 7g. Files likely to be modified

Listed per sub-phase so each commit stays focused.

**7a** — shell buffer:
- `editor/buffer.py` — read-only regions, attrs array, attribute-aware primitives, undo record extensions
- `editor/ansi_parser.py` *(new)* — ANSI → attr runs
- `editor/shell_mode.py` — use attrs, install read-only region on submit, real `ShellBufferInput`, TUI passthrough
- `editor/editor.py` — `after_key()` general async bridge
- `editor/view.py` — render per-character attributes
- `shell/tui/runner.py` — pause/resume for TUI passthrough
- New tests: `test_read_only_regions.py`, `test_buffer_attrs.py`, `test_ansi_parser.py`, `test_async_bridge.py`, `test_shell_buffer_interactive.py`, extensions to `test_shell_mode.py`

**7b** — shell pipeline:
- `shell/glob.py` — `**` handling
- `shell/parser.py` — stderr redirect syntax, `Redirect.fd`
- `shell/output.py` — split stderr capture
- `shell/builtins.py` — stdin/output discipline
- `wsclient/client.py` — `--command` batch mode
- Extensions to `test_glob.py`, `test_parser.py`, `test_redirection.py`, `test_builtins.py`; new `test_wsclient_batch.py`

**7c** — tech debt:
- `shell/tui/__init__.py`, `shell/tui/runner.py` — `on_tick`, terminal-size measurement, resize drain loop
- `shell/shell.py` — measure size in `_make_run_tui`, SIGWINCH handler on POSIX (in `LocalRawInput`)
- `shell/programs/sysmon.py` — use `on_tick`
- `terminal.py` — WS `resize` message handling, pass measured size into `run_tui_app`
- `wsclient/client.py` — send `resize` on connect and on host SIGWINCH
- `main.py` — route `resize` WS message type
- `editor/buffer.py` — `_MarkSet` wrapper
- `recursive_neon/__init__.py` — maybe remove the pydantic.v1 filter
- `docs/TECH_DEBT.md` — close out TD-003, TD-004, TD-005; re-audit TD-001
- Extensions to `test_tui_runner.py`, `test_sysmon.py`, `test_terminal.py`; new `test_mark_set.py`, `test_tui_resize.py`

**7d** — editor extensibility:
- `editor/config_loader.py` *(new)* — `~/.neon-edit.py` loader + sandbox
- `editor/faces.py` *(new)* — face → ANSI mapping
- `editor/modes/python_mode.py`, `editor/modes/markdown_mode.py`, `editor/modes/sh_mode.py` *(new)*
- `editor/modes.py` — `Mode.syntax_rules` field
- `editor/view.py` — render syntax rules per visible line, cache
- `shell/programs/edit.py` — trigger loader on editor startup
- New tests: `test_config_loader.py`, `test_syntax_python.py`, `test_syntax_markdown.py`, `test_syntax_sh.py`, `test_faces.py`

**7e** — game-world hooks:
- `editor/editor.py` — `game_state`, `on_npc_event`, save-hook plumbing
- `editor/game_bridge.py` *(new)* — `open-note` / `open-task-list` / `list-npcs` commands
- `services/game_event_bus.py` *(new)* — pub/sub
- `services/npc_manager.py` — `on_message_callback`
- `shell/programs/edit.py` — wire game state into editor
- `docs/GAME_EVENTS.md` *(new)* — event schema
- New tests: `test_editor_game_bridge.py`, `test_editor_npc_events.py`, `test_game_event_bus.py`, `test_editor_save_events.py`

**7f** — new TUI apps:
- `shell/programs/fsbrowse.py` *(new)*
- `shell/programs/portscan.py` *(new)*
- `shell/programs/memdump.py` *(new)*
- Register in `shell/programs/__init__.py`
- New tests: `test_fsbrowse.py`, `test_portscan.py`, `test_memdump.py`

#### 7h. Success criteria (whole phase)

- All existing tests from previous phases still pass.
- Every "explicitly deferred again" item in 6l-5 has either landed or is consciously withdrawn (with a written justification).
- `*shell*` buffer renders colours, protects history, runs interactive programs and TUI apps.
- Shell pipeline handles `**`, stderr, builtins-in-pipes, and `--command` batch.
- `sysmon` live-updates.
- Editor loads user Python config safely; Python/Markdown/shell files have syntax highlighting.
- Editor is wired into game state: notes, task lists, NPC messages, save-hook events.
- Three new TUI apps: `fsbrowse`, `portscan`, `memdump`.
- Target: ~1800 total tests (≈400 new across 7a–7f).

After Phase 7, the project moves to Phase 8 (browser) with a genuinely polished CLI foundation — every feature that exists has been exercised end-to-end and nothing is carrying forward as deferred.

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
