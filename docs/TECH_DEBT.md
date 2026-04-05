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

---

## TD-003: TUI framework has no timer/auto-refresh mechanism

**Added**: 2026-03-27
**Affected files**:
- `backend/src/recursive_neon/shell/tui/__init__.py` — `TuiApp` protocol
- `backend/src/recursive_neon/shell/tui/runner.py` — `run_tui_app()` loop

**Problem**: The TUI framework is purely keystroke-driven — `on_key()` is
only called when the user presses a key. There is no periodic callback, so
apps like `sysmon` can only refresh their display in response to input.

**Enhancement needed**: Add an optional `on_tick()` method to the `TuiApp`
protocol (or a `tick_interval` attribute) so `run_tui_app()` can use a
timeout on the keystroke read and call `on_tick()` periodically. This would
let sysmon show live-updating stats, and future apps (e.g., a network
monitor or countdown timer) could animate without requiring keypresses.

**Implement when**: A TUI app needs live updates without user interaction
(sysmon auto-refresh, animated displays, timed game events).

---

## TD-004: Mark tracking uses identity but Mark.__eq__ uses value equality

**Added**: 2026-04-04
**Affected files**:
- `backend/src/recursive_neon/editor/buffer.py` — `track_mark()`, `untrack_mark()`
- `backend/src/recursive_neon/editor/mark.py` — `Mark.__eq__`

**Problem**: `Mark.__eq__` compares by position `(line, col)`, not identity.
`Buffer.track_mark()` was fixed in Phase 6i to use identity (`any(t is m ...)`)
instead of equality (`m not in ...`), but any future code that uses `in` or
`==` to check for a specific Mark object in `_tracked_marks` will match the
*wrong* mark if another mark happens to be at the same position. This is
particularly relevant with the window system, where multiple windows can have
independent tracked marks at the same buffer position.

`untrack_mark()` already uses identity (`is not`), which is correct.

**Risk**: Low (the fix is in place), but the mismatch between `__eq__`
semantics and tracking semantics is a latent footgun for future code.

**Options**:
1. Add a `Mark.__eq__` override that uses identity — but this breaks
   legitimate value comparisons (e.g., `assert point == Mark(1, 0)`).
2. Use a dedicated `MarkSet` that wraps identity-based membership — cleaner
   but more indirection.
3. Keep the current approach (identity checks in track/untrack) and document
   the invariant. This is what Emacs does internally.

**Current decision**: Option 3. The `track_mark`/`untrack_mark` methods are
the only place that needs identity semantics, and they already use it.

---

## TD-005: TUI apps ignore real terminal size and don't handle resize

**Added**: 2026-04-05
**Affected files**:
- `backend/src/recursive_neon/shell/tui/runner.py` — `run_tui_app()` defaults to 80×24
- `backend/src/recursive_neon/shell/shell.py` — `_make_run_tui` calls `run_tui_app` without width/height
- `backend/src/recursive_neon/terminal.py` — WebSocket path same
- `backend/src/recursive_neon/shell/keys.py` — local raw input has no resize signal hook
- `backend/src/recursive_neon/wsclient/client.py` — WS client sends no resize messages

**Problem**: When any TUI app (neon-edit, sysmon, codebreaker) launches in
a large terminal window, it renders into a fixed 80×24 `ScreenBuffer` in
the top-left corner instead of filling the terminal. `run_tui_app()`'s
`width` and `height` parameters default to `80, 24` (see `runner.py:28-29`)
and every caller omits them. Additionally, resizing the terminal while an
app is running does not trigger a re-layout — the `TuiApp.on_resize` hook
exists on the protocol but is never invoked by the runner.

The editor already implements `EditorView.on_resize(width, height)`
correctly (`editor/view.py:102`), as do `sysmon` and `codebreaker`. The
bug is entirely in the framework glue: nobody measures the terminal or
listens for resize events.

**Fix sketch** (scheduled for Phase 7c-4):
1. Measure the real terminal size at TUI entry via
   `shutil.get_terminal_size(fallback=(80, 24))` and pass it to
   `run_tui_app`. Both the local shell path (`shell.py` `_make_run_tui`)
   and the WebSocket path (`terminal.py`) must be updated.
2. Add a resize event channel:
   - **Local (POSIX)**: install a `SIGWINCH` handler that enqueues a
     resize sentinel into the raw-input key stream or a dedicated
     resize queue read by `run_tui_app`.
   - **Local (Windows)**: `signal.SIGWINCH` does not exist. Poll
     `shutil.get_terminal_size()` on a short interval (reuse the
     `on_tick` infrastructure from 7c-1 once it lands) and dispatch
     `on_resize` when the dimensions change.
   - **WebSocket**: extend the WS protocol with a `{"type": "resize",
     "width": N, "height": M}` message. The browser terminal and the
     `wsclient` both send it on connect and whenever the host terminal
     resizes. `TerminalSessionManager` forwards it to the running TUI.
3. `run_tui_app` drains the resize channel on each iteration and calls
   `app.on_resize(new_w, new_h)` before the next keystroke, delivering
   the fresh screen via `_deliver_screen`.
4. `ScreenBuffer.create` default stays 80×24 for tests that don't care,
   but real callers always pass measured dimensions.

**Fallback on detection failure**: if `get_terminal_size()` returns the
`fallback=(80, 24)` tuple because stdout is not a TTY, keep 80×24 — this
is the correct behaviour for piped / redirected output.

**Risk**: High user-visible impact (every TUI launch looks wrong in a
modern terminal), low implementation risk (the protocol hooks already
exist and the editor already calls `on_resize` correctly).

---

## TD-006: Virtual filesystem allows duplicate names + editor save_callback corrupts multi-buffer sessions

**Added**: 2026-04-05 (user bug report during Phase 6l-2)
**Affected files**:
- `backend/src/recursive_neon/services/app_service.py` — `create_file`, `create_directory`, `update_file` (rename path), `copy_file`, `move_file` do not check for name collisions in the target parent
- `backend/src/recursive_neon/shell/programs/edit.py` — `save_callback` closes over a single shared `file_id` for the whole editor session instead of tracking per buffer

**Problem**: A user reported seeing two files with the same name in the
same directory after opening one file, splitting the window with `C-x 2`,
opening a different file in the second window, then editing and saving
both buffers. Investigation identified **two independent root causes**
that together produce the observed corruption:

**Bug 1 — Filesystem allows duplicate `(parent_id, name)` pairs**.
`AppService.create_file` (`app_service.py:332-355`) and
`create_directory` (`:314-330`) call `_validate_node_name` to reject
path-separator / reserved names but never check whether a sibling with
the same name already exists in the parent. `update_file`'s rename
path (`:357-382`), `copy_file` (`:413-440`) and `move_file`
(`:442-479`) have the same gap. Because `resolve_path` returns the
first child match (`path_resolver.py:69-74`), any later duplicate
becomes invisible to most commands — but it is still persisted, still
counted by `ls`, and still returned by `list_directory`.

**Bug 2 — Editor `save_callback` uses a single shared `file_id` closure**.
`shell/programs/edit.py:47-103` declares one `file_id: str | None =
None` captured via `nonlocal` inside `save_callback`. Only the
initial `edit <path>` argument sets it (`:62`). Buffers opened later
via `find-file` (C-x C-f) never update this closure — `open_callback`
just returns content. When the user saves a buffer that was opened
via `find-file`:

- If `file_id is None` (editor launched without an initial file), the
  save path falls into the `else` branch and calls `create_file` with
  the buffer's filepath. The existing file at that path is **not**
  updated — a duplicate node is created (relying on bug 1 to succeed).
- If `file_id is not None` (editor launched with an existing file),
  every subsequent save — regardless of which buffer is current —
  calls `update_file(file_id, …)`, silently writing the active
  buffer's content into the file that happened to be opened first.

Both bugs are reachable in normal editing workflows. Fixing either
alone is insufficient: bug 1 allows duplicates even when the editor is
not involved (e.g., `touch foo; touch foo` via shell), and bug 2
produces silent data corruption even when bug 1 is fixed (the save
goes to the wrong node instead of creating a duplicate).

**Regression tests** (currently `@pytest.mark.xfail(strict=True)`):
- `backend/tests/unit/test_filesystem_name_uniqueness.py` — 13 tests
  covering `create_file` / `create_directory` / `update_file` rename /
  `copy_file` / `move_file` / path-resolution invariants.
- `backend/tests/unit/shell/test_edit_save_callback.py` — 4 tests
  covering the four concrete multi-buffer save paths, including the
  exact user-reported scenario.

The xfail markers document the expected behaviour; the fix PR should
remove them.

**Fix plan** (to be scheduled inside Phase 7 — before any further
editor polish touches the save path):

1. **Filesystem layer** (`app_service.py`):
   - Add a private `_find_child_by_name(parent_id, name)` helper that
     uses `_children_index` for O(1) lookup.
   - `create_file` and `create_directory` raise `ValueError` (or a new
     `FileExistsError`) if `_find_child_by_name` returns a node.
   - `update_file` raises on rename collisions. A rename to the same
     name is a no-op and must continue to succeed.
   - `copy_file` and `move_file` raise on target collisions. Callers
     that want overwrite semantics (e.g., `cp -f`, `mv -f`) pass an
     explicit `overwrite=True` flag.
   - Update `tests/unit/test_app_service.py` tests that currently rely
     on silent duplicate creation (none as of 2026-04-05, but grep
     during the fix).

2. **Editor layer** (`edit.py`):
   - Replace the single `file_id` closure with a `dict[int, str]`
     keyed by `id(buffer)` (or `buffer.name`, if unique is maintained)
     that maps buffer identity to the corresponding filesystem node
     ID. The dict is captured via closure.
   - `open_callback` should register `buf → file_id` as soon as it
     loads existing file content, so `find-file` sees a properly
     tracked buffer.
   - `save_callback` looks up the buffer in the dict; if present,
     calls `update_file`; if absent, calls `create_file` and registers
     the new `file_id`. Write-file to a new path removes the old
     mapping and creates a new one.
   - On `remove_buffer`, drop the mapping.
   - Add a `sync-with-filesystem` path for the case where the user
     saves a buffer whose filepath has changed since open (e.g., via
     C-x C-w write-file). The mapping must follow the buffer, not the
     old filepath.

3. **Test file cleanup**: remove the `@pytest.mark.xfail` markers
   from both regression test files. The tests should pass without
   further changes.

**Risk**: Medium-high. Bug 2 is silent data corruption — users can
lose edits. Bug 1 creates invariant violations that could compound in
future features (the attributed-text model in 7a-2, syntax
highlighting in 7d-2, game-state sync in 7e all assume unique paths).

---

## Resolved

### ~~TD-002: Unused LLM/AI dependencies~~ (resolved 2026-03-26)

- **Location**: `backend/pyproject.toml`
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` were listed as core dependencies but unused.
- **Resolution**: Moved to `[project.optional-dependencies] ai-extras`. Install with `pip install -e ".[ai-extras]"` when needed.
