# Backend Conventions

## Python Style

- **Imports**: stdlib → third-party → local, alphabetical within groups
- **Classes**: PascalCase. Interfaces prefixed with `I` (e.g., `INPCManager`)
- **Functions/methods**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Private**: leading underscore
- **Type hints**: always on function parameters and return values
- **Docstrings**: Google-style (Args/Returns/Raises)
- **Async**: all I/O operations should be async; use `asyncio.to_thread()` for blocking ops

## Dependency Injection

Services are wired through `ServiceContainer` (dataclass) and `ServiceFactory` (static methods):

```python
# dependencies.py
@dataclass
class ServiceContainer:
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    system_state: SystemState
    game_state: GameState
    app_service: AppService
    start_time: datetime

class ServiceFactory:
    @staticmethod
    def create_production_container() -> ServiceContainer: ...

    @staticmethod
    def create_test_container(**overrides) -> ServiceContainer: ...
```

To add a new service:
1. Define interface in `services/interfaces.py`
2. Implement in `services/my_service.py`
3. Add field to `ServiceContainer`
4. Wire in `ServiceFactory.create_production_container()`
5. Add mock support in `create_test_container()`

## Shell Programs

Programs are standalone executables with a restricted interface (`ProgramContext`). They cannot modify shell state (cwd, env vars).

To add a new program:
1. Create an async function: `async def prog_mycommand(ctx: ProgramContext) -> int`
2. Access services via `ctx.services.app_service`, `ctx.services.npc_manager`, etc.
3. Write output via `ctx.stdout.writeln()`, errors via `ctx.stderr.error()`
4. Return exit code (0 = success, nonzero = error)
5. Register in a `register_*_programs(registry)` function
6. Call the registration function from `Shell.__init__` in `shell.py`

Programs that need subcommands (like `note`, `task`) dispatch via a dict in the main function. Reference `notes.py` and `tasks.py` for the pattern.

Only commands that **must** modify shell state (cwd, env vars) are builtins. Everything else is a program.

## Testing

- Framework: pytest + pytest-asyncio (auto mode — no `@pytest.mark.asyncio` needed)
- Fixtures in `tests/conftest.py` (mock LLM, sample NPCs)
- Shell test fixtures in `tests/unit/shell/conftest.py` (`test_container`, `make_ctx`, `output`)
- Group related tests in classes (`class TestMyService:`)
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Mock via DI — inject mocks through `ServiceFactory.create_test_container()`
- Shell programs: create `ProgramContext` via `make_ctx`, call the program function directly, assert on `CapturedOutput`

```bash
pytest                     # all tests
pytest -m unit             # unit only
pytest -m integration      # integration only
pytest -m "not slow"       # skip slow
pytest --cov               # with coverage
```
