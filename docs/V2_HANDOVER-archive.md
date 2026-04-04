<!-- HANDOVER-ARCHIVE — companion to docs/V2_HANDOVER.md -->
<!-- Do not use this file for /resume-feature or /implement-next-phase -->

# V2 Handover Archive

**Active handover document**: [V2_HANDOVER.md](./V2_HANDOVER.md)

---

## Retired on 2026-04-04

### Phase 6b: Improved notes integration — COMPLETE
With the editor available, notes commands open neon-edit for interactive editing using a `# Title` first-line convention.

- `note edit <ref>` opens the note in neon-edit (first line `# Title`, rest is content). On save, title and content are parsed back. Inline flags (`-t`/`-c`) still work for backward compatibility.
- `note create <title>` without `-c` opens the editor pre-filled with `# Title`. On save, the note is created. The `-c` flag still creates immediately without the editor.
- When TUI mode is unavailable, `note edit` shows an error suggesting flags; `note create` falls back to creating an empty note.
- 946 total tests (19 new: format/parse helpers, editor integration for both create and edit, fallback paths).

### Phase 6c: System monitor TUI — COMPLETE
A fake "htop"-style system monitor showing in-game processes. `Process` and `ProcessState` models in `models/process.py`. `sysmon` shell command launches the TUI with animated CPU/memory bars, process list, and sort/kill key bindings. 980 total tests.

Future 6c candidates (not scheduled):
- File browser TUI (navigate virtual filesystem, preview files, open in editor)
- Port scanner minigame (network puzzle)
- Memory dump minigame (hex viewer puzzle)

### Phase 6d: Notes browser in neon-edit — COMPLETE
Interactive notes browser inside the editor. Loose coupling approach: a `*Notes*` read-only buffer with buffer-local keymap lists notes; Enter opens a note in a new buffer with `# Title` convention and save callback.

- `note browse` command opens neon-edit with the `*Notes*` buffer
- Buffer-local keymaps: `Buffer.keymap` field, checked first by `_resolve_keymap()`, falls through to global via parent
- Callable keymap targets: `BindingTarget` now accepts `Callable[..., Any]` alongside command name strings
- `Buffer.on_focus` callback: triggered on `switch_to_buffer` / `remove_buffer`, used to auto-refresh the note list
- `kill-buffer` command (C-x k): remove a buffer with minibuffer prompt
- Improved prefix key display: "C-x z is undefined" instead of "z is undefined"
- Windows C-h / Backspace disambiguation via `_win_ctrl_pressed()`
- 1031 total tests (51 new: 12 notes browser, 8 buffer-local keymaps, 7 callable targets, 5 kill-buffer, 3 prefix display, 3 on_focus, plus supporting tests).

### Phase 6e: Test harness + viewport scrolling + tutorial document — COMPLETE
Programmatic test harness for TUI-level editor testing, viewport scrolling commands, game-themed tutorial document, and a bugfix for C-u prefix digit parsing.

- `EditorHarness` class (`tests/unit/editor/harness.py`): `send_keys(*keys)`, `type_string(s)`, `screen_text(row)`, `screen_lines()`, `cursor_position()`, `message_line()`, `modeline()`, `buffer_text()`, `point()`. Factory: `make_harness(text, width, height)`. ANSI auto-stripping on all screen accessors.
- `Viewport` protocol (`editor/viewport.py`): `scroll_top`, `text_height`, `scroll_to`. EditorView implements it and sets `editor.viewport = self`. Commands fall back gracefully when viewport is None (headless).
- `scroll-up` (C-v / PageDown): forward one screenful, move point to top of new viewport
- `scroll-down` (M-v / PageUp): backward one screenful, move point to bottom of new viewport
- `recenter` (C-l): center viewport around point; consecutive presses cycle center/top/bottom
- Tutorial document (`initial_fs/Documents/TUTORIAL.txt`): ~280-line game-themed tutorial (Apache 2.0), Emacs tutorial pedagogical structure, 14 chapters. Chapters 10-14 marked `[NOT YET IMPLEMENTED]` at the time.
- `help-tutorial` (C-h t): opens the tutorial in a read-only buffer; re-opening switches to existing buffer
- Bugfix: C-u prefix digit parsing — `_prefix_has_digits` now properly initialized and reset, fixing a bug where digits after C-u failed to replace the default 4 after any prior command had executed
- 1073 total tests (42 new: 14 harness, 22 scroll/viewport, 5 tutorial, 1 prefix-arg fix).

### Phase 6f: Sentence motion, undo alias, help commands, save-some-buffers — COMPLETE
**Goal**: Implement the "easy" missing tutorial commands — straightforward features that don't require new infrastructure.

- Sentence motion on Buffer: `forward_sentence`, `backward_sentence`, `kill_sentence` (sentence ends at `.`/`?`/`!` followed by whitespace or end-of-line)
- `backward-sentence` (M-a), `forward-sentence` (M-e), `kill-sentence` (M-k)
- `C-x u` → undo (keybinding alias in C-x prefix keymap)
- `describe-key-briefly` (C-h c): show binding in message area (not *Help* buffer)
- `describe-mode` (C-h m): show current mode and key bindings in *Help* buffer, recurses into prefix keymaps
- `where-is` (C-h x): prompt for command name, show which key(s) it's bound to (reverse keymap lookup via `Keymap.reverse_lookup()`)
- `save-some-buffers` (C-x s): iterate modified buffers with y/n minibuffer prompt, save confirmed ones via chained callbacks
- 1120 total tests (47 new: 22 sentence motion/kill, 25 commands/keybindings/help/save-some-buffers/reverse-lookup).

### Phase 6g: Variable system + mode infrastructure — COMPLETE
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
- 1172 total tests (52 new: 29 variable system, 23 mode system).

### Phase 6h: Replace string + text filling — COMPLETE
**Goal**: Implement the text manipulation commands the tutorial covers: interactive find/replace and paragraph filling.

- `replace-string` (M-x replace-string): two sequential minibuffer prompts (search, replacement), replaces all from point to end of buffer, reports count, undoable as one group
- `fill-paragraph` (M-q): rewrap current paragraph to `fill-column` width, paragraph boundaries at blank lines. Helpers: `_find_paragraph_bounds()` (blank-line delimited), `_fill_lines()` (word-wrap reflow)
- `set-fill-column` (C-x f): with prefix arg sets to that value, without sets to current column
- `auto-fill-mode` (M-x auto-fill-mode): minor mode toggle, auto-breaks lines at fill-column during self-insert via `_auto_fill_break()` hook in `self-insert-command`. Modeline shows "Fill" when active.
- `Mode.indicator` field: optional short modeline string for minor modes (falls back to name-derived string if empty)
- 1215 total tests (43 new: 13 replace-string, 5 paragraph bounds, 6 fill-lines, 9 fill-paragraph, 3 set-fill-column, 7 auto-fill-mode).

### Phase 6i: Window system — COMPLETE
**Goal**: Emacs-style window splitting so a single frame displays multiple buffers simultaneously. The prerequisite for shell-in-editor and the "desktop environment" vision.

**Architecture**:
- `Window` class (`editor/window.py`): `buffer`, `_point` (tracked Mark), `scroll_top`, layout fields (`_height`, `_width`, `_top`, `_left`). Implements `Viewport` protocol (`scroll_top`, `text_height`, `scroll_to`). Factory `Window.for_buffer(buf)` creates a window with a tracked mark at the buffer's point.
- `SplitDirection` enum: `HORIZONTAL` (C-x 2, top/bottom), `VERTICAL` (C-x 3, left/right)
- `WindowSplit` dataclass: `direction`, `first` (WindowNode), `second` (WindowNode). `WindowNode = Window | WindowSplit`.
- `WindowTree` class: manages the binary split tree. `root: WindowNode`, `active: Window`. Methods: `split()`, `delete_window()`, `next_window()`, `windows()` (depth-first leaf list), `delete_other_windows()`, `is_single()`, `other_window()`.

**Dual-point sync**: `Window._point` is a tracked Mark in the buffer (maintained by mark tracking during insert/delete). Movement commands only move `buffer.point`, so EditorView syncs after each key: `active._point ← buffer.point`. On window switch: save old `buffer.point → old._point`, restore `new._point → buffer.point`, update `editor.viewport` to new window, switch editor's current buffer. Existing 1215+ headless tests see `_window_tree = None` and are unaffected.

**EditorView refactored**: creates a `WindowTree` on init (single root window). `_render()` walks the tree: `_compute_layout()` assigns regions, `_render_window()` draws text + modeline per window, `_render_dividers()` draws `│` columns for vertical splits. Active modeline: `\033[7m` (reverse), inactive: `\033[2;7m` (dim reverse). Message line is global (last screen row). `ScreenBuffer.set_region()` added for column-range writes.

**Single-window equivalence**: window height = `total - 1` (message), text_height = `height - 1` (modeline), so text_height = `total - 2`. Identical to the previous single-window layout. All existing TUI tests produced the same output.

**Commands**: `split-window-below` (C-x 2), `split-window-right` (C-x 3), `other-window` (C-x o), `delete-window` (C-x 0), `delete-other-windows` (C-x 1), `scroll-other-window` (C-M-v), `find-file-other-window` (C-x 4 C-f). New `C-x 4` prefix keymap.

**Files**: new `editor/window.py`, modified `editor/editor.py` (+1 field), `editor/view.py` (refactored), `editor/default_commands.py` (+7 commands), `shell/tui/__init__.py` (+`set_region`), `editor/__init__.py` (exports). Tests: `test_window.py`, `test_window_view.py`, `test_window_commands.py` (~65 new tests).

### Phase 6j: Shell-in-editor (shell mode) — COMPLETE
**Goal**: Run the game's shell inside an editor window, like Emacs `M-x shell`. The keystone feature that makes neon-edit the game's "desktop environment."

**Architecture — direct execution model**: The Shell's `run()` loop is NOT used. Instead, the editor drives command execution: user presses Enter → `on_key()` (sync) extracts input, stores an async callback on `editor._pending_async` → TUI runner calls `EditorView.on_after_key()` (async) which awaits `shell.execute_line()` → output appended to buffer → new prompt rendered. This avoids background-task coordination entirely.

**Async bridge — `on_after_key` protocol**: 4-line backward-compatible addition to `run_tui_app()`. After each keystroke, the runner checks for an optional `on_after_key()` method on the TuiApp and awaits it. Existing TUI apps (CodeBreaker, sysmon, notes browser) have no such method and are unaffected.

**Components**:
- `BufferOutput(Output)` (`editor/shell_mode.py`): captures shell output as ANSI-stripped plain text for buffer insertion.
- `ShellState` dataclass: per-buffer state — Shell reference, `input_start` mark (kind="left"), history index, saved input, finished flag. Stored as `buf._shell_state`.
- `ShellBufferInput`: stub `InputSource` that raises `EOFError` for interactive programs (chat, etc.) — deferred to future phase.
- `setup_shell_buffer()`: initialises buffer with shell-mode keymap, welcome banner, prompt, tracked marks.
- Shell-mode keymap: Enter → `_comint_send_input`, M-p/M-n → history navigation, Tab → completion. Parent = global keymap, so all normal editing keys work.
- `execute_shell_command()`: async function that runs the command, captures output via `BufferOutput`, appends output + new prompt, updates `input_start` mark. Undo recording disabled during output insertion.

**Editor integration**:
- `Editor.shell_factory: Callable[[], Any]` — set by the `edit` shell program to create Shell instances.
- `Editor._pending_async: Callable[[], Awaitable[None]]` — set by Enter handler, consumed by `on_after_key`.
- `EditorView.on_after_key()` — awaits `_pending_async`, syncs window, re-renders.

**Commands**: `shell` (M-x shell) creates or switches to `*shell*` buffer. Modeline shows `(Shell)`.

**Deferred to future phases** (tracked in 6l-5):
- Raw-mode TUI apps inside the shell buffer (requires raw-mode passthrough)
- Interactive programs (chat) need a minibuffer↔get_line bridge for sub-prompts
- Output region protection (per-region read-only) — buffer is fully writable; shell reads only from input_start to EOB
- ANSI rendering in buffer (would need attributed-text model)
- The `on_after_key` pattern is general-purpose and could support other async features (e.g., background NPC responses)

**Files**: new `editor/shell_mode.py` (~310 lines), modified `editor/editor.py` (+2 fields), `editor/view.py` (+`on_after_key`), `shell/tui/runner.py` (+4 lines), `shell/programs/edit.py` (+shell_factory wiring), `editor/default_commands.py` (+1 import), `editor/__init__.py` (exports). Tests: `test_shell_mode.py` (66 new tests). 1348 total tests.

### Phase 6k: Tutorial verification + polish — COMPLETE
**Goal**: Verify every feature in the tutorial works end-to-end. Fix gaps, polish UX.

- **Tutorial walk-through integration test** — `test_tutorial_walkthrough.py` exercises every chapter (1–14) programmatically via `EditorHarness`. 72 tests covering movement, scrolling, editing, kill/yank, mark/region, word/sentence motion, search, files/buffers, help, replace, fill, windows, and shell mode (async). Autouse fixture saves/restores `VARIABLES` defaults so fill-column mutations don't leak across tests.
- **`describe-bindings` (C-h b)** — Lists every reachable keybinding grouped by layer (buffer-local → minor modes → major mode → global). Prefix keymaps recursively expanded (`C-x C-s`, `C-h k`, `C-x 4 C-f`, …). New `_format_bindings_local` helper prevents parent-chain duplication between layers. 10 new tests in `test_help.py`.
- **TUTORIAL.txt cleanup** — Removed all 5 `[NOT YET IMPLEMENTED]` markers (chapters 10–14). Each chapter now has real practice prompts. Quick Reference expanded with sentence motion, fill, windows, shell mode, `C-h b`, `C-h m`, `C-h v`, `C-x s`.
- **Modeline improvements** — Listed as a deliverable but already shipped in 6g/6h (`(Shell)`, `(Text Fill)`, `(Fundamental)`). Walk-through tests verify this now works end-to-end.
- 1433 total tests (82 new: 72 walkthrough, 10 describe-bindings).

**Files**: modified `editor/default_commands.py` (+58 lines: describe-bindings + `_format_bindings_local` + `C-h b` binding), `initial_fs/Documents/TUTORIAL.txt` (+51/−22), `tests/unit/editor/test_help.py` (+10 tests); new `tests/unit/editor/test_tutorial_walkthrough.py` (787 lines, 72 tests).

**Deferred from 6k** (carried forward into Phase 6l-5):
- **Python config file loading** — the `EditorVariable`/`Mode` API exists (Phase 6g) but there is no `~/.neon-edit.py` loader or sandboxed extension entry point. Tracked in the long-standing "Future 6a extensions" list as the "Python extension API" item.
- **Game-world integration hooks** — no NPC-triggered buffer events, no in-game script callbacks, no editor↔game-state bridge.
- **Syntax highlighting** — already listed under "Future 6a extensions"; still deferred.
- **Undo granularity inspection** — observed during the walk-through that a second C-/ after Backspace appears to redo rather than continue undoing.

---

## Retired on 2026-03-27

### Section 3: What Was Done (Phase 0)

#### 3.1 Branch Setup
- Stashed uncommitted changes on `claude/improve-terminal-input-*`
- Renamed `master` → `legacy/v1`
- Created orphan branch `main`, later renamed to `master`
- Old `master` (v1 code) renamed to `legacy` on the remote
- Cleared working tree, selectively restored files from `legacy/v1`

#### 3.2 Files Kept and Cleaned

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

#### 3.3 What Was Deliberately Excluded
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

### Phase 1: Build the Python CLI Shell — COMPLETE
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

### Phase 2: Deepen Core Features — COMPLETE
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

### Phase 3: WebSocket Terminal Protocol + CLI Client — COMPLETE
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

### Phase 4: TUI Apps (Raw Mode) — COMPLETE
**Goal**: Interactive full-screen apps that run inside the terminal, driven by keystroke input. Testable via both the local CLI and the WebSocket client from Phase 3.

Completed:
1. **Raw mode protocol**: Server sends `{"type": "mode", "mode": "raw"|"cooked"}` to switch modes. Client sends `{"type": "key", "key": "..."}` for keystrokes in raw mode. Mode-aware message routing ignores wrong-mode messages.
2. **TUI framework** (`shell/tui/`): `ScreenBuffer` (2D text grid with cursor), `TuiApp` protocol (`on_start`/`on_key`/`on_resize`), `RawInputSource` protocol, `run_tui_app()` lifecycle manager.
3. **CodeBreaker minigame**: Mastermind-style TUI game with ANSI-colored rendering, arrow key navigation, symbol cycling, win/loss detection. Registered as `codebreaker` shell command.
4. **Local terminal support**: `LocalRawInput` for platform-specific keystroke reading + alternate screen buffer.
5. **WebSocket client raw mode**: Platform-specific raw key reading (Windows `msvcrt` / Unix `tty.setraw`). Headless mode (`--headless`) for automation.
6. **Tests**: 57 new tests — TUI framework (19), CodeBreaker (27), terminal raw mode + WS integration (11). 402 total tests, all passing.

### Phase 5: Context-Sensitive Completion + Shell Improvements — COMPLETE
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

### Phase 6a: Text Editor ("neon-edit") — COMPLETE

#### Architecture
A lightweight Emacs-inspired TUI editor. The editor is structured as a set of Python classes and functions for editing text, wrapped by a thin TUI shell. The architecture draws from the Zwei → Hemlock → GNU Emacs lineage:

- **Text storage**: List of Python strings (one per line), inspired by Zwei/Hemlock's linked-list-of-lines model. Newlines are implicit between lines.
- **Positions**: `Mark(line, col, kind)` following Hemlock — with left-inserting / right-inserting kinds for correct behavior during insertions.
- **Commands**: Named functions with prefix arg (Hemlock's `defcommand` model), registered in a command table.
- **Key binding**: Layered keymaps with inheritance (Hemlock ordering: buffer > minor modes > major mode > global). Prefix keys (C-x) are sub-keymaps.
- **Undo**: Emacs-style unlimited undo list with boundary markers between command groups. Undo is itself undoable.
- **Kill ring**: List of strings with yank pointer (Emacs model). Consecutive kills merge.

#### 6a-1. Buffer Primitives — COMPLETE
Pure data model — no TUI, no keybindings, just text manipulation and movement.

- `Buffer` class: `name`, `lines: list[str]`, `point: Mark`, `mark: Mark | None`, `modified: bool`, `filepath: str | None`
- `Mark` class: `line: int`, `col: int`, `kind: str` (temporary / left-inserting / right-inserting)
- Primitive operations: `insert_char`, `insert_string`, `delete_char_forward`, `delete_char_backward`, `delete_region`, `get_region_text`
- Mark maintenance: all marks adjust correctly when text is inserted/deleted (left-inserting stays left of new text, right-inserting stays right)
- Line splitting/joining: Enter splits a line, backspace at col 0 joins with previous
- Point movement: `forward_char`, `backward_char`, `forward_line`, `backward_line`, `beginning_of_line`, `end_of_line`, `beginning_of_buffer`, `end_of_buffer`
- Thorough tests for all primitives and mark behavior

#### 6a-2. Undo + Kill Ring — COMPLETE
Non-destructive editing support.

- Undo list (Emacs-style): `UndoInsert`, `UndoDelete`, `UndoBoundary` entries. Primitives push undo records automatically. Undo walks backwards through one command group. Undo itself is undoable.
- Kill ring: `push`, `append_to_top` (for consecutive kills), `yank`, `rotate`. Last-command-type tracking for kill merging.
- Kill commands: `kill_line` (C-k), `kill_region` (C-w), `kill_word_forward` (M-d)
- Yank: `yank` (C-y), `yank_pop` (M-y)
- Tests for undo/redo round-trips, kill merging, yank rotation

#### 6a-3. Command System + Keymaps — COMPLETE
Dispatch layer connecting keystrokes to buffer operations.

- `Command` dataclass: `name`, `function(editor, prefix)`, `doc`
- Command registry: `@defcommand` decorator, `COMMANDS` dict
- `Keymap` class: `bindings: dict[tuple[str,...], str | Keymap]`, `parent` for inheritance. Prefix keys (C-x) are sub-keymaps.
- Keymap resolution: global → major mode → minor modes → buffer-local (Hemlock ordering)
- `Editor` class: owns buffer list, current buffer, global keymap, command dispatch loop
- Prefix argument (C-u): repeat count for commands
- Register all 6a-1/6a-2 operations as named commands with Emacs keybindings
- Tests for keymap lookup, prefix keys, command dispatch

#### 6a-4. TUI View + Shell Integration — COMPLETE
The thin shell that renders the editor in the terminal.

- `EditorView` (TuiApp implementation): renders buffer text, status line, cursor position into ScreenBuffer. Scrolling/viewport tracking.
- Status line: filename, modified flag, line:col, mode name (Emacs-style modeline)
- Key translation: map TUI key events to editor key notation (`"C-f"`, `"M-x"`, `"C-x C-s"`)
- `neon-edit <path>` shell command: opens file from virtual filesystem
- File I/O: load from / save to virtual filesystem FileNodes
- Minibuffer (stretch): single-line input for save-as, M-x command-by-name
- Tests for rendering, scrolling, file round-trips, shell integration

#### E1-E5. Editor Enhancements — COMPLETE
Post-6a-4 incremental improvements to make the editor genuinely usable.

**E1. Word Movement, Additional Keys, Read-Only Buffers**
- `forward_word` (M-f), `backward_word` (M-b) with alphanumeric + underscore word boundaries
- `kill_word_backward` (M-Backspace) with kill ring integration
- Arrow key bindings (Left/Right/Up/Down, Home, End, Delete)
- `read_only` flag on Buffer — insert/delete operations return early, movement still works
- 30 tests

**E2+E3. Minibuffer, M-x, File Ops, Buffer Switching**
- `Minibuffer` class: single-line input widget with prompt, cursor, text editing (C-a/C-e/C-k/C-d/Backspace/arrows), tab completion cycling, on_change callback
- `execute-extended-command` (M-x): minibuffer with command name completer
- `find-file` (C-x C-f): open file from virtual filesystem or create new buffer, with path completion
- `write-file` (C-x C-w): save-as with path prompt
- `switch-to-buffer` (C-x b): buffer switching with name completer
- `list-buffers` (C-x C-b): read-only buffer list display
- 38 minibuffer tests

**E4. Incremental Search (C-s / C-r)**
- `Buffer.find_forward()` / `Buffer.find_backward()`: text search from a given position
- `isearch-forward` (C-s) / `isearch-backward` (C-r): live minibuffer search with on_change handler
- Repeatable search (C-s again in minibuffer advances to next match)
- Direction toggling, position stack for backspace-undo
- 21 tests

**E5. Help System + open_callback**
- `describe-key` (C-h k): prompts for a key, shows binding and command doc in *Help* buffer
- `command-apropos` (C-h a): pattern search across command names and docstrings
- `_show_help_buffer()`: creates/switches to read-only *Help* buffer
- `open_callback` / `path_completer` on Editor: wired by shell `edit` program for C-x C-f integration
- 9 tests

927 total tests (359 new for editor), all passing. Lint and type checks clean.

### Retired Known Issues

1. ~~**No Python venv exists**~~ — **Resolved.** A `.venv` is created with `uv venv --python 3.14` and deps installed via `uv pip install -e "backend/.[dev]"`.

2. ~~**CLAUDE.md is outdated**~~ — **Resolved.** Rewritten for v2 with setup commands, quality tooling, and key entry points.

3. ~~**`npc_manager.py` uses LangChain ConversationChain**~~ — **Resolved.** Migrated to direct LLM invocation via `langchain_core.messages`. `ConversationChain` and `ConversationBufferWindowMemory` removed; the NPC model's own conversation history is used directly.

6. ~~**Remote `origin/master` still exists**~~ — **Resolved.** Remote reorganized: old `master` (v1) → `legacy`, `main` (v2) → `master` (default branch).

### Retired Status Snapshot

As of 2026-03-27: Phases 0-5 + 6a (editor) + E1-E5 (editor enhancements) complete. 927 tests passing. Phase 6b (notes integration) next.
