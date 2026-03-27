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

## Resolved

### ~~TD-002: Unused LLM/AI dependencies~~ (resolved 2026-03-26)

- **Location**: `backend/pyproject.toml`
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` were listed as core dependencies but unused.
- **Resolution**: Moved to `[project.optional-dependencies] ai-extras`. Install with `pip install -e ".[ai-extras]"` when needed.
