# AGENTS.md — Guidance for AI Agents

This file helps AI agents (Claude Code, Copilot, etc.) work effectively on this codebase.

## Project Context

Recursive://Neon is a CLI-first RPG where the player interacts via a terminal shell. The game simulates SSHing into a remote system. Phases 0-6k are complete plus Phase 6l-1 (C-g keyboard-quit hardening), 6l-2 (keyboard-escape-quit + ESC-as-Meta), 6l-3 (true incremental search with match highlighting, wrap-around, state-stack backspace, smart case-fold + M-c toggle, multi-line search), 6l-4 (query-replace M-% with per-session undo stack, single post-session undo group, and the capture-mode session-object pattern that describe-key was retrofitted to), and 6l-5 (undo-chain granularity bug — two consecutive C-/ now walk distinct groups back through history). 1620 passing tests + 13 xfail (TD-006 regressions). **Phase 6l is now complete.** Phase 7 (deferred-items cleanup incl. TD-006 fix in 7c-5 and new 7c-6 aggressive undo coalescing) is next, followed by Phase 8 (browser terminal + desktop GUI).

## Architecture at a Glance

```
Shell programs (ProgramContext) ──→ Services (AppService, NPCManager) ──→ Models (GameState)
     ↑                                         ↑
Shell builtins (ShellSession) ──────→ ServiceContainer (DI)
```

- **Programs** get a restricted `ProgramContext` (args, stdout, services, cwd_id). They cannot modify shell state.
- **Builtins** get the full `ShellSession` and can modify cwd, env vars, etc.
- **Services** are accessed via `ServiceContainer` (dependency injection). Never instantiate directly.
- **Models** are Pydantic BaseModel instances. The virtual filesystem uses UUID-based `FileNode` objects.

## How to Add a New Shell Command

1. Create `async def prog_mycommand(ctx: ProgramContext) -> int` in an appropriate file under `shell/programs/`
2. Use `ctx.services.app_service` (or other services) for business logic
3. Write to `ctx.stdout` / `ctx.stderr` for output
4. Return 0 for success, nonzero for error
5. Register via `registry.register_fn("mycommand", prog_mycommand, "Help text", completer=my_completer)` in a `register_*` function
6. Call the registration function from `Shell.__init__` in `shell.py`
7. Write tests using the `make_ctx` fixture from `tests/unit/shell/conftest.py`

## How to Add a New Service

1. Define interface in `services/interfaces.py` (abstract class)
2. Implement in `services/my_service.py`
3. Add field to `ServiceContainer` dataclass in `dependencies.py`
4. Wire in `ServiceFactory.create_production_container()`
5. Add mock support in `ServiceFactory.create_test_container()`

## Key Patterns

- **Type hints**: use built-in `list[...]`, `dict[...]` (Python 3.14, no `typing.List`/`Dict`)
- **Async**: all I/O-bound operations are async. Use `asyncio.to_thread()` for blocking calls.
- **Testing**: pytest with auto-mode asyncio. Tests grouped in classes. Shell programs tested via `CapturedOutput`.
- **Persistence**: JSON files in `game_data/`. Use `_save_json`/`_load_json` helpers. Always handle corrupt files gracefully.
- **Virtual filesystem**: all paths resolve through `path_resolver.py` to UUID-based `FileNode` objects. Never use real file paths in game logic.

## Critical Rules

1. **Virtual filesystem isolation is sacred** — see `backend/FILESYSTEM_SECURITY.md`
2. **Use dependency injection** — never instantiate services directly
3. **Write tests** — every new feature needs tests
4. **Don't add features beyond what's tested** — V1's failure was breadth without depth

## Running Checks

```bash
cd backend
../.venv/Scripts/pytest              # All 1620 tests (13 xfail for TD-006)
../.venv/Scripts/ruff check .        # Lint
../.venv/Scripts/mypy                # Type check
```

All three must pass before committing.

## Key Files

| Purpose | Path |
|---------|------|
| Shell entry point | `backend/src/recursive_neon/shell/__main__.py` |
| Shell REPL + dispatch | `backend/src/recursive_neon/shell/shell.py` |
| Completion framework | `backend/src/recursive_neon/shell/completion.py` |
| Glob expansion | `backend/src/recursive_neon/shell/glob.py` |
| Tokenizer + pipeline parser | `backend/src/recursive_neon/shell/parser.py` |
| WS terminal sessions | `backend/src/recursive_neon/terminal.py` |
| WS client entry point | `backend/src/recursive_neon/wsclient/__main__.py` |
| Program registry | `backend/src/recursive_neon/shell/programs/__init__.py` |
| DI container | `backend/src/recursive_neon/dependencies.py` |
| Config | `backend/src/recursive_neon/config.py` |
| App service | `backend/src/recursive_neon/services/app_service.py` |
| NPC manager | `backend/src/recursive_neon/services/npc_manager.py` |
| TUI framework | `backend/src/recursive_neon/shell/tui/` |
| Editor core | `backend/src/recursive_neon/editor/` |
| Shell-in-editor | `backend/src/recursive_neon/editor/shell_mode.py` |
| Window system | `backend/src/recursive_neon/editor/window.py` |
| CodeBreaker minigame | `backend/src/recursive_neon/shell/programs/codebreaker.py` |
| Models | `backend/src/recursive_neon/models/` |
| Test fixtures | `backend/tests/conftest.py`, `backend/tests/unit/shell/conftest.py` |

## WebSocket Terminal Protocol (Phase 3)

The shell runs over WebSocket via `/ws/terminal`. Key concepts:
- **`InputSource` protocol** in `shell.py` — abstracts where command lines come from (prompt_toolkit, WebSocket queue, test mock)
- **`QueueOutput`** in `output.py` — pushes output to an `asyncio.Queue` for the WS handler to drain
- **`TerminalSessionManager`** in `terminal.py` — owns Shell instances by UUID, decoupled from WS connection lifecycle
- **Message protocol**: `input`, `output`, `prompt`, `complete`/`completions`, `mode`, `screen`, `key`, `exit`, `error` (all JSON)
- **WebSocket CLI client**: `python -m recursive_neon.wsclient` for interactive sessions; `--headless` for automation

## TUI Framework (Phase 4)

Full-screen apps run inside the terminal via raw mode. Key concepts:
- **`ScreenBuffer`** in `shell/tui/__init__.py` — 2D text grid with cursor, renders to ANSI or WebSocket `screen` messages
- **`TuiApp` protocol** — apps implement `on_start()`, `on_key()`, `on_resize()`
- **`run_tui_app()`** in `shell/tui/runner.py` — lifecycle manager: enters raw mode, routes keystrokes, delivers screens, exits cleanly
- **Raw mode switching**: server sends `{"type": "mode", "mode": "raw"}`, client sends `{"type": "key", "key": "ArrowUp"}` etc.
- **`ProgramContext.run_tui`** — callback wired by terminal session or local CLI to launch TUI apps

### How to Add a TUI App

1. Create a class implementing `TuiApp` (`on_start`, `on_key`, `on_resize`)
2. Use `ScreenBuffer` for rendering (set lines, move cursor, call `render_ansi()` or `to_message()`)
3. Return exit code from `on_key` to signal app termination
4. Register a shell command that calls `ctx.run_tui(my_app)`
5. See `programs/codebreaker.py` for the reference implementation

## Shell Features (Phase 5)

The shell supports Unix-like features:
- **Context-sensitive completion** — per-command completers registered via `CompletionFn` callbacks. `completion.py` provides `CompletionContext`, shared helpers. Each program registers its completer during `register_*_programs()`.
- **Glob expansion** — `tokenize_ext()` returns `Token(value, quoted)`. `glob.py` expands unquoted `*`, `?`, `[...]` against the virtual filesystem before dispatch. Quoted tokens are never expanded.
- **Pipes** (`|`) — `parse_pipeline()` splits at unquoted operators. Segments run sequentially; stdout captured via `CapturedOutput` and passed as `ProgramContext.stdin`. `cat` and `grep` read from stdin when piped.
- **Output redirection** (`>`, `>>`) — captured output written to virtual files.
- **Pipe-aware completion** — `_last_pipe_segment()` scopes completions to the current segment.

## Editor + Window System (Phase 6a-6i)

neon-edit is an Emacs-inspired TUI editor with:
- `Buffer`/`Mark` text model, undo/kill ring, layered keymaps, minibuffer, incremental search
- Variable system, mode infrastructure (fundamental-mode, text-mode, auto-fill-mode)
- **Window system** (Phase 6i): `Window` class with tracked point + scroll state, `WindowTree` binary split tree, 7 window commands (C-x 2/3/o/0/1, C-M-v, C-x 4 C-f)
- EditorView renders the window tree with per-window modelines and vertical dividers

## Editor polish (Phase 6l)

- **`keyboard-quit` / C-g hardening** (6l-1): `Editor._reset_transient_state()` helper clears every transient interactive flag (prefix keymap, prefix arg, describe-key session, query-replace session, region, ESC state). Top-level C-g intercept in `process_key` dispatches `keyboard-quit` from any context.
- **`keyboard-escape-quit` + ESC-as-Meta** (6l-2): bare Escape sets `_meta_pending`; the next non-ESC key is rewritten as `M-<key>` (ESC f → M-f). Three consecutive Escapes run `keyboard-escape-quit`, which dismisses the minibuffer via `mb.process_key("C-g")` (preserving isearch's point-restore), switches away from `*Help*`, and calls `_reset_transient_state()`. State machine runs at the top of `process_key`, *above* minibuffer routing but *below* describe-key capture (and now *below* query-replace capture too).
- **True incremental search** (6l-3): `isearch-forward` / `isearch-backward` (C-s / C-r) with match highlighting, wrap-around, state-stack backspace, smart case-fold + M-c toggle, M-Enter newline insertion for multi-line search. The old minibuffer-driven behaviour was renamed to `search-forward` / `search-backward` (M-x only).
  - **Styling architecture**: new `StyleSpan(row, col, width, style, priority)` dataclass in `shell/tui/__init__.py`. `EditorView._style_text_rows` post-compose pass (parallel to `_style_modeline_rows`) walks the composed plain-text screen and wraps character ranges in ANSI codes. Priority resolution per cell: strict `>`, stable by emission. Reserved priorities: 10 syntax (future), 20 non-current match, 25 current match, 30 region (future), 40 cursor line (future). This is the canonical extension point for syntax highlighting.
  - **`editor.highlight_term` / `highlight_case_fold`** — owned by whichever interactive command sets them (isearch, query-replace); cleared on exit/cancel/replay and also by `_reset_transient_state()` so keyboard-escape-quit covers them for free.
  - **`Buffer.find_forward` / `find_backward`** accept `\n` in the needle and a `case_fold=False` kwarg. Multi-line matching walks line-by-line without allocating a joined view. Available to all callers, not just isearch.
  - **`case-fold-search` defvar** — global default True; smart session rule: fold only while search text is all lowercase (Emacs behaviour). M-c explicitly toggles and shows `(case)` / `(fold)` in the prompt.
  - **Deviation from Emacs**: Emacs uses C-j for newline insertion in isearch, but `shell/keys.py:45-46` maps both `\r` and `\n` to `"Enter"`. M-Enter is used instead — unambiguous on every platform. Documented inline at the top of the isearch section in `default_commands.py`.
- **Query-replace (M-%)** (6l-4): Emacs-style interactive find-and-replace with the ten standard keys (y/SPC replace, n/DEL skip, q/RET exit, `.` once, `!` all, `u` undo, `U` undo-all, `e` edit replacement, C-g cancel, `?` help). Reuses the 6l-3 highlight mechanism — the current match is whichever match point is on (point-driven, no new field). Entry via two chained minibuffer prompts, both with M-Enter newline insertion for multi-line search/replacement.
  - **Capture-mode session-object pattern**: `_QueryReplaceSession` dataclass in `default_commands.py` (from/to text, case-fold, start point, `replacements` stack, `paused_for_edit`, count). Installed on `Editor._query_replace_session`; routing hook in `process_key` sits between describe-key and the ESC state machine, consuming keys before they reach the state machine so ESC inside a session is an invalid key (cancellation goes through `C-g` or `keyboard-escape-quit`). Cleared by `_reset_transient_state()`. **Describe-key was refactored to use the same pattern** — six scattered fields on `Editor` collapsed into a single `_DescribeKeySession`. Any future capture mode (plausible: `query-replace-regexp`) should follow this convention.
  - **Single-undo-group on exit**: query-replace keystrokes bypass `_execute_command_by_name`, so no `add_undo_boundary()` calls fire during the session. Raw `buf.delete_region` + `buf.insert_string` ops for replacements *and* for `u`/`U` reverts pile into one contiguous run in `Buffer.undo_list`. A post-session `C-/` walks the whole run LIFO and reverts everything at once. The session's own `_Replacement` stack handles `u`/`U` at a higher level. Alternate design (per-replacement boundaries + exit-collapse) is recorded in `V2_HANDOVER.md` 6l-4 addendum in case the compound-reverts model produces problems with future features.
  - **`e` (edit replacement) sub-phase**: nested minibuffer pre-filled with current `to_text`; a `paused_for_edit` flag on the session suppresses the top-level query-replace routing so the minibuffer handles keys normally. The minibuffer's `process_key` is patched (isearch precedent) so resume works on both submit and cancel.
  - **Deviation from Emacs**: `?` help is a one-line message-area legend instead of Emacs's pop-up window — faithful behaviour would require real window-splitting with auto-restore (disproportionately complex). `case-replace` and `M-c` mid-session toggle are explicitly NOT implemented (not in spec; deferred).
- **Undo-chain granularity fix (6l-5)**: two consecutive `C-/` presses now walk two distinct undo groups back through history instead of flipping into redo on the second press. Two-layered fix: (1) `Editor._execute_command_by_name` / `execute_command` skip the pre-command `add_undo_boundary()` call when dispatching `undo`, because `add_undo_boundary`'s chain-break side effect (clears `last_command_type == "undo"`, resets `_undo_cursor`) defeats `Buffer.undo()`'s consecutive-undo tracking. (2) `Buffer.undo()` now inserts an `UndoBoundary` before extending its reverse entries onto the undo list — without this, a later chain-break followed by another undo walks both the reverse group and the source group in a single pass, collapsing two user-visible states into one keystroke. `add_undo_boundary()` grew an optional `break_undo_chain: bool = True` kwarg so `undo()` can append a boundary without breaking its own chain. See `tests/unit/editor/test_undo_chain.py` for the regression surface and the rationale docstring.

## Shell-in-Editor (Phase 6j)

Run the game's shell inside an editor buffer (`M-x shell`), like Emacs comint-mode:
- **Direct execution model**: the Shell's `run()` loop is not used. The editor's Enter key handler stores a pending async callback; the TUI runner's `on_after_key()` hook awaits `shell.execute_line()` and appends output to the buffer.
- **`editor/shell_mode.py`**: `BufferOutput` (ANSI-stripped output capture), `ShellState` (per-buffer state), `setup_shell_buffer()`, comint commands (Enter, M-p, M-n, Tab).
- **Async bridge**: `on_after_key` is a backward-compatible TUI runner extension — existing apps unaffected.
- **Shell factory**: `Editor.shell_factory` callback decouples the editor from the service layer; set by the `edit` shell program.
- **Deferred**: interactive programs (chat), TUI apps in shell buffer, output region protection — see handover.

## Tutorial Verification + `describe-bindings` (Phase 6k)

- **`describe-bindings` (C-h b)** in `editor/default_commands.py` lists every reachable keybinding in a `*Help*` buffer, grouped by layer (buffer-local → minor → major → global). Use `_format_bindings_local` (no parent walk) when showing bindings by layer so inherited bindings don't duplicate under each header.
- **Tutorial walk-through test** (`tests/unit/editor/test_tutorial_walkthrough.py`, 72 tests) exercises every chapter of `TUTORIAL.txt` via `EditorHarness`. When adding new editor features that belong in the tutorial, add a matching test class there.
- **Window-tree gotcha for tests**: `EditorView.on_key` calls `_ensure_editor_on_buffer(active_window.buffer)` at the start of every keystroke. If a test uses `editor.create_buffer()` to make a new buffer current and then sends a key, the active window silently reverts the editor's current buffer to whatever the window shows. To test commands on a specific buffer, route through `C-x b switch-to-buffer` key events (the proper flow updates the window too).
- **Variable-registry leakage**: `M-x set-variable` and `C-x f` mutate `VARIABLES[name].default` (module-level global). Tests that touch `fill-column` or similar must save/restore defaults — see the `_restore_global_variables` autouse fixture in `test_tutorial_walkthrough.py` for the pattern.

## What's Next (Phase 7, then Phase 8)

**Phase 6l is complete** — the editor polish pass landed everything scheduled plus the undo-granularity fix.

- **Phase 7** — deferred-items cleanup (7a-7f): shell buffer completions, `on_tick` / auto-refresh, extensibility API, game-world hooks, future TUI apps, **TD-006** (filesystem name uniqueness + editor `save_callback` multi-buffer bug, 7c-5), and the newly-added **7c-6 aggressive undo-group coalescing** (runs of Backspace / C-d / kill / yank merge into a single undo group, discovered during 6l-5 — scheduled before Phase 8 so every future frontend inherits the improved granularity).
- **Phase 8** — browser terminal + desktop GUI: xterm.js over `/ws/terminal`, raw/cooked rendering, desktop chrome, cyberpunk CSS restore.

See `docs/V2_HANDOVER.md` for the full plan.
