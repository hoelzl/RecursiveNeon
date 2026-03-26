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

## Resolved

### ~~TD-002: Unused LLM/AI dependencies~~ (resolved 2026-03-26)

- **Location**: `backend/pyproject.toml`
- **Summary**: `langchain-community`, `langgraph`, and `chromadb` were listed as core dependencies but unused.
- **Resolution**: Moved to `[project.optional-dependencies] ai-extras`. Install with `pip install -e ".[ai-extras]"` when needed.
