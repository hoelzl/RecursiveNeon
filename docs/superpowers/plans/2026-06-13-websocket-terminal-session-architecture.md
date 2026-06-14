# Work Stream C — WebSocket Terminal & Session Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove global state from the WebSocket terminal layer, isolate per-session shell state, validate the terminal protocol, and harden connection/cleanup behavior.

**Architecture:** Move `TerminalSessionManager` and `ConnectionManager` into `ServiceContainer`, inject them via FastAPI `Depends`, create per-session `ShellSession` instances, add Pydantic message models for `/ws/terminal`, protect completion reads with an `asyncio.Lock`, enforce connection limits, and clean up tasks/queues on disconnect.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest-asyncio, asyncio.

---

## File Structure

### New files
- `backend/src/recursive_neon/connection_manager.py` — `ConnectionManager` implementation.
- `backend/src/recursive_neon/models/ws_messages.py` — Pydantic models for the `/ws/terminal` protocol.
- `backend/tests/unit/models/test_ws_messages.py` — Unit tests for message parsing.
- `backend/tests/unit/test_connection_manager.py` — Unit tests for connection-manager cleanup.

### Modified files
- `backend/src/recursive_neon/services/interfaces.py` — Add `IConnectionManager` protocol.
- `backend/src/recursive_neon/dependencies.py` — Add managers to `ServiceContainer` and factories.
- `backend/src/recursive_neon/main.py` — Inject managers; remove `app.state` and module-level `ws_manager`; guard logging; preserve exception context.
- `backend/src/recursive_neon/terminal.py` — Per-session `ShellSession`; typed `mode`; connection limits; cleanup; resize wake.
- `backend/src/recursive_neon/shell/shell.py` — Accept injected `ShellSession`; add state lock and async completion method.
- `backend/src/recursive_neon/shell/session.py` — No functional changes expected, but may need type tweaks.
- `backend/tests/conftest.py` — Add `terminal_manager` fixture if useful.
- `backend/tests/unit/test_main.py` — Use `dependency_overrides`.
- `backend/tests/unit/test_terminal.py` — Use `dependency_overrides`; add per-session and cleanup tests.
- `frontend/src/terminal/protocol.ts` — Align if any field names diverge.

---

## Task 1: Define the connection-manager interface

**Files:**
- Modify: `backend/src/recursive_neon/services/interfaces.py`
- Test: `backend/tests/unit/test_connection_manager.py` (will fail until Task 2)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_connection_manager.py`:

```python
"""Tests for the WebSocket connection manager."""

from unittest.mock import AsyncMock

import pytest

from recursive_neon.connection_manager import ConnectionManager
from recursive_neon.services.interfaces import IConnectionManager


class TestConnectionManager:
    async def test_broadcast_removes_dead_connection(self):
        """A socket that fails during broadcast is removed."""
        mgr = ConnectionManager()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = Exception("disconnected")

        await mgr.connect(good_ws)
        await mgr.connect(bad_ws)
        assert mgr.active_count == 2

        await mgr.broadcast({"type": "test"})

        good_ws.send_json.assert_called_once_with({"type": "test"})
        assert mgr.active_count == 1
        assert bad_ws not in mgr.active_connections
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_connection_manager.py::TestConnectionManager::test_broadcast_removes_dead_connection -v
```

Expected: `ModuleNotFoundError: No module named 'recursive_neon.connection_manager'` or similar.

- [ ] **Step 3: Add `IConnectionManager` to interfaces**

Append to `backend/src/recursive_neon/services/interfaces.py`:

```python
class IConnectionManager(Protocol):
    """Protocol for the generic WebSocket connection manager."""

    async def connect(self, websocket: Any) -> bool: ...
    def disconnect(self, websocket: Any) -> None: ...
    async def send_personal(self, message: dict, websocket: Any) -> None: ...
    async def broadcast(self, message: dict) -> None: ...
```

- [ ] **Step 4: Run the test again**

Same command as Step 2.

Expected: `ModuleNotFoundError: No module named 'recursive_neon.connection_manager'`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/recursive_neon/services/interfaces.py backend/tests/unit/test_connection_manager.py
git commit -m "feat(ws): define IConnectionManager protocol and failing cleanup test"
```

---

## Task 2: Move `ConnectionManager` out of `main.py`

**Files:**
- Create: `backend/src/recursive_neon/connection_manager.py`
- Modify: `backend/src/recursive_neon/main.py`
- Test: `backend/tests/unit/test_connection_manager.py`

- [ ] **Step 1: Create `ConnectionManager` implementation**

Create `backend/src/recursive_neon/connection_manager.py`:

```python
"""Generic WebSocket connection manager."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    MAX_CONNECTIONS = 50

    def __init__(self):
        self.active_connections: set[Any] = set()

    @property
    def active_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: Any) -> bool:
        """Accept a WebSocket connection. Returns False if limit reached."""
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Server overloaded")
            logger.warning(
                "Connection rejected: limit reached (%d)", self.MAX_CONNECTIONS
            )
            return False
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("Client connected. Total: %d", len(self.active_connections))
        return True

    def disconnect(self, websocket: Any):
        self.active_connections.discard(websocket)
        logger.info("Client disconnected. Total: %d", len(self.active_connections))

    async def send_personal(self, message: dict, websocket: Any):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Error broadcasting to client: %s", e)
                self.disconnect(connection)
```

- [ ] **Step 2: Update `main.py` to import from new location**

In `backend/src/recursive_neon/main.py`:

```python
from recursive_neon.connection_manager import ConnectionManager
```

Remove the old inline `ConnectionManager` class and module-level `ws_manager = ConnectionManager()`.

- [ ] **Step 2b: Update existing `TestConnectionManager` import**

In `backend/tests/unit/test_main.py`, change:

```python
from recursive_neon.main import ConnectionManager
```

to:

```python
from recursive_neon.connection_manager import ConnectionManager
```

- [ ] **Step 3: Run the test**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_connection_manager.py::TestConnectionManager::test_broadcast_removes_dead_connection -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/src/recursive_neon/connection_manager.py backend/src/recursive_neon/main.py
git commit -m "refactor(ws): move ConnectionManager to its own module"
```

---

## Task 3: Add managers to `ServiceContainer`

**Files:**
- Modify: `backend/src/recursive_neon/dependencies.py`
- Modify: `backend/src/recursive_neon/services/interfaces.py` (already has `IConnectionManager`)
- Test: `backend/tests/unit/test_dependencies.py` (if it exists) or add an assertion in `test_main.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_main.py` or create `backend/tests/unit/test_dependencies.py`:

```python
from recursive_neon.dependencies import ServiceFactory


def test_test_container_has_terminal_and_connection_managers():
    container = ServiceFactory.create_test_container()
    assert container.terminal_manager is not None
    assert container.connection_manager is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_main.py::test_test_container_has_terminal_and_connection_managers -v
```

Expected: `AttributeError: 'ServiceContainer' object has no attribute 'terminal_manager'`.

- [ ] **Step 3: Add fields to `ServiceContainer`**

In `backend/src/recursive_neon/dependencies.py`:

- Add `IConnectionManager` to the existing `recursive_neon.services.interfaces` import.
- Import `ConnectionManager` and `TerminalSessionManager` locally inside the factory methods to avoid a circular import (`terminal.py` already imports `ServiceContainer`).

```python
from recursive_neon.services.interfaces import (
    IAppService,
    IConnectionManager,
    IGameEventBus,
    INPCManager,
    IOllamaClient,
    IProcessManager,
    LLMInterface,
)

@dataclass
class ServiceContainer:
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    system_state: SystemState
    game_state: GameState
    app_service: IAppService
    terminal_manager: TerminalSessionManager
    connection_manager: IConnectionManager
    start_time: datetime
    process_table: ProcessTable = field(default_factory=ProcessTable)
    event_bus: IGameEventBus = field(default_factory=GameEventBus)

    def __repr__(self) -> str:
        return (
            f"ServiceContainer("
            f"process_manager={type(self.process_manager).__name__}, "
            f"ollama_client={type(self.ollama_client).__name__}, "
            f"npc_manager={type(self.npc_manager).__name__}, "
            f"system_state={type(self.system_state).__name__}, "
            f"game_state={type(self.game_state).__name__}, "
            f"app_service={type(self.app_service).__name__}, "
            f"terminal_manager={type(self.terminal_manager).__name__}, "
            f"connection_manager={type(self.connection_manager).__name__}, "
            f"event_bus={type(self.event_bus).__name__}, "
            f"process_table={type(self.process_table).__name__}, "
            f"start_time={self.start_time.isoformat()})"
        )
```

- [ ] **Step 4: Build managers in factories**

In `ServiceFactory.create_production_container`:

```python
        import dataclasses

        from recursive_neon.connection_manager import ConnectionManager
        from recursive_neon.terminal import TerminalSessionManager

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            terminal_manager=None,  # type: ignore[arg-type]
            connection_manager=ConnectionManager(),
            start_time=start_time,
            process_table=ProcessTable.with_defaults(),
        )

        terminal_manager = TerminalSessionManager(
            container=container,
            data_dir=data_dir,
        )
        container = dataclasses.replace(container, terminal_manager=terminal_manager)
        terminal_manager._container = container
```

In `ServiceFactory.create_test_container`:

```python
        import dataclasses

        from recursive_neon.connection_manager import ConnectionManager
        from recursive_neon.terminal import TerminalSessionManager

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            terminal_manager=None,  # type: ignore[arg-type]
            connection_manager=ConnectionManager(),
            start_time=start_time,
        )

        terminal_manager = TerminalSessionManager(container=container)
        container = dataclasses.replace(container, terminal_manager=terminal_manager)
        terminal_manager._container = container
```

- [ ] **Step 5: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/recursive_neon/dependencies.py backend/tests/unit/test_main.py
git commit -m "feat(di): add terminal and connection managers to ServiceContainer"
```

---

## Task 4: Inject managers into endpoints

**Files:**
- Modify: `backend/src/recursive_neon/main.py`
- Test: `backend/tests/unit/test_main.py`, `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Add dependency getters in `main.py`**

```python
async def get_terminal_manager(
    container: ServiceContainer = Depends(get_container),
) -> TerminalSessionManager:
    return container.terminal_manager


async def get_connection_manager(
    container: ServiceContainer = Depends(get_container),
) -> IConnectionManager:
    return container.connection_manager
```

- [ ] **Step 2: Update `terminal_websocket` signature**

```python
@app.websocket("/ws/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    terminal_manager: TerminalSessionManager = Depends(get_terminal_manager),
):
```

Remove `manager: TerminalSessionManager = app.state.terminal_manager` and use `terminal_manager` directly.

- [ ] **Step 3: Update legacy `websocket_endpoint` signature**

```python
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    container: ServiceContainer = Depends(get_container),
    manager: IConnectionManager = Depends(get_connection_manager),
):
```

Replace all `ws_manager` references inside with `manager`.

- [ ] **Step 4: Remove lifespan `app.state` mutation**

In `lifespan`, delete:

```python
        app.state.services = container
        ...
        terminal_manager = TerminalSessionManager(...)
        app.state.terminal_manager = terminal_manager
```

Keep `initialize_container(container)`.

- [ ] **Step 5: Update `test_main.py` fixtures**

Change:

```python
@pytest.fixture(autouse=True)
def _reset_global_container():
    yield
    reset_container()
```

To reset *before* yield:

```python
@pytest.fixture(autouse=True)
def _reset_global_container():
    reset_container()
    yield
```

Change `client` fixture:

```python
@pytest.fixture
def client(container):
    initialize_container(container)
    app.dependency_overrides[get_container] = lambda: container
    c = TestClient(app, raise_server_exceptions=False)
    try:
        yield c
    finally:
        c.close()
        app.dependency_overrides.clear()
```

- [ ] **Step 6: Update `test_terminal.py` fixtures**

Similarly:

```python
@pytest.fixture(autouse=True)
def _reset_global_container():
    reset_container()
    yield


@pytest.fixture
def client(container):
    initialize_container(container)
    app.dependency_overrides[get_container] = lambda: container
    c = TestClient(app, raise_server_exceptions=False)
    try:
        yield c
    finally:
        c.close()
        app.dependency_overrides.clear()
```

Remove any `app.state.terminal_manager = ...` lines.

- [ ] **Step 7: Run tests**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_main.py tests/unit/test_terminal.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/recursive_neon/main.py backend/tests/unit/test_main.py backend/tests/unit/test_terminal.py
git commit -m "feat(ws): inject terminal and connection managers via Depends"
```

---

## Task 5: Per-session `ShellSession` isolation

**Files:**
- Modify: `backend/src/recursive_neon/shell/shell.py`
- Modify: `backend/src/recursive_neon/terminal.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestTerminalSessionIsolation:
    async def test_two_terminal_sessions_have_independent_cwd(self, container):
        mgr = TerminalSessionManager(container=container)
        s1 = mgr.create_session()
        s2 = mgr.create_session()

        # s1 cd into Documents
        s1.shell.session.cwd_id = s1.shell.session.resolve_path("Documents").id
        # s2 should still be at root
        assert s1.shell.session.get_cwd_path() == "/Documents"
        assert s2.shell.session.get_cwd_path() == "/"

        await mgr.remove_session(s1.session_id)
        await mgr.remove_session(s2.session_id)

    async def test_two_terminal_sessions_have_independent_env(self, container):
        mgr = TerminalSessionManager(container=container)
        s1 = mgr.create_session()
        s2 = mgr.create_session()

        s1.shell.session.env["FOO"] = "bar"
        assert "FOO" not in s2.shell.session.env

        await mgr.remove_session(s1.session_id)
        await mgr.remove_session(s2.session_id)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestTerminalSessionIsolation -v
```

Expected: FAIL because both sessions share a single `ShellSession`.

- [ ] **Step 3: Make `Shell` accept an injected session**

In `backend/src/recursive_neon/shell/shell.py`:

```python
    def __init__(
        self,
        container: ServiceContainer,
        output: Output | None = None,
        data_dir: str | None = None,
        session: ShellSession | None = None,
    ) -> None:
        self.output = output or Output()
        self.session = session or ShellSession(container)
        self.data_dir = data_dir
        ...
```

- [ ] **Step 4: Create per-session `ShellSession` in terminal manager**

In `backend/src/recursive_neon/terminal.py`:

```python
    def create_session(self) -> TerminalSession:
        session_id = uuid.uuid4().hex[:12]
        shell_session = ShellSession(
            container=self._container,
            username="user",
            hostname="neon-proxy",
        )
        shell = Shell(
            container=self._container,
            data_dir=self._data_dir,
            session=shell_session,
        )
        ts = TerminalSession(session_id=session_id, shell=shell)
        self._sessions[session_id] = ts
        logger.info("Terminal session created: %s", session_id)
        self._ensure_auto_save_running()
        return ts
```

- [ ] **Step 5: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/recursive_neon/shell/shell.py backend/src/recursive_neon/terminal.py backend/tests/unit/test_terminal.py
git commit -m "feat(terminal): isolate ShellSession per terminal connection"
```

---

## Task 6: Test concurrent file creation safety

**Files:**
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the test**

```python
    async def test_concurrent_file_creation_is_safe(self, container):
        mgr = TerminalSessionManager(container=container)
        s1 = mgr.create_session()
        s2 = mgr.create_session()

        root_id = s1.shell.session.resolve_path("/").id
        s1.shell.session.container.app_service.create_file(
            {"name": "a.txt", "parent_id": root_id, "content": "a"}
        )
        s2.shell.session.container.app_service.create_file(
            {"name": "b.txt", "parent_id": root_id, "content": "b"}
        )

        children = s1.shell.session.container.app_service.list_directory(root_id)
        names = {c.name for c in children}
        assert {"a.txt", "b.txt"} <= names

        await mgr.remove_session(s1.session_id)
        await mgr.remove_session(s2.session_id)
```

- [ ] **Step 2: Run the test**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestTerminalSessionIsolation::test_concurrent_file_creation_is_safe -v
```

Expected: PASS (relies on existing AppService locking from Work Stream 2.2).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_terminal.py
git commit -m "test(terminal): concurrent file creation across sessions"
```

---

## Task 7: Create typed WebSocket message models

**Files:**
- Create: `backend/src/recursive_neon/models/ws_messages.py`
- Create: `backend/tests/unit/models/test_ws_messages.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/models/test_ws_messages.py`:

```python
"""Tests for /ws/terminal message models."""

import pytest

from recursive_neon.models.ws_messages import (
    ClientMessage,
    CompleteMessage,
    InputMessage,
    KeyMessage,
    ResizeMessage,
    parse_client_message,
)


class TestParseClientMessage:
    def test_input_message(self):
        msg = parse_client_message({"type": "input", "line": "ls"})
        assert isinstance(msg, InputMessage)
        assert msg.line == "ls"

    def test_key_message(self):
        msg = parse_client_message({"type": "key", "key": "ArrowUp"})
        assert isinstance(msg, KeyMessage)
        assert msg.key == "ArrowUp"

    def test_resize_message(self):
        msg = parse_client_message({"type": "resize", "width": 80, "height": 24})
        assert isinstance(msg, ResizeMessage)
        assert msg.width == 80
        assert msg.height == 24

    def test_complete_message(self):
        msg = parse_client_message({"type": "complete", "line": "l"})
        assert isinstance(msg, CompleteMessage)
        assert msg.line == "l"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_client_message({"type": "bogus"})

    def test_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            parse_client_message({"type": "input"})

    def test_client_message_union(self):
        """Union alias is importable."""
        assert ClientMessage is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/models/test_ws_messages.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the models**

Create `backend/src/recursive_neon/models/ws_messages.py`:

```python
"""Pydantic models for the /ws/terminal WebSocket protocol."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class InputMessage(BaseModel):
    type: Literal["input"]
    line: str


class KeyMessage(BaseModel):
    type: Literal["key"]
    key: str


class ResizeMessage(BaseModel):
    type: Literal["resize"]
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


class CompleteMessage(BaseModel):
    type: Literal["complete"]
    line: str


ClientMessage = InputMessage | KeyMessage | ResizeMessage | CompleteMessage


class OutputMessage(BaseModel):
    type: Literal["output"]
    text: str


class PromptMessage(BaseModel):
    type: Literal["prompt"]
    text: str


class CompletionsMessage(BaseModel):
    type: Literal["completions"]
    items: list[str]
    replace: int


class ModeMessage(BaseModel):
    type: Literal["mode"]
    mode: Literal["raw", "cooked"]


class ScreenMessage(BaseModel):
    type: Literal["screen"]
    lines: list[str]
    cursor: list[int]
    cursor_visible: bool


class ExitMessage(BaseModel):
    type: Literal["exit"]


class ErrorMessage(BaseModel):
    type: Literal["error"]
    message: str


def parse_client_message(data: dict) -> ClientMessage:
    """Validate and parse an incoming client message.

    Raises:
        ValueError: If the message is malformed or has an unknown type.
    """
    try:
        msg_type = data.get("type")
        if msg_type == "input":
            return InputMessage.model_validate(data)
        if msg_type == "key":
            return KeyMessage.model_validate(data)
        if msg_type == "resize":
            return ResizeMessage.model_validate(data)
        if msg_type == "complete":
            return CompleteMessage.model_validate(data)
        raise ValueError(f"Unknown message type: {msg_type}")
    except ValidationError as e:
        raise ValueError(f"Invalid message: {e}") from e
```

- [ ] **Step 4: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/recursive_neon/models/ws_messages.py backend/tests/unit/models/test_ws_messages.py
git commit -m "feat(protocol): add typed /ws/terminal message models"
```

---

## Task 8: Validate messages in `_ws_reader`

**Files:**
- Modify: `backend/src/recursive_neon/main.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestTerminalMessageValidation:
    def test_malformed_message_returns_typed_error(self, client):
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input"})  # missing "line"
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "Invalid message" in resp["message"]

    def test_resize_message_validated(self, client):
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "resize", "width": -1, "height": 24})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    def test_unknown_message_returns_typed_error(self, client):
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "bogus"})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "Unknown message type" in resp["message"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestTerminalMessageValidation -v
```

Expected: FAIL — malformed messages may crash or return wrong error.

- [ ] **Step 3: Update `_ws_reader`**

In `backend/src/recursive_neon/main.py`:

```python
from recursive_neon.models.ws_messages import (
    ErrorMessage,
    KeyMessage,
    InputMessage,
    ResizeMessage,
    CompleteMessage,
    parse_client_message,
)


async def _ws_reader(
    websocket: WebSocket, session: TerminalSession
) -> None:
    """Read messages from the WebSocket and feed them into the shell."""
    while True:
        try:
            msg = parse_client_message(await websocket.receive_json())
        except ValueError as e:
            await websocket.send_json(
                {"type": "error", "message": str(e)}
            )
            continue

        if isinstance(msg, InputMessage):
            if session.mode == "cooked":
                session.feed_line(msg.line)
        elif isinstance(msg, KeyMessage):
            if session.mode == "raw":
                session.feed_key(msg.key)
        elif isinstance(msg, ResizeMessage):
            session.feed_resize(msg.width, msg.height)
        elif isinstance(msg, CompleteMessage):
            if session.mode == "cooked":
                items, replace = session.shell.get_completions_ext(msg.line)
                await websocket.send_json(
                    {"type": "completions", "items": items, "replace": replace}
                )
        else:
            await websocket.send_json(
                {"type": "error", "message": f"Unknown message type: {msg.type}"}
            )
```

Note: completion locking is added in Task 10.

- [ ] **Step 4: Update `terminal_websocket` docstring**

Ensure the completions server → client message includes `replace`:

```python
        Server → Client:
            {"type": "output", "text": "..."}
            {"type": "prompt", "text": "user@neon:~$ "}
            {"type": "completions", "items": [...], "replace": 0}
```

- [ ] **Step 5: Run the tests**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/recursive_neon/main.py backend/tests/unit/test_terminal.py
git commit -m "feat(ws): validate /ws/terminal messages with Pydantic models"
```

---

## Task 9: Align frontend protocol types

**Files:**
- Modify: `frontend/src/terminal/protocol.ts`

- [ ] **Step 1: Inspect current TypeScript definitions**

Open `frontend/src/terminal/protocol.ts` and confirm the following fields match the backend models exactly:

| Backend model | TypeScript interface | Fields |
|---------------|---------------------|--------|
| `OutputMessage` | `OutputMessage` | `type: 'output'; text: string` |
| `PromptMessage` | `PromptMessage` | `type: 'prompt'; text: string` |
| `CompletionsMessage` | `CompletionsMessage` | `type: 'completions'; items: string[]; replace: number` |
| `ModeMessage` | `ModeMessage` | `type: 'mode'; mode: 'raw' | 'cooked'` |
| `ScreenMessage` | `ScreenMessage` | `type: 'screen'; lines: string[]; cursor: [number, number]; cursor_visible: boolean` |
| `ExitMessage` | `ExitMessage` | `type: 'exit'` |
| `ErrorMessage` | `ErrorMessage` | `type: 'error'; message: string` |
| `InputMessage` | `InputMessage` | `type: 'input'; line: string` |
| `KeyMessage` | `KeyMessage` | `type: 'key'; key: string` |
| `ResizeMessage` | `ResizeMessage` | `type: 'resize'; width: number; height: number` |
| `CompleteMessage` | `CompleteMessage` | `type: 'complete'; line: string` |

- [ ] **Step 2: Make any corrections**

If a field diverges, update the TypeScript interface. For example, if the backend sends `cursorVisible` instead of `cursor_visible`, change one side to match.

- [ ] **Step 3: Run frontend type check**

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/terminal/protocol.ts
git commit -m "chore(frontend): align terminal protocol types with backend models"
```

---

## Task 10: Add shell state lock for completions

**Files:**
- Modify: `backend/src/recursive_neon/shell/shell.py`
- Modify: `backend/src/recursive_neon/main.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestCompletionLocking:
    async def test_completion_uses_async_lock_path(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        items, replace = await session.shell.get_completions_ext_async("l")
        assert "ls" in items
        assert replace == 1

        await mgr.remove_session(session.session_id)

    async def test_completion_and_execution_are_mutually_exclusive(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        lock_acquired = []

        async def slow_command():
            async with session.shell._state_lock:
                lock_acquired.append("execute")
                await asyncio.sleep(0.05)

        async def completion():
            await asyncio.sleep(0.01)
            await session.shell.get_completions_ext_async("l")
            lock_acquired.append("complete")

        await asyncio.gather(slow_command(), completion())
        assert lock_acquired == ["execute", "complete"]

        await mgr.remove_session(session.session_id)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestCompletionLocking -v
```

Expected: `AttributeError: 'Shell' object has no attribute 'get_completions_ext_async'`.

- [ ] **Step 3: Add the lock and async method**

In `backend/src/recursive_neon/shell/shell.py`:

```python
import asyncio
...

class Shell:
    def __init__(...):
        ...
        self._state_lock = asyncio.Lock()
```

Add method:

```python
    async def get_completions_ext_async(self, text: str) -> tuple[list[str], int]:
        """Async version of get_completions_ext that holds the shell state lock."""
        async with self._state_lock:
            return self.get_completions_ext(text)
```

Wrap `execute_line`:

```python
    async def execute_line(self, line: str) -> int:
        async with self._state_lock:
            return await self._execute_line_unsafe(line)
```

Then rename the current body to `_execute_line_unsafe`.

- [ ] **Step 4: Use async completions in `_ws_reader`**

In `backend/src/recursive_neon/main.py`:

```python
        elif isinstance(msg, CompleteMessage):
            if session.mode == "cooked":
                items, replace = await session.shell.get_completions_ext_async(msg.line)
                await websocket.send_json(
                    {"type": "completions", "items": items, "replace": replace}
                )
```

- [ ] **Step 5: Run the tests**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/recursive_neon/shell/shell.py backend/src/recursive_neon/main.py backend/tests/unit/test_terminal.py
git commit -m "feat(shell): protect completion reads and command execution with state lock"
```

---

## Task 11: Enforce `/ws/terminal` connection limits

**Files:**
- Modify: `backend/src/recursive_neon/terminal.py`
- Modify: `backend/src/recursive_neon/main.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestConnectionLimits:
    def test_terminal_rejects_connection_over_limit(self, client):
        # Patch the manager to a tiny limit for the test
        container = get_container()
        container.terminal_manager.max_connections = 1

        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            # Second connection should be rejected
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/terminal") as ws2:
                    ws2.receive_json()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestConnectionLimits::test_terminal_rejects_connection_over_limit -v
```

Expected: FAIL because the second connection is currently accepted.

- [ ] **Step 3: Add `max_connections` to `TerminalSessionManager`**

In `backend/src/recursive_neon/terminal.py`:

```python
class TerminalSessionManager:
    AUTO_SAVE_INTERVAL_SECONDS = 60

    def __init__(
        self,
        container: ServiceContainer,
        data_dir: str | None = None,
        max_connections: int = 50,
    ) -> None:
        self._container = container
        self._data_dir = data_dir
        self.max_connections = max_connections
        ...
```

- [ ] **Step 4: Enforce limit in endpoint**

In `backend/src/recursive_neon/main.py`, inside `terminal_websocket`, immediately after accepting:

```python
    await websocket.accept()

    if terminal_manager.active_count >= terminal_manager.max_connections:
        await websocket.close(code=1013, reason="Server overloaded")
        return

    session = terminal_manager.create_session()
```

Note: `active_count` is checked after `accept()` so the client gets a clean close.

- [ ] **Step 5: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/recursive_neon/terminal.py backend/src/recursive_neon/main.py backend/tests/unit/test_terminal.py
git commit -m "feat(ws): enforce max connections on /ws/terminal"
```

---

## Task 12: Clean up terminal session tasks and queues

**Files:**
- Modify: `backend/src/recursive_neon/terminal.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestTerminalCleanup:
    async def test_disconnect_cleans_up_tasks_and_queues(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()
        await session.start()

        assert session._shell_task is not None
        assert not session._shell_task.done()

        await mgr.remove_session(session.session_id)

        assert session._shell_task.done() or session._shell_task.cancelled()
        assert mgr.active_count == 0
```

- [ ] **Step 2: Run the test to verify it passes/fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestTerminalCleanup::test_disconnect_cleans_up_tasks_and_queues -v
```

Expected: It may already pass; if not, fix `TerminalSession.stop`.

- [ ] **Step 3: Harden `TerminalSession.stop`**

In `backend/src/recursive_neon/terminal.py`:

```python
    async def stop(self) -> None:
        """Stop the shell and drain queues."""
        self.input_queue.put_nowait(None)
        self.key_queue.put_nowait(None)

        if self._shell_task is not None:
            try:
                await asyncio.wait_for(self._shell_task, timeout=2.0)
            except TimeoutError:
                self._shell_task.cancel()
                try:
                    await self._shell_task
                except asyncio.CancelledError:
                    pass
                logger.warning(
                    "Shell task for %s cancelled after timeout", self.session_id
                )

        # Drain output queue to avoid "task destroyed but it is pending" warnings
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
```

- [ ] **Step 4: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/recursive_neon/terminal.py backend/tests/unit/test_terminal.py
git commit -m "fix(terminal): cancel and drain shell task/queues on disconnect"
```

---

## Task 13: Type `TerminalSession.mode` as `Literal`

**Files:**
- Modify: `backend/src/recursive_neon/terminal.py`
- Test: `mypy`

- [ ] **Step 1: Update the dataclass field**

In `backend/src/recursive_neon/terminal.py`:

```python
from typing import Literal
...

@dataclass
class TerminalSession:
    ...
    mode: Literal["cooked", "raw"] = "cooked"
```

- [ ] **Step 2: Run mypy**

```bash
cd backend
../.venv/Scripts/mypy src/recursive_neon/terminal.py
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/recursive_neon/terminal.py
git commit -m "chore(types): narrow TerminalSession.mode to Literal"
```

---

## Task 14: Guard module-level logging configuration

**Files:**
- Modify: `backend/src/recursive_neon/main.py`
- Test: existing tests should not reconfigure logging

- [ ] **Step 1: Guard the basicConfig call**

In `backend/src/recursive_neon/main.py`:

```python
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
```

- [ ] **Step 2: Run tests**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_main.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/recursive_neon/main.py
git commit -m "fix(logging): guard basicConfig to avoid test-time reconfiguration"
```

---

## Task 15: Preserve lifespan exception context

**Files:**
- Modify: `backend/src/recursive_neon/main.py`
- Test: existing tests

- [ ] **Step 1: Raise RuntimeError from original exception**

In `backend/src/recursive_neon/main.py`, in the lifespan startup error handler:

```python
    except Exception as exc:
        logger.error("Startup error: %s", exc)
        if container:
            container.system_state.status = SystemStatus.ERROR
            container.system_state.last_error = str(exc)
        raise RuntimeError(f"Startup error: {exc}") from exc
```

- [ ] **Step 2: Run tests**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_main.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/recursive_neon/main.py
git commit -m "fix(lifespan): preserve exception context on startup failure"
```

---

## Task 16: Type `_ws_reader` / `_ws_writer` parameters

**Files:**
- Modify: `backend/src/recursive_neon/main.py`
- Test: `mypy`

- [ ] **Step 1: Add type annotations**

```python
async def _ws_reader(websocket: WebSocket, session: TerminalSession) -> None:
    ...

async def _ws_writer(websocket: WebSocket, session: TerminalSession) -> None:
    ...
```

- [ ] **Step 2: Run mypy**

```bash
cd backend
../.venv/Scripts/mypy src/recursive_neon/main.py
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/src/recursive_neon/main.py
git commit -m "chore(types): type _ws_reader and _ws_writer session params"
```

---

## Task 17: Wake raw-mode input on resize

**Files:**
- Modify: `backend/src/recursive_neon/terminal.py`
- Test: `backend/tests/unit/test_terminal.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_terminal.py`:

```python
class TestRawResizeWake:
    async def test_resize_wakes_raw_input(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        raw_input = WebSocketRawInput(session.key_queue)
        raw_input.set_resize_event(asyncio.Event())

        # No key queued; resize event wakes the wait
        async def trigger_resize():
            await asyncio.sleep(0.01)
            raw_input._resize_event.set()

        key_task = asyncio.create_task(raw_input.get_key())
        await trigger_resize()
        key = await key_task
        assert key is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend
../.venv/Scripts/pytest tests/unit/test_terminal.py::TestRawResizeWake::test_resize_wakes_raw_input -v
```

Expected: `AttributeError` on `set_resize_event` or `_resize_event`.

- [ ] **Step 3: Add resize event to `WebSocketRawInput`**

In `backend/src/recursive_neon/terminal.py`:

```python
class WebSocketRawInput:
    def __init__(self, key_queue: asyncio.Queue[str | None]) -> None:
        self._key_queue = key_queue
        self._resize_event: asyncio.Event | None = None

    def set_resize_event(self, event: asyncio.Event) -> None:
        self._resize_event = event

    async def get_key(self, *, timeout: float | None = None) -> str | None:
        if self._resize_event is not None and self._resize_event.is_set():
            self._resize_event.clear()
            return None

        key_task = asyncio.create_task(self._key_queue.get())
        tasks: set[asyncio.Task] = {key_task}
        resize_task: asyncio.Task | None = None
        if self._resize_event is not None:
            resize_task = asyncio.create_task(self._resize_event.wait())
            tasks.add(resize_task)

        try:
            if timeout is None:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
            else:
                done, pending = await asyncio.wait_for(
                    asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED),
                    timeout=timeout,
                )
        except TimeoutError:
            for task in tasks:
                task.cancel()
            return None

        for task in pending:
            task.cancel()

        if resize_task in done:
            if self._resize_event is not None:
                self._resize_event.clear()
            key_task.cancel()
            return None

        key = key_task.result()
        if key is None:
            raise EOFError
        return key
```

- [ ] **Step 4: Wire resize event in `TerminalSession.start`**

In `_run_tui_factory`:

```python
            raw_input = WebSocketRawInput(session.key_queue)
            raw_input.set_resize_event(session._resize_event)
```

Add `_resize_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)` to `TerminalSession`.

- [ ] **Step 5: Set event on `feed_resize` when raw**

In `TerminalSession.feed_resize`:

```python
    def feed_resize(self, width: int, height: int) -> None:
        self._terminal_size = (width, height)
        self._resize_pending = (width, height)
        if self.mode == "raw":
            self._resize_event.set()
```

- [ ] **Step 6: Run the test**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/recursive_neon/terminal.py backend/tests/unit/test_terminal.py
git commit -m "feat(terminal): wake raw-mode input on resize"
```

---

## Task 18: Run full quality gates

**Files:** all touched files

- [ ] **Step 1: Run lint, format, type check, and tests**

```bash
cd backend
../.venv/Scripts/ruff check .
../.venv/Scripts/ruff format --check .
../.venv/Scripts/mypy
../.venv/Scripts/pytest -q
```

Expected: all green.

- [ ] **Step 2: Fix any remaining issues**

Iterate on failures.

- [ ] **Step 3: Final commit**

```bash
git commit -m "chore(quality): full green gate for Work Stream C"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Every 5.1–5.6 requirement has at least one task.
- [x] **No placeholders:** No TBD/TODO/fill-in-later steps.
- [x] **Type consistency:** `ShellSession` injection, `TerminalSessionManager` constructor, message model names, and lock method names match across tasks. Managers are built locally inside factories to avoid circular imports, and the terminal manager's internal container reference is updated after the final container is assembled.
- [x] **Test coverage:** DI, isolation, message validation, completion locking, connection limits, cleanup, typing, and resize wake all have tests.

Plan is ready for execution.
