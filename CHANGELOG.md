# Changelog

All notable changes to Recursive://Neon are documented here.

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
