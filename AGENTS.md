# AGENTS.md — Guidance for AI Agents

This file helps AI agents (Claude Code, Copilot, etc.) work effectively on this codebase.

## Project Context

Recursive://Neon is a CLI-first RPG where the player interacts via a terminal shell. The game simulates SSHing into a remote system. Phases 0-3 are complete (CLI shell with filesystem, notes, tasks, NPC chat, persistence, WebSocket terminal protocol). Phase 4 (TUI apps / raw mode) is not started.

## Architecture at a Glance

```
Shell programs (ProgramContext) ──→ Services (AppService, NPCManager) ──→ Models (GameState)
     ↑                                         ↑
Shell builtins (ShellSession) ──────→ ServiceContainer (DI)
```

- **Programs** get a restricted `ProgramContext` (args, stdout, services, cwd_id). They cannot modify shell state.
- **Builtins** get the full `ShellSession` and can modify cwd, env vars, etc.
- **Services** are accessed via `ServiceContainer` (dependency injection). Never instantiate directly.
- **Models** are Pydantic BaseModel instances. The virtual filesystem uses UUID-based `FileNode` objects.

## How to Add a New Shell Command

1. Create `async def prog_mycommand(ctx: ProgramContext) -> int` in an appropriate file under `shell/programs/`
2. Use `ctx.services.app_service` (or other services) for business logic
3. Write to `ctx.stdout` / `ctx.stderr` for output
4. Return 0 for success, nonzero for error
5. Register via `registry.register_fn("mycommand", prog_mycommand, "Help text")` in a `register_*` function
6. Call the registration function from `Shell.__init__` in `shell.py`
7. Write tests using the `make_ctx` fixture from `tests/unit/shell/conftest.py`

## How to Add a New Service

1. Define interface in `services/interfaces.py` (abstract class)
2. Implement in `services/my_service.py`
3. Add field to `ServiceContainer` dataclass in `dependencies.py`
4. Wire in `ServiceFactory.create_production_container()`
5. Add mock support in `ServiceFactory.create_test_container()`

## Key Patterns

- **Type hints**: use built-in `list[...]`, `dict[...]` (Python 3.14, no `typing.List`/`Dict`)
- **Async**: all I/O-bound operations are async. Use `asyncio.to_thread()` for blocking calls.
- **Testing**: pytest with auto-mode asyncio. Tests grouped in classes. Shell programs tested via `CapturedOutput`.
- **Persistence**: JSON files in `game_data/`. Use `_save_json`/`_load_json` helpers. Always handle corrupt files gracefully.
- **Virtual filesystem**: all paths resolve through `path_resolver.py` to UUID-based `FileNode` objects. Never use real file paths in game logic.

## Critical Rules

1. **Virtual filesystem isolation is sacred** — see `backend/FILESYSTEM_SECURITY.md`
2. **Use dependency injection** — never instantiate services directly
3. **Write tests** — every new feature needs tests
4. **Don't add features beyond what's tested** — V1's failure was breadth without depth

## Running Checks

```bash
cd backend
../.venv/Scripts/pytest              # All 345 tests
../.venv/Scripts/ruff check .        # Lint
../.venv/Scripts/mypy                # Type check
```

All three must pass before committing.

## Key Files

| Purpose | Path |
|---------|------|
| Shell entry point | `backend/src/recursive_neon/shell/__main__.py` |
| Shell REPL + dispatch | `backend/src/recursive_neon/shell/shell.py` |
| WS terminal sessions | `backend/src/recursive_neon/terminal.py` |
| WS client entry point | `backend/src/recursive_neon/wsclient/__main__.py` |
| Program registry | `backend/src/recursive_neon/shell/programs/__init__.py` |
| DI container | `backend/src/recursive_neon/dependencies.py` |
| Config | `backend/src/recursive_neon/config.py` |
| App service | `backend/src/recursive_neon/services/app_service.py` |
| NPC manager | `backend/src/recursive_neon/services/npc_manager.py` |
| Models | `backend/src/recursive_neon/models/` |
| Test fixtures | `backend/tests/conftest.py`, `backend/tests/unit/shell/conftest.py` |

## WebSocket Terminal Protocol (Phase 3)

The shell runs over WebSocket via `/ws/terminal`. Key concepts:
- **`InputSource` protocol** in `shell.py` — abstracts where command lines come from (prompt_toolkit, WebSocket queue, test mock)
- **`QueueOutput`** in `output.py` — pushes output to an `asyncio.Queue` for the WS handler to drain
- **`TerminalSessionManager`** in `terminal.py` — owns Shell instances by UUID, decoupled from WS connection lifecycle
- **Message protocol**: `input`, `output`, `prompt`, `complete`/`completions`, `exit`, `error` (all JSON)
- **WebSocket CLI client**: `python -m recursive_neon.wsclient` for interactive sessions

## What's Next (Phase 4)

Phase 4 is TUI apps with raw mode. Key decisions ahead:
- Raw mode protocol design (server tells client to switch modes; client sends keystrokes)
- TUI framework: screen buffer, cursor management, input handling
- Minigames, file browser, etc. (scope TBD)
- Testable via both local CLI and WebSocket client

See `docs/V2_HANDOVER.md` Section 6 (Phase 4) for the full plan.
