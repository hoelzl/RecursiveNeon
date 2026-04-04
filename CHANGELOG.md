# Changelog

All notable changes to Recursive://Neon are documented here.

## Phase 6j — Shell-in-Editor (2026-04-04)

### Added
- **Shell-in-editor (M-x shell)** — Run the game's shell inside an editor buffer, like Emacs comint-mode. `shell-mode` major mode with a buffer-local keymap. Type commands at a prompt, press Enter, see output appear inline. The shell is an in-process Python object (no subprocess).
- **Async bridge (`on_after_key`)** — Backward-compatible TUI runner extension: after each keystroke, the runner checks for an optional async `on_after_key()` method on the TuiApp and awaits it. Enables sync `on_key()` to trigger async shell command execution. Existing TUI apps are unaffected.
- **`BufferOutput`** — `Output` subclass that captures shell output as ANSI-stripped plain text for insertion into the editor buffer.
- **`ShellState`** — Per-buffer shell state tracking: Shell reference, `input_start` mark, history navigation index, finished flag.
- **Shell-mode commands**: `comint-send-input` (Enter), `comint-previous-input` (M-p), `comint-next-input` (M-n), shell Tab completion.
- **`Editor.shell_factory`** — Callback set by the `edit` shell program so `M-x shell` can create Shell instances without the editor knowing about the service layer.
- **`Editor._pending_async`** — General-purpose mechanism for commands to schedule async work that the TUI runner executes after the current keystroke.
- **66 new tests** — `test_shell_mode.py`: ANSI stripping (5), BufferOutput (6), setup (9), input extraction (4), input replacement (4), comint-send-input (5), history navigation (8), completion (5), async execution (8), on_after_key (3), M-x shell command (4), integration (5). 1348 total tests.

## Phase 6i — Window System (2026-04-04)

### Added
- **Emacs-style window splitting** — `Window` class with independent cursor (tracked `Mark`) and scroll state per window. `WindowTree` manages a binary tree of horizontal/vertical splits. Each window implements the `Viewport` protocol for per-window scrolling.
- **Window commands**: `split-window-below` (C-x 2), `split-window-right` (C-x 3), `other-window` (C-x o), `delete-window` (C-x 0), `delete-other-windows` (C-x 1), `scroll-other-window` (C-M-v), `find-file-other-window` (C-x 4 C-f). New `C-x 4` prefix keymap.
- **Window rendering** — EditorView refactored to render a window tree: per-window text regions, per-window modelines (active = bright reverse, inactive = dim reverse), vertical dividers (`│`) for side-by-side splits, global message line at bottom.
- **`ScreenBuffer.set_region()`** — Column-range write method for rendering vertical split windows without disturbing adjacent content.
- **Dual-point sync** — Window-local tracked marks stay correct during edits via buffer mark tracking. Movement sync happens around each keystroke dispatch. All 1215 pre-existing headless and TUI tests pass unchanged.
- **67 new tests** — `test_window.py` (30: tree ops, point tracking), `test_window_view.py` (15: rendering), `test_window_commands.py` (22: command integration + headless no-ops). 1282 total tests.

### Fixed
- **`Buffer.track_mark()` identity bug** — Changed from equality-based (`not in`) to identity-based (`any(t is m ...)`) duplicate detection. Two marks at the same position but different objects (e.g., `buffer.point` and `window._point`) were incorrectly treated as duplicates, preventing multi-window point tracking.

## Phase 5 — Shell Improvements (2026-03-26)

### Added
- **Context-sensitive tab completion** (5a) — Per-command completion framework. Programs register `CompletionFn` callbacks via `ProgramRegistry`. New `shell/completion.py` with `CompletionContext`, shared helpers (`complete_paths`, `complete_flags_or_paths`, `complete_choices`).
  - `cd` completes directories only
  - `ls`, `rm`, `grep`, `find`, `mkdir` complete their flags
  - `note` / `task` complete subcommands, then dynamic note indices / task list names / task refs
  - `chat` completes NPC IDs dynamically
  - `help` completes all command names
  - Unknown commands fall back to path completion
  - Works over WebSocket (same `get_completions_ext` path)
- **Shell-level glob expansion** (5b) — `tokenize_ext()` returns `Token(value, quoted)` with quoting metadata. New `shell/glob.py` expands unquoted `*`, `?`, `[...]` against the virtual filesystem before dispatch. Quoted tokens pass through unchanged (POSIX behavior). Unmatched globs are literal.
- **Pipes and output redirection** (5c) — `parse_pipeline()` splits command lines at unquoted `|`, `>`, `>>`. Pipeline segments execute sequentially with buffered stdout passing. `CapturedOutput` (no ANSI codes) used for pipes/redirects. `ProgramContext.stdin` field added; `cat` and `grep` read from it when piped. Redirect writes to virtual files. Stderr always goes to real output.
- **Pipe-aware tab completion** — `_last_pipe_segment()` scopes completions to the current segment after `|`.
- **125 new tests** — context-sensitive completion (58), glob expansion (33), pipes/redirection (34). 527 total tests.

### Changed
- `ProgramRegistry.register` / `register_fn` accept optional `completer` parameter
- `ProgramEntry` gains `completer` field; `get_completer()` method added
- `Shell.get_completions_ext` delegates to per-command completers; `ShellCompleter` simplified to wrapper
- `Shell.execute_line` uses `parse_pipeline` → `expand_globs` → segment execution pipeline
- `builtins.py` exports `BUILTIN_COMPLETERS` dict
- `_get_current_argument` and `_quote_path` moved to `completion.py` (re-exported from `shell.py` for compat)
- Integration test for `find -name` now quotes the glob pattern (required by shell-level expansion)

## Post-Phase 4 Fixes (2026-03-26)

### Changed
- **LangChain migration** — Replaced deprecated `ConversationChain` + `ConversationBufferWindowMemory` from `langchain_classic` with direct LLM message invocation using `langchain_core.messages`. The NPC model already tracked conversation history, making LangChain's memory abstraction redundant. Eliminates all `LangChainDeprecationWarning` messages.
- **Simplified mock LLM** — Test fixtures no longer need `predict`, `generate_prompt`, `BaseChatModel` spec; only `invoke`/`ainvoke` returning `AIMessage`.

### Fixed
- **Chat autocomplete** — Shell tab-completion no longer pops up while chatting with NPCs. Added `complete` parameter to `get_line` protocol.
- **Chat history isolation** — Chat messages no longer pollute shell command history (and vice versa). Added `history_id` parameter to `get_line`; chat uses a separate `InMemoryHistory`.
- **Pydantic v1 warning** — Moved `warnings.filterwarnings` from `shell/__main__.py` and `main.py` to `recursive_neon/__init__.py` so it takes effect before transitive imports trigger the warning.

## Phase 4 — TUI Apps / Raw Mode (2026-03-25)

### Added
- **Raw mode protocol** — Server sends `{"type": "mode", "mode": "raw"|"cooked"}` to switch terminal modes. Client sends `{"type": "key", "key": "..."}` in raw mode; server ignores wrong-mode messages.
- **TUI framework** (`shell/tui/`):
  - `ScreenBuffer` — 2D text grid with cursor position, visibility, and ANSI rendering
  - `TuiApp` protocol — `on_start()`, `on_key()`, `on_resize()` interface for full-screen apps
  - `RawInputSource` protocol — keystroke input abstraction
  - `run_tui_app()` — lifecycle manager: mode switching, keystroke routing, screen delivery
- **CodeBreaker minigame** — Mastermind-style TUI game with ANSI-colored UI, arrow key navigation, symbol cycling, win/loss detection. Registered as `codebreaker` shell command.
- **Local terminal raw mode** — `PromptToolkitInput` wires up `LocalRawInput` + alternate screen buffer for TUI apps.
- **WebSocket client raw mode** — Platform-specific raw key reading (Windows `msvcrt` / Unix `tty.setraw`). Client detects mode switches and routes keystrokes.
- **Headless WebSocket client** — `--headless` flag reads/writes JSON on stdin/stdout for automation.
- **57 new tests** — TUI framework (19), CodeBreaker (27), terminal raw mode + WebSocket integration (11). 402 total tests.

### Changed
- `ProgramContext` gains `run_tui` callback for launching TUI apps
- `/ws/terminal` protocol extended with `mode`, `screen`, and `key` message types
- WebSocket client refactored with session-based architecture for mode switching

## Phase 3 — WebSocket Terminal Protocol + CLI Client (2026-03-24)

### Added
- **`InputSource` protocol** — Shell is now transport-agnostic; receives lines from any source (prompt_toolkit, WebSocket, test mock)
- **`QueueOutput`** — Output adapter that pushes messages to an `asyncio.Queue` for WebSocket delivery
- **`TerminalSessionManager`** — Manages Shell instances by UUID, independent of WebSocket connection lifecycle; supports future persistent sessions
- **`/ws/terminal` WebSocket endpoint** — JSON protocol with `input`, `output`, `prompt`, `complete`/`completions`, `exit`, `error` message types
- **WebSocket CLI client** — `python -m recursive_neon.wsclient` connects to the backend over WebSocket with interactive prompt_toolkit REPL
- **Periodic auto-save** — Background task saves game state every 60s while WebSocket sessions are active
- **Tab completion over WebSocket** — `_WebSocketCompleter` (async generator) sends completion requests to server; server returns items + replacement length
- **`ProgramContext.get_line`** — Callback so programs (e.g. `chat`) can read user input through the shell's `InputSource`, enabling sub-REPLs over WebSocket
- **Typing indicator** — Animated spinner ("NPC is typing...") shown while waiting for LLM response in chat
- **28 new tests** — QueueOutput, WebSocketInput, session manager lifecycle, shell start/stop/feed/exit, tab completion (incl. `get_completions_ext`), WebSocket completer unit test, 8 WebSocket integration tests (345 total)

### Changed
- `shell.py` refactored: prompt_toolkit imports are now lazy (only loaded for local CLI); `PromptToolkitInput` class encapsulates all prompt_toolkit logic
- `ShellCompleter` moved inside a factory function (`_make_shell_completer`) to keep prompt_toolkit deferred
- `Shell.run()` accepts an optional `InputSource` parameter (defaults to `PromptToolkitInput`)
- `Shell.get_completions()` method added for transport-agnostic tab completion; `get_completions_ext()` also returns replacement length
- Chat commands now all use `/` prefix for consistency: `/exit`, `/help`, `/relationship`, `/status`
- WebSocket client uses `patch_stdout(raw=True)` to preserve ANSI codes, `complete_while_typing=False` for Tab-only completion

### Fixed
- ANSI color codes rendered as literal text in chat prompt (missing `ANSI()` wrapper for prompt_toolkit)
- ANSI color codes rendered as literal text in WebSocket client output (`patch_stdout` was stripping escape codes)
- Chat sub-REPL hung over WebSocket (was creating local `PromptSession` instead of using shell's `InputSource`)
- Windows console ANSI support enabled via `ENABLE_VIRTUAL_TERMINAL_PROCESSING` for older terminals

## Phase 2 — Deepen Core Features (2026-03-24)

### Added
- **Note CLI** — `note list/show/create/edit/delete` with 1-based index and UUID prefix references
- **Task CLI** — `task lists/list/add/done/undone/delete` with auto-created default list and `--list` flag
- **`grep`** — regex search across virtual filesystem files/directories (`-i` for case-insensitive)
- **`find`** — glob-based filename search (`find [path] -name <pattern>`)
- **`write`** — create or overwrite file content from the command line
- **`save`** — explicitly save game state to disk
- **Persistence** — filesystem, notes, tasks, NPC state, and shell history all persist to `game_data/` as JSON; auto-save on shell exit
- **NPC think-tag stripping** — `<think>...</think>` blocks from qwen3 models are removed before display and storage
- **NPC system prompt refinement** — brevity instruction, stay in character, no meta-commentary
- **Chat slash commands** — `/help`, `/relationship`, `/status` within NPC conversations
- **Integration tests** — end-to-end workflows for notes, tasks, filesystem, persistence round-trips, chat
- **Corrupt save file handling** — graceful recovery (log + skip) instead of crash

### Changed
- `delete_note`, `delete_task_list`, `delete_task` now raise `ValueError` on missing IDs (consistency with other methods)
- Modernized type hints from `typing.Dict`/`List` to built-in `dict`/`list` across all source files
- Test fixtures use `settings.initial_fs_path` instead of hardcoded relative paths
- Removed duplicate `mock_llm` fixture from `test_npc_manager.py`
- DRY persistence: extracted `_save_json`/`_load_json` helpers in `AppService`

### Fixed
- Think-tags were stored in NPC memory before stripping, polluting conversation history
- `note edit` silently ignored unknown flags (now returns error)
- UUID prefix matching could return wrong item on ambiguous prefix (now requires unique match)
- `ChatProgram` created a new `PromptSession` per input line (chat history now works)

## Phase 1 — CLI Shell (2026-03-24)

### Added
- Interactive shell via `python -m recursive_neon.shell` using prompt_toolkit
- Shell architecture: builtins vs. programs separation with restricted `ProgramContext`
- **Builtins**: `cd`, `exit`, `export`
- **Filesystem programs**: `ls` (`-l`, `-a`), `pwd`, `cat`, `mkdir` (`-p`), `touch`, `rm` (`-r`), `cp`, `mv`
- **Utility programs**: `help`, `clear`, `echo` (with `$VAR` expansion), `env`, `whoami`, `hostname`, `date`
- **Chat program**: `chat <npc_id>` with NPC conversation sub-REPL
- Tab completion for command names and virtual filesystem paths (quoting-aware)
- Command history via prompt_toolkit
- `-h`/`--help` flag support for all commands
- ANSI-colored prompt with exit code indicator
- `CapturedOutput` test abstraction for programmatic testing
- 172 unit tests

## Phase 0 — V2 Bootstrap (2026-03-23)

### Added
- Orphan `master` branch with curated files from v1
- V2 handover document with decisions, file inventory, and implementation plan
- Code quality tooling: ruff, mypy, pre-commit hooks, GitHub Actions CI
- Upgraded langchain to 1.x with `langchain_classic` compatibility shim
- Pydantic v1 warning suppression for Python 3.14+
