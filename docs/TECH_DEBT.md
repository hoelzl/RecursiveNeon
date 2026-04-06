# Tech Debt Tracker

Workarounds and temporary fixes that should be revisited when dependencies or circumstances change.
Check this file during dependency upgrades.

---

## TD-001: Suppress pydantic.v1 warning on Python 3.14+

**Added**: 2026-03-24
**Affected files**:
- `backend/src/recursive_neon/__init__.py` — `warnings.filterwarnings` block

**Problem**: `langchain-core` imports `pydantic.v1.fields` at module level
(`langchain_core/_api/deprecation.py:25`), which emits a `UserWarning` on
Python 3.14 because Pydantic V1 compatibility isn't supported on 3.14+.

The filter must live in `recursive_neon/__init__.py` (the package root)
because `python -m recursive_neon.shell` loads the `shell` sub-package
**before** `shell/__main__.py` runs, and the transitive import chain
(`shell → services → npc_manager → langchain_core`) triggers the warning
during that early package load.

**Workaround**: `warnings.filterwarnings("ignore", ...)` in
`recursive_neon/__init__.py`, which is the first module loaded for any
entry point.

**Remove when**: `langchain-core` drops the `pydantic.v1` import, **or**
`pydantic >= 2.13` ships stable (which backports 3.14 support into the V1
shim, silencing the warning). After upgrading, run:

```bash
python -W all -m recursive_neon.shell
```

If no `pydantic.v1` warning appears, delete the `warnings.filterwarnings`
block from `__init__.py` and delete this entry.

**Upstream refs**:
- https://github.com/langchain-ai/langchain/issues/33926
- https://github.com/pydantic/pydantic/issues/12618

**Re-audit 2026-04-06 (Phase 7c-3)**: warning still fires with
`langchain-core==1.2.20`, `pydantic==2.12.5`, Python 3.14.3.
Filter stays. Re-check on next dependency bump.

---

## Resolved

### ~~TD-003: TUI framework has no timer/auto-refresh~~ (resolved 2026-04-06)

- **Location**: `shell/tui/__init__.py`, `shell/tui/runner.py`, `shell/programs/sysmon.py`
- **Summary**: TUI apps were purely keystroke-driven with no periodic callback.
- **Resolution**: Added `tick_interval_ms` and `on_tick(dt_ms)` to `TuiApp` protocol; `RawInputSource.get_key` now accepts `timeout`; `run_tui_app` fires ticks via keystroke-read timeout. `sysmon` sets `tick_interval_ms=1000` and auto-refreshes.

### ~~TD-004: Mark tracking identity enforcement~~ (resolved 2026-04-06)

- **Location**: `editor/buffer.py`
- **Summary**: `Mark.__eq__` uses value equality but tracking needs identity semantics.
- **Resolution**: Added `_MarkSet` wrapper class that uses `id()` internally; `track_mark`/`untrack_mark` now delegate to `_MarkSet.add`/`discard`; debug assertion catches duplicate tracking.

### ~~TD-005: TUI apps ignore real terminal size and don't handle resize~~ (resolved 2026-04-06)

- **Location**: `shell/tui/runner.py`, `shell/shell.py`, `terminal.py`, `wsclient/client.py`, `main.py`
- **Summary**: TUI apps launched into fixed 80×24 and never handled resize.
- **Resolution**: `_measure_terminal()` reads real size via `shutil.get_terminal_size`; `run_tui_app` accepts `resize_source` callback and drains resize events each iteration; local path polls on each keystroke/tick; WS path supports `{"type": "resize"}` messages; wsclient sends resize on connect.

### ~~TD-006: Filesystem name uniqueness + editor save_callback~~ (resolved 2026-04-06)

- **Location**: `services/app_service.py`, `shell/programs/edit.py`
- **Summary**: Filesystem allowed duplicate `(parent_id, name)` pairs; editor `save_callback` used a single shared `file_id` closure corrupting multi-buffer saves.
- **Resolution**: Added `_find_child_by_name` / `_check_name_collision` to `AppService`; all mutating methods (`create_file`, `create_directory`, `update_file` rename, `copy_file`, `move_file`) now raise `FileExistsError` on collision; `copy_file`/`move_file` accept `overwrite=True` flag. Editor: replaced single `file_id` closure with per-buffer `dict[id(buffer), str]` mapping; save resolves existing files by path on first save. 13 xfail regression tests turned green.

### ~~TD-002: Unused LLM/AI dependencies~~ (resolved 2026-03-26)

- **Location**: `backend/pyproject.toml`
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` were listed as core dependencies but unused.
- **Resolution**: Moved to `[project.optional-dependencies] ai-extras`. Install with `pip install -e ".[ai-extras]"` when needed.
