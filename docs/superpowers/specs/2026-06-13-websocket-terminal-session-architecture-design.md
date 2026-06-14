# Work Stream C — WebSocket Terminal & Session Architecture

**Status:** Design approved
**Scope:** Subtasks 5.1–5.6 from `docs/CODEBASE_REVIEW_HANDOVER.md`
**Strategy:** Incremental refactor in handover order, test-first
**Author:** Kimi Code (brainstorming skill)
**Date:** 2026-06-13

---

## 1. Context

The `/ws/terminal` endpoint currently relies on module-level/global state, shared shell sessions, and untyped JSON parsing. This design addresses those issues while preserving the existing local CLI behavior and the legacy `/ws` endpoint.

Key current problems:
- `TerminalSessionManager` is created in `main.py` lifespan and stored in `app.state.terminal_manager`.
- `ConnectionManager` is a module-level singleton in `main.py`.
- Tests mutate `app.state` directly.
- `Shell.__init__` always creates its own `ShellSession`; the terminal manager cannot enforce per-session isolation.
- Incoming WebSocket messages are parsed with ad-hoc `.get()` calls.
- Tab completion reads shell state without locking, racing with command execution.
- `/ws/terminal` has no connection limit.
- `ConnectionManager.broadcast` logs send errors but keeps dead sockets.
- `TerminalSession.mode` is typed as `str`; module-level `logging.basicConfig` runs at import time; lifespan discards exception context; resize does not wake raw-mode input.

---

## 2. Section 1 — Architecture & DI Container

**Goal:** Remove global `TerminalSessionManager` / `ConnectionManager` singletons and `app.state` mutation.

### Changes

1. **Move `ConnectionManager` out of `main.py`.**
   - New file: `backend/src/recursive_neon/connection_manager.py`.
   - Contains `ConnectionManager` and a small `IConnectionManager` protocol.
   - This avoids a circular import between `main.py` and `dependencies.py`.

2. **Add both managers to `ServiceContainer`.**
   - `terminal_manager: TerminalSessionManager`
   - `connection_manager: IConnectionManager`

3. **Build them in `ServiceFactory`.**
   - `create_production_container` constructs:
     - `TerminalSessionManager(container=container, data_dir=...)`
     - `ConnectionManager()`
   - `create_test_container` constructs both with lightweight defaults.
   - Update `ServiceContainer.__repr__` to include the new manager fields by type name only (avoiding recursive repr of the shared container).

4. **Inject via FastAPI `Depends`.**
   - `get_terminal_manager(container: ServiceContainer = Depends(get_container)) -> TerminalSessionManager`
   - `get_connection_manager(container: ServiceContainer = Depends(get_container)) -> IConnectionManager`
   - Update `terminal_websocket` and the legacy `websocket_endpoint` to receive their managers as parameters.

5. **Remove `app.state.terminal_manager` mutation** from `lifespan` and endpoint code.

6. **Update tests** to use `app.dependency_overrides[get_container] = lambda: container` and reset overrides in teardown, instead of touching `app.state`.

### Acceptance Criteria

- No `app.state.terminal_manager` access anywhere.
- No module-level `ws_manager` singleton in `main.py`.
- `pytest` tests for `/ws` and `/ws/terminal` use `dependency_overrides`.

---

## 3. Section 2 — Per-Session `ShellSession` Isolation

**Goal:** Concurrent `/ws/terminal` connections must not share mutable shell state (`cwd`, `env`, `history`), while still sharing the same game-world services.

### Changes

1. **Make `Shell` accept an injected `ShellSession`.**
   - Add `session: ShellSession | None = None` to `Shell.__init__`.
   - If `None`, create one internally (keeps local CLI and existing tests working).

2. **Create per-session `ShellSession` in `TerminalSessionManager.create_session`.**
   - `session = ShellSession(container, username="user", hostname="neon-proxy")`
   - Pass it into `Shell(container=container, session=session, data_dir=...)`.

3. **Keep `ServiceContainer` shared.**
   - All sessions use the same `app_service`, `npc_manager`, `event_bus`, etc.
   - Concurrent mutations to shared services are serialized by the `AppService._save_lock` added in Work Stream 2.2.

4. **Local CLI unchanged.**
   - `Shell()` without a session continues to create its own `ShellSession`.

### Tests

- `test_two_terminal_sessions_have_independent_cwd`
- `test_two_terminal_sessions_have_independent_env`
- `test_concurrent_file_creation_is_safe`
- Update `test_terminal.py` fixtures to no longer rely on a single global shell state.

### Acceptance Criteria

- Two browser tabs can `cd` independently without affecting each other.
- Shared game state mutations remain consistent.

---

## 4. Section 3 — Typed WebSocket Message Models & Protocol Alignment

**Goal:** Validate every incoming `/ws/terminal` message and keep backend/frontend protocol definitions in sync.

### Changes

1. **Create `backend/src/recursive_neon/models/ws_messages.py`.**
   - Pydantic models:
     - `InputMessage` (`type="input"`, `line: str`)
     - `KeyMessage` (`type="key"`, `key: str`)
     - `ResizeMessage` (`type="resize"`, `width: int`, `height: int`)
     - `CompleteMessage` (`type="complete"`, `line: str`)
   - Discriminated union `ClientMessage = InputMessage | KeyMessage | ResizeMessage | CompleteMessage`.
   - Helper `parse_client_message(data)` returns a typed message or raises `ValueError`.

2. **Validate in `_ws_reader`.**
   - Replace manual `.get()` parsing with `msg = parse_client_message(await websocket.receive_json())`.
   - Dispatch on `msg.type` using Python 3.11 `match`/`case` for exhaustiveness checking.
   - Unknown types return a typed `ErrorMessage`.

3. **Add server → client message models.**
   - `OutputMessage`, `PromptMessage`, `CompletionsMessage`, `ModeMessage`, `ScreenMessage`, `ExitMessage`, `ErrorMessage`.
   - Outgoing messages can still be sent as `dict`, but the models are the source of truth.

4. **Frontend alignment.**
   - Update `frontend/src/terminal/protocol.ts` only if field names diverge.
   - Ensure `ScreenMessage` fields (`lines`, `cursor`, `cursor_visible`) match exactly.

5. **Docstrings.**
   - Update `terminal_websocket` docstring to mention the `replace` field in `completions`.

### Tests

- `test_terminal_rejects_malformed_message`
- `test_terminal_resize_message_validated`
- `test_terminal_unknown_message_returns_typed_error`
- Unit tests for `parse_client_message` covering all types and invalid payloads.

### Acceptance Criteria

- Malformed client messages return a typed error, not a `500`.
- Backend and frontend protocol definitions match exactly.

---

## 5. Section 4 — Completion Locking

**Goal:** Eliminate the race between tab-completion requests and concurrent command execution.

### Changes

1. **Add an `asyncio.Lock` to `Shell`.**
   - `self._state_lock = asyncio.Lock()` in `Shell.__init__`.

2. **Protect completion reads.**
   - Add async method `Shell.get_completions_ext_async(line: str) -> tuple[list[str], int]` that acquires `self._state_lock` and delegates to the synchronous `get_completions_ext`.
   - Keep the synchronous version for prompt_toolkit and direct callers that already run on the shell task.

3. **Use the async version in `_ws_reader`.**
   - Replace `session.shell.get_completions_ext(line)` with `await session.shell.get_completions_ext_async(line)`.

4. **Protect command execution.**
   - `Shell.execute_line` acquires `self._state_lock` around parse/expand/execute.
   - Because `execute_line` runs in the shell task and `get_completions_ext_async` runs in the WS reader task, the lock guarantees mutual exclusion.

### Tests

- `test_completion_does_not_race_with_command_execution`
- Update `test_tab_completion_request` in `test_terminal.py` to use the async path.

### Acceptance Criteria

- Completions are computed against a consistent shell state.
- No dictionary-size-during-iteration or similar races.

---

## 6. Section 5 — Connection Limits & Cleanup

**Goal:** Prevent resource exhaustion and remove dead WebSocket connections.

### Changes

1. **Apply `MAX_CONNECTIONS` to `/ws/terminal`.**
   - Add `max_connections: int = 50` to `TerminalSessionManager`.
   - In `terminal_websocket`, reject if `terminal_manager.active_count >= terminal_manager.max_connections`.
   - Close with code `1013` ("Server overloaded") and return.

2. **Remove dead connections on broadcast failure.**
   - In `ConnectionManager.broadcast`, on `Exception`, call `self.disconnect(connection)` in addition to logging.

3. **Improve terminal session cleanup.**
   - In `TerminalSession.stop`:
     - Put `None` into both `input_queue` and `key_queue`.
     - Cancel `_shell_task` if it does not finish within the graceful timeout.
     - Drain any remaining items from `output_queue`.
   - In `TerminalSessionManager.remove_session`:
     - Ensure `_auto_save_task` is cancelled when no sessions remain.

4. **Legacy `/ws` cleanup.**
   - `websocket_endpoint` benefits from the improved `ConnectionManager.broadcast` cleanup.

### Tests

- `test_terminal_rejects_connection_over_limit`
- `test_broadcast_removes_dead_connection`
- `test_terminal_disconnect_cleans_up_tasks`
- Update connection-manager tests to assert dead-socket removal.

### Acceptance Criteria

- Connection count is bounded.
- Failed sockets are removed from active sets.
- Disconnecting a terminal session does not leak tasks or queues.

---

## 7. Section 6 — Internal Cleanup & Typing

**Goal:** Fix the smaller terminal/main.py issues listed in 5.6.

### Changes

1. **Type `TerminalSession.mode` as `Literal["cooked", "raw"]`.**

2. **Guard module-level `logging.basicConfig` in `main.py`.**
   - Keep the call at module level but guard it with `if not logging.getLogger().handlers:` so importing `main.py` in tests does not reconfigure logging.

3. **Preserve exception context in lifespan.**
   - Use `raise RuntimeError(f"Startup error: {exc}") from exc` instead of bare `raise`.

4. **Type `_ws_reader` / `_ws_writer` parameters.**
   - Change `session` parameter type from `Any` to `TerminalSession`.

5. **Wake raw-mode input on resize.**
   - Add an `asyncio.Event` to `WebSocketRawInput`.
   - `TerminalSession.feed_resize` sets the event when in raw mode.
   - `WebSocketRawInput.get_key` wakes when the event is set and returns `None`, causing the TUI runner loop to re-check `resize_source` immediately.

### Tests

- `mypy` must pass on `terminal.py` and `main.py`.
- Resize wake test: feed a resize while a TUI app is waiting for a key and verify `on_resize` is called without an extra keystroke.

### Acceptance Criteria

- `mypy` passes on `terminal.py` and `main.py`.
- Resize events reach TUI apps without waiting for the next keystroke.

---

## 8. Section 7 — Testing Strategy

### Test Layers

1. **Unit tests for `models/ws_messages.py`.**
   - Valid/invalid message parsing.
   - Exhaustiveness of `ClientMessage` union.

2. **Unit tests for `TerminalSessionManager` / `TerminalSession`.**
   - DI wiring, per-session isolation, connection limits, cleanup.

3. **WebSocket integration tests in `test_terminal.py`.**
   - Full `/ws/terminal` flow with typed messages.
   - Malformed message handling.
   - Concurrent sessions.

4. **Tests for `ConnectionManager`.**
   - Dead-connection removal on broadcast failure.

5. **Type-check coverage.**
   - Run `mypy` on `main.py`, `terminal.py`, `shell/shell.py`, `shell/session.py`, `models/ws_messages.py`.

### Fixtures

- Use `dependency_overrides[get_container] = lambda: container` in `test_main.py` and `test_terminal.py`.
- Reset overrides and call `reset_container()` in teardown.
- Add `mock_terminal_manager` fixture if needed for unit tests.

### Quality Gates

- `ruff check .`
- `ruff format --check .`
- `mypy`
- `pytest -q`

---

## 9. Implementation Order

Incremental, test-first:

1. **5.1** — Move terminal manager & connection manager into DI.
2. **5.2** — Per-session `ShellSession` isolation.
3. **5.3** — Typed WS message models & protocol alignment.
4. **5.4** — Shell state lock for completions.
5. **5.5** — Connection limits & cleanup.
6. **5.6** — Internal cleanup & typing.

Each subtask gets its own failing tests before implementation.

---

## 10. Affected Files

### Backend source
- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/terminal.py`
- `backend/src/recursive_neon/dependencies.py`
- `backend/src/recursive_neon/connection_manager.py` (new)
- `backend/src/recursive_neon/models/ws_messages.py` (new)
- `backend/src/recursive_neon/shell/shell.py`
- `backend/src/recursive_neon/shell/session.py`

### Frontend source
- `frontend/src/terminal/protocol.ts` (alignment only if needed)

### Tests
- `backend/tests/unit/test_terminal.py`
- `backend/tests/unit/test_main.py`
- `backend/tests/unit/shell/test_shell_integration.py` (if shell constructor changes affect it)
- `backend/tests/unit/models/test_ws_messages.py` (new)
- `backend/tests/conftest.py`

---

## 11. Final Acceptance Criteria

- No `app.state.terminal_manager` access.
- `TerminalSessionManager` and `ConnectionManager` are injectable via `ServiceContainer`.
- Each `/ws/terminal` connection gets its own `ShellSession`.
- Two concurrent sessions have independent `cwd`/`env`/`history`.
- Incoming `/ws/terminal` messages are validated Pydantic models.
- Malformed messages return a typed error.
- Completions are computed under a shell state lock.
- `/ws/terminal` enforces a connection limit.
- `ConnectionManager.broadcast` removes dead sockets.
- Terminal disconnect cleans up tasks, queues, and auto-save.
- `mypy` passes on `main.py`, `terminal.py`, `shell/shell.py`, `shell/session.py`, and `models/ws_messages.py`.
- Resize wakes raw-mode input.
- Full test suite passes.
