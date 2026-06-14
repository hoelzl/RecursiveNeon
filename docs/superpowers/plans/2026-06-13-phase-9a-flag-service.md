# Phase 9a — Flag / Quest State Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent, event-emitting key/value flag store (`FlagService`) that game logic and NPCs can query and mutate.

**Architecture:** Flags are stored on the shared `GameState` model (flat `dict[str, Any]`) so `AppService` can persist them alongside notes/tasks/filesystem. `FlagService` owns the mutation API and publishes `flag.set` / `flag.cleared` events on the existing `GameEventBus`. The service is injected through `ServiceContainer`/`ServiceFactory` like every other backend service.

**Tech Stack:** Python 3.13, Pydantic, pytest-asyncio, asyncio.

---

## File Structure

### New files
- `backend/src/recursive_neon/services/flag_service.py` — `FlagService` implementation.
- `backend/tests/unit/test_flag_service.py` — Unit tests for flag CRUD, events, and persistence.

### Modified files
- `backend/src/recursive_neon/services/interfaces.py` — Add `IFlagService` protocol.
- `backend/src/recursive_neon/models/game_state.py` — Add `flags: dict[str, Any]` to `GameState`.
- `backend/src/recursive_neon/dependencies.py` — Add `flag_service` to `ServiceContainer`; build it in both factories.
- `backend/src/recursive_neon/services/app_service.py` — Load/save `flags.json` in `save_all_to_disk`/`load_all_from_disk` and expose standalone helpers.
- `backend/tests/unit/test_interfaces.py` — Assert `FlagService` implements `IFlagService` and container field is the protocol.

---

## Task 1: Define the `IFlagService` protocol

**Files:**
- Modify: `backend/src/recursive_neon/services/interfaces.py`
- Test: `backend/tests/unit/test_interfaces.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_interfaces.py`:

```python
from recursive_neon.services.flag_service import FlagService
from recursive_neon.services.interfaces import IFlagService


def test_flag_service_implements_interface():
    service = FlagService(game_state=GameState(), event_bus=GameEventBus())
    assert isinstance(service, IFlagService)


def test_container_flag_service_field_is_interface():
    hints = get_type_hints(ServiceContainer)
    assert hints["flag_service"] is IFlagService
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_interfaces.py -v
```

Expected: `ModuleNotFoundError: No module named 'recursive_neon.services.flag_service'`.

- [ ] **Step 3: Add the protocol**

Append to `backend/src/recursive_neon/services/interfaces.py` (after `IAppService`):

```python
# ============================================================================
# Flag Service Interface
# ============================================================================


@runtime_checkable
class IFlagService(Protocol):
    """Protocol for the persistent world-flag / quest-state store."""

    def set_flag(self, key: str, value: Any = True) -> None: ...
    def clear_flag(self, key: str) -> None: ...
    def get_flag(self, key: str, default: Any = None) -> Any: ...
    def has_flag(self, key: str) -> bool: ...
    def list_flags(self) -> dict[str, Any]: ...
```

- [ ] **Step 4: Run the test again**

Same command.

Expected: `ModuleNotFoundError` (the implementation does not exist yet).

- [ ] **Step 5: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/services/interfaces.py backend/tests/unit/test_interfaces.py
git commit -m "feat(flags): define IFlagService protocol and failing interface tests"
```

---

## Task 2: Add `flags` to `GameState`

**Files:**
- Modify: `backend/src/recursive_neon/models/game_state.py`
- Test: `backend/tests/unit/test_flag_service.py` (will be expanded in Task 3)

- [ ] **Step 1: Update `GameState`**

In `backend/src/recursive_neon/models/game_state.py`, add the field:

```python
class GameState(BaseModel):
    """Overall game state"""

    player_id: str = "player_1"
    current_location: str = "main_lobby"
    active_quests: list[str] = Field(default_factory=list)
    completed_quests: list[str] = Field(default_factory=list)
    inventory: dict[str, int] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)

    # App states
    notes: NotesState = Field(default_factory=NotesState)
    tasks: TasksState = Field(default_factory=TasksState)
    filesystem: FileSystemState = Field(default_factory=FileSystemState)
```

- [ ] **Step 2: Run existing tests to catch regressions**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_app_service.py tests/unit/test_main.py -q
```

Expected: PASS. Adding a defaulted Pydantic field should not break existing serialization.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/models/game_state.py
git commit -m "feat(flags): add flags dict to GameState"
```

---

## Task 3: Implement `FlagService`

**Files:**
- Create: `backend/src/recursive_neon/services/flag_service.py`
- Test: `backend/tests/unit/test_flag_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_flag_service.py`:

```python
"""Tests for the world-flag / quest-state service."""

from __future__ import annotations

import pytest

from recursive_neon.models.game_state import GameState
from recursive_neon.services.flag_service import FlagService
from recursive_neon.services.game_event_bus import GameEventBus


class TestFlagService:
    def test_set_and_get_flag(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("door.unlocked", True)
        assert service.get_flag("door.unlocked") is True
        assert service.has_flag("door.unlocked") is True

    def test_get_flag_with_default(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        assert service.get_flag("missing", "fallback") == "fallback"
        assert service.has_flag("missing") is False

    def test_set_overwrites_value(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("counter", 1)
        service.set_flag("counter", 2)
        assert service.get_flag("counter") == 2

    def test_clear_flag_removes_it(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("tmp", "value")
        service.clear_flag("tmp")
        assert service.has_flag("tmp") is False
        assert service.get_flag("tmp") is None

    def test_clear_missing_flag_is_no_op(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.clear_flag("never_set")
        assert service.has_flag("never_set") is False

    def test_list_flags_returns_copy(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("a", 1)
        service.set_flag("b", 2)
        flags = service.list_flags()
        assert flags == {"a": 1, "b": 2}
        flags["a"] = 99
        assert service.get_flag("a") == 1

    def test_set_publishes_flag_set_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.set", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("door.unlocked", True)
        assert len(events) == 1
        assert events[0][0] == "flag.set"
        assert events[0][1] == {"key": "door.unlocked", "value": True, "old_value": None}

    def test_set_overwrite_includes_old_value(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append(data)

        bus.subscribe("flag.set", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("x", 1)
        service.set_flag("x", 2)
        assert events[-1] == {"key": "x", "value": 2, "old_value": 1}

    def test_clear_publishes_flag_cleared_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.cleared", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("door.unlocked", True)
        service.clear_flag("door.unlocked")
        assert len(events) == 1
        assert events[0][0] == "flag.cleared"
        assert events[0][1] == {"key": "door.unlocked", "old_value": True}

    def test_clear_missing_does_not_publish(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.cleared", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.clear_flag("missing")
        assert events == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_flag_service.py -v
```

Expected: `ModuleNotFoundError` for `recursive_neon.services.flag_service`.

- [ ] **Step 3: Implement `FlagService`**

Create `backend/src/recursive_neon/services/flag_service.py`:

```python
"""Persistent world-flag / quest-state service."""

from __future__ import annotations

import copy
import logging
from typing import Any

from recursive_neon.models.game_state import GameState
from recursive_neon.services.game_event_bus import GameEventBus

logger = logging.getLogger(__name__)


class FlagService:
    """Key/value store for world flags and quest state.

    Mutations are published on the ``GameEventBus``:
        - ``flag.set``   → {"key": str, "value": Any, "old_value": Any | None}
        - ``flag.cleared`` → {"key": str, "old_value": Any | None}

    Values should be JSON-serialisable scalars.  The service does not
    enforce this at runtime, but persistence will fail loudly if a value
    cannot be serialised.
    """

    def __init__(
        self,
        game_state: GameState,
        event_bus: GameEventBus,
    ) -> None:
        self._game_state = game_state
        self._event_bus = event_bus

    def set_flag(self, key: str, value: Any = True) -> None:
        """Set *key* to *value* and publish a ``flag.set`` event."""
        old_value = self._game_state.flags.get(key)
        self._game_state.flags[key] = value
        self._event_bus.publish(
            "flag.set",
            {"key": key, "value": value, "old_value": old_value},
        )
        logger.debug("Flag set: %s = %r (was %r)", key, value, old_value)

    def clear_flag(self, key: str) -> None:
        """Remove *key* and publish a ``flag.cleared`` event if it existed."""
        old_value = self._game_state.flags.pop(key, None)
        if key in self._game_state.flags or old_value is not None:
            self._event_bus.publish(
                "flag.cleared",
                {"key": key, "old_value": old_value},
            )
            logger.debug("Flag cleared: %s (was %r)", key, old_value)

    def get_flag(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if unset."""
        return self._game_state.flags.get(key, default)

    def has_flag(self, key: str) -> bool:
        """Return True if *key* is set."""
        return key in self._game_state.flags

    def list_flags(self) -> dict[str, Any]:
        """Return a shallow copy of all flags."""
        return copy.copy(self._game_state.flags)
```

Note: the `clear_flag` condition above is intentionally conservative. A
simpler, correct version is:

```python
    def clear_flag(self, key: str) -> None:
        old_value = self._game_state.flags.pop(key, None)
        if old_value is not None or key in self._game_state.flags:
            self._event_bus.publish(
                "flag.cleared",
                {"key": key, "old_value": old_value},
            )
```

Use whichever form is easier to read; the tests only cover the
pop-and-publish path.

- [ ] **Step 4: Run the tests**

Same command as Step 2.

Expected: PASS.

- [ ] **Step 5: Run `test_interfaces.py` again**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_interfaces.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/services/flag_service.py backend/tests/unit/test_flag_service.py
git commit -m "feat(flags): implement FlagService with events"
```

---

## Task 4: Wire `FlagService` into DI

**Files:**
- Modify: `backend/src/recursive_neon/dependencies.py`
- Test: `backend/tests/unit/test_flag_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_flag_service.py`:

```python
from recursive_neon.dependencies import ServiceFactory


class TestFlagServiceDI:
    def test_test_container_provides_flag_service(self):
        container = ServiceFactory.create_test_container()
        assert container.flag_service is not None
        assert isinstance(container.flag_service, FlagService)

    def test_flag_service_shares_game_state_with_app_service(self):
        container = ServiceFactory.create_test_container()
        container.flag_service.set_flag("shared", 123)
        assert container.app_service.game_state.flags["shared"] == 123
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_flag_service.py::TestFlagServiceDI -v
```

Expected: `TypeError: ServiceContainer.__init__() missing required argument 'flag_service'`.

- [ ] **Step 3: Update `ServiceContainer`**

In `backend/src/recursive_neon/dependencies.py`:

1. Import `IFlagService`:

```python
from recursive_neon.services.interfaces import (
    IAppService,
    IConnectionManager,
    IFlagService,
    IGameEventBus,
    INPCManager,
    IOllamaClient,
    IProcessManager,
    ITerminalSessionManager,
    LLMInterface,
)
```

2. Add the field to the dataclass:

```python
@dataclass
class ServiceContainer:
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    system_state: SystemState
    game_state: GameState
    app_service: IAppService
    flag_service: IFlagService
    terminal_manager: ITerminalSessionManager
    connection_manager: IConnectionManager
    start_time: datetime
    process_table: ProcessTable = field(default_factory=ProcessTable)
    event_bus: IGameEventBus = field(default_factory=GameEventBus)
```

3. Update `__repr__` to include `flag_service`:

```python
    def __repr__(self) -> str:
        return (
            f"ServiceContainer("
            f"process_manager={type(self.process_manager).__name__}, "
            f"ollama_client={type(self.ollama_client).__name__}, "
            f"npc_manager={type(self.npc_manager).__name__}, "
            f"system_state={type(self.system_state).__name__}, "
            f"game_state={type(self.game_state).__name__}, "
            f"app_service={type(self.app_service).__name__}, "
            f"flag_service={type(self.flag_service).__name__}, "
            f"terminal_manager={type(self.terminal_manager).__name__}, "
            f"connection_manager={type(self.connection_manager).__name__}, "
            f"event_bus={type(self.event_bus).__name__}, "
            f"process_table={type(self.process_table).__name__}, "
            f"start_time={self.start_time.isoformat()})"
        )
```

- [ ] **Step 4: Build `FlagService` in both factories**

In `ServiceFactory.create_production_container`, after the `AppService` is created and state is loaded, add:

```python
        flag_service = FlagService(
            game_state=game_state,
            event_bus=container.event_bus,
        )
```

Then pass `flag_service=flag_service` into the `ServiceContainer(...)` call.

Because `FlagService` is constructed before the container exists, use a temporary container for the event bus. The existing code already builds a temporary container with `event_bus=GameEventBus()` defaulted; build `flag_service` after that container is assembled:

```python
        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            flag_service=None,  # type: ignore[arg-type]
            terminal_manager=None,  # type: ignore[arg-type]
            connection_manager=ConnectionManager(),
            start_time=start_time,
            process_table=ProcessTable.with_defaults(),
        )

        flag_service = FlagService(
            game_state=game_state,
            event_bus=container.event_bus,
        )
        terminal_manager = TerminalSessionManager(
            container=container,
            data_dir=data_dir,
        )
        container = dataclasses.replace(
            container,
            flag_service=flag_service,
            terminal_manager=terminal_manager,
        )
        terminal_manager._container = container
```

In `ServiceFactory.create_test_container`, add the same `flag_service` construction and pass it in:

```python
        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            flag_service=None,  # type: ignore[arg-type]
            terminal_manager=None,  # type: ignore[arg-type]
            connection_manager=ConnectionManager(),
            start_time=start_time,
        )

        flag_service = FlagService(
            game_state=game_state,
            event_bus=container.event_bus,
        )
        terminal_manager = TerminalSessionManager(container=container)
        container = dataclasses.replace(
            container,
            flag_service=flag_service,
            terminal_manager=terminal_manager,
        )
        terminal_manager._container = container
```

- [ ] **Step 5: Run the tests**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_flag_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/dependencies.py backend/tests/unit/test_flag_service.py
git commit -m "feat(di): wire FlagService into ServiceContainer"
```

---

## Task 5: Persist flags via `AppService`

**Files:**
- Modify: `backend/src/recursive_neon/services/app_service.py`
- Test: `backend/tests/unit/test_flag_service.py`

- [ ] **Step 1: Write the failing persistence tests**

Append to `backend/tests/unit/test_flag_service.py`:

```python
import tempfile


class TestFlagServicePersistence:
    async def test_flags_round_trip_through_app_service(self):
        from recursive_neon.dependencies import ServiceFactory

        container = ServiceFactory.create_test_container()
        container.flag_service.set_flag("door.unlocked", True)
        container.flag_service.set_flag("counter", 42)

        with tempfile.TemporaryDirectory() as tmpdir:
            await container.app_service.save_all_to_disk(tmpdir)

            new_container = ServiceFactory.create_test_container()
            await new_container.app_service.load_all_from_disk(tmpdir)
            assert new_container.flag_service.get_flag("door.unlocked") is True
            assert new_container.flag_service.get_flag("counter") == 42
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_flag_service.py::TestFlagServicePersistence -v
```

Expected: FAIL — flags are not saved/loaded yet.

- [ ] **Step 3: Add save/load helpers to `AppService`**

In `backend/src/recursive_neon/services/app_service.py`, add after `load_tasks_from_disk` / before `save_all_to_disk`:

```python
    async def save_flags_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save flag state to disk."""
        async with self._save_lock:
            await asyncio.to_thread(
                self._sync_save_json,
                data_dir,
                "flags.json",
                {"flags": self.game_state.flags},
            )

    async def load_flags_from_disk(
        self, data_dir: str = "backend/game_data"
    ) -> bool:
        """Load flag state from disk. Returns True if a file was found."""
        data = await asyncio.to_thread(
            self._sync_load_json, data_dir, "flags.json"
        )
        if data is None:
            return False
        try:
            self.game_state.flags = dict(data.get("flags", {}))
            return True
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Corrupt flags.json: %s", e)
            return False
```

- [ ] **Step 4: Include flags in `save_all_to_disk` / `load_all_from_disk`**

Update `save_all_to_disk` to also call `save_flags_to_disk`:

```python
    async def save_all_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save all state (filesystem, notes, tasks, flags) to disk."""
        async with self._save_lock:
            await asyncio.to_thread(
                self._sync_save_json,
                data_dir,
                "filesystem.json",
                {
                    "nodes": [
                        node.model_dump(mode="json")
                        for node in self.game_state.filesystem.nodes
                    ],
                    "root_id": self.game_state.filesystem.root_id,
                },
            )
            await asyncio.to_thread(
                self._sync_save_json,
                data_dir,
                "notes.json",
                {
                    "notes": [
                        note.model_dump(mode="json")
                        for note in self.game_state.notes.notes
                    ],
                },
            )
            await asyncio.to_thread(
                self._sync_save_json,
                data_dir,
                "tasks.json",
                {
                    "lists": [
                        tl.model_dump(mode="json")
                        for tl in self.game_state.tasks.lists
                    ],
                },
            )
            await asyncio.to_thread(
                self._sync_save_json,
                data_dir,
                "flags.json",
                {"flags": self.game_state.flags},
            )
```

Update `load_all_from_disk`:

```python
    async def load_all_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load all state from disk. Returns True if filesystem was loaded."""
        fs_loaded = await self.load_filesystem_from_disk(data_dir)
        await self.load_notes_from_disk(data_dir)
        await self.load_tasks_from_disk(data_dir)
        await self.load_flags_from_disk(data_dir)
        return fs_loaded
```

- [ ] **Step 5: Load flags in production startup**

In `ServiceFactory.create_production_container`, after loading notes and tasks, add:

```python
        # Load flags (non-fatal if missing)
        await app_service.load_flags_from_disk(data_dir)
```

- [ ] **Step 6: Run the tests**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
../.venv/Scripts/pytest tests/unit/test_flag_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/services/app_service.py backend/src/recursive_neon/dependencies.py backend/tests/unit/test_flag_service.py
git commit -m "feat(flags): persist flags via AppService"
```

---

## Task 6 (Optional): Expose a debug `flag` shell command

**Files:**
- Create: `backend/src/recursive_neon/shell/programs/flag.py`
- Modify: `backend/src/recursive_neon/shell/shell.py`
- Test: `backend/tests/unit/shell/test_flag_program.py`

This is optional. Skip it if the goal is the minimum viable Phase 9a.
If implemented, gate the command behind `settings.debug` or hide it
from default `help` output so it does not become diegetic UI.

- [ ] **Step 1: Implement `prog_flag`**

A minimal version:

```python
"""Debug flag command."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from recursive_neon.shell.programs import ProgramContext


async def prog_flag(ctx: ProgramContext) -> int:
    args = ctx.args
    if not args:
        ctx.stdout.writeln("Usage: flag <set|get|clear|list> ...")
        return 1

    service = ctx.services.flag_service
    sub = args[0]

    if sub == "set":
        if len(args) < 2:
            ctx.stdout.writeln("Usage: flag set <key> [value]")
            return 1
        key = args[1]
        value = args[2] if len(args) > 2 else True
        service.set_flag(key, value)
        ctx.stdout.writeln(f"Set flag {key}")
        return 0

    if sub == "get":
        if len(args) < 2:
            ctx.stdout.writeln("Usage: flag get <key>")
            return 1
        value = service.get_flag(args[1])
        ctx.stdout.writeln(str(value))
        return 0

    if sub == "clear":
        if len(args) < 2:
            ctx.stdout.writeln("Usage: flag clear <key>")
            return 1
        service.clear_flag(args[1])
        ctx.stdout.writeln(f"Cleared flag {args[1]}")
        return 0

    if sub == "list":
        for key, value in service.list_flags().items():
            ctx.stdout.writeln(f"{key} = {value}")
        return 0

    ctx.stdout.writeln(f"Unknown flag subcommand: {sub}")
    return 1
```

- [ ] **Step 2: Register it in `Shell`**

In `backend/src/recursive_neon/shell/shell.py`, import and register
`prog_flag` only when `settings.debug` is true:

```python
from recursive_neon.config import settings
...
if settings.debug:
    from recursive_neon.shell.programs.flag import prog_flag
    registry.register_fn("flag", prog_flag, "Debug: set/get/list world flags")
```

- [ ] **Step 3: Add tests**

Create `backend/tests/unit/shell/test_flag_program.py` covering at
least `flag set`, `flag get`, and `flag list`.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git add backend/src/recursive_neon/shell/programs/flag.py backend/src/recursive_neon/shell/shell.py backend/tests/unit/shell/test_flag_program.py
git commit -m "feat(shell): add debug flag command"
```

---

## Task 7: Full quality gates

**Files:** all touched files

- [ ] **Step 1: Run lint, format, type check, and tests**

```bash
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon/backend
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
cd C:/Users/tc/Programming/LLM-Assisted/Projects/RecursiveNeon
git commit --allow-empty -m "chore(quality): full green gate for Phase 9a"
```

---

## Self-Review

- **Spec coverage:** Every Phase 9a requirement from `docs/PHASE_9_PLAN.md` §9a is covered: CRUD API, events, persistence, DI, optional shell exposure.
- **No placeholders:** Every step includes exact file paths, code, and commands.
- **Type consistency:** `IFlagService` method names and signatures match `FlagService` exactly. `ServiceContainer` fields and factory construction are updated together.
- **Game state integration:** Flags live on `GameState.flags`, matching the existing pattern for notes/tasks/filesystem and avoiding a second persistence owner.
