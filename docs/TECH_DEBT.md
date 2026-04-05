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

## Resolved

### ~~TD-002: Unused LLM/AI dependencies~~ (resolved 2026-03-26)

- **Location**: `backend/pyproject.toml`
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` were listed as core dependencies but unused.
- **Resolution**: Moved to `[project.optional-dependencies] ai-extras`. Install with `pip install -e ".[ai-extras]"` when needed.
