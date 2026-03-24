# Tech Debt Tracker

Workarounds and temporary fixes that should be revisited when dependencies or circumstances change.
Check this file during dependency upgrades.

---

## TD-001: Suppress pydantic.v1 warning on Python 3.14+

**Added**: 2026-03-24
**Affected files**:
- `backend/src/recursive_neon/shell/__main__.py` — `warnings.filterwarnings` block
- `backend/src/recursive_neon/main.py` — `warnings.filterwarnings` block
- `backend/pyproject.toml` — `E402` per-file-ignores for both entry points

**Problem**: `langchain-core` imports `pydantic.v1.fields` at module level
(`langchain_core/_api/deprecation.py:25`), which emits a `UserWarning` on
Python 3.14 because Pydantic V1 compatibility isn't supported on 3.14+.

**Workaround**: `warnings.filterwarnings("ignore", ...)` before any langchain
imports in both entry points.

**Remove when**: `langchain-core` drops the `pydantic.v1` import, **or**
`pydantic >= 2.13` ships stable (which backports 3.14 support into the V1
shim, silencing the warning). After upgrading, run:

```bash
python -W all -m recursive_neon.shell
```

If no `pydantic.v1` warning appears, delete the `warnings.filterwarnings`
blocks, remove the `E402` per-file-ignores from `pyproject.toml`, and delete
this entry.

**Upstream refs**:
- https://github.com/langchain-ai/langchain/issues/33926
- https://github.com/pydantic/pydantic/issues/12618
