<!-- HANDOVER-ARCHIVE — companion to docs/V2_HANDOVER.md -->
<!-- Do not use this file for /resume-feature or /implement-next-phase -->

# V2 Handover Archive

**Active handover document**: [V2_HANDOVER.md](./V2_HANDOVER.md)

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
