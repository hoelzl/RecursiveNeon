# Changelog

All notable changes to Recursive://Neon are documented here.

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
