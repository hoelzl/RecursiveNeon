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

## Testing

- Framework: pytest + pytest-asyncio
- Fixtures in `tests/conftest.py` (mock LLM, sample NPCs)
- Group related tests in classes (`class TestMyService:`)
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Async tests: `@pytest.mark.asyncio`
- Mock via DI — inject mocks through `ServiceFactory.create_test_container()`

```bash
pytest                     # all tests
pytest -m unit             # unit only
pytest -m "not slow"       # skip slow
pytest --cov               # with coverage
```
