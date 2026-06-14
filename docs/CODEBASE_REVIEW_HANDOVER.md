# Codebase Review Handover — Recursive://Neon

**Status:** Section 2 (Cross-Cutting Foundations) implemented; remaining sections pending
**Scope:** Address all architectural, design, implementation, testing, and documentation issues identified in the deep review.
**Design decisions (confirmed by maintainer):**

1. **Config loader:** Move user config to a controlled game path; eliminate `~/.neon-edit.py`.
2. **Terminal sessions:** Per-session `ShellSession` with shared services.
3. **Persistence:** Native `async` persistence methods using `asyncio.to_thread()` internally.
4. **Editor boundary:** Single typed `IEditorHost` interface injected into `Editor`.

---

## 1. How to Use This Document

Each work stream below contains:

- **Goal** — what we are fixing and why.
- **Affected files** — the primary files to change.
- **Detailed changes** — concrete implementation steps.
- **Tests to add/update** — how to verify the fix.
- **Acceptance criteria** — the conditions that close the issue.

At the end is a traceability table mapping every issue from the review to its handover section, ensuring nothing is dropped.

---

## 2. Cross-Cutting Foundations ✅ Completed

These changes unblock or simplify most other streams. They have been implemented and all acceptance criteria are met (see notes below).

### 2.1 Define missing service interfaces

**Goal:** Complete the DI layer so every service is consumed via an interface.

**Files:**

- `backend/src/recursive_neon/services/interfaces.py`
- `backend/src/recursive_neon/dependencies.py`
- `backend/src/recursive_neon/services/app_service.py`
- `backend/src/recursive_neon/services/game_event_bus.py`
- All call sites that use `container.app_service` / `container.event_bus`

**Detailed changes:**

1. In `interfaces.py`:
   - Add `IAppService` protocol with all public methods currently used by shell, editor, HTTP endpoints, and tests.
   - Add `IGameEventBus` protocol with `subscribe`, `unsubscribe`, and `publish` (the existing method used by every call site).
   - Extend `IOllamaClient` with `generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]` and `chat(self, messages: list[dict[str, str]], **kwargs) -> str`.
   - Rename `LLMInterface.invoke` parameter `input` to `prompt` to avoid shadowing the built-in.
2. In `dependencies.py`:
   - Change `ServiceContainer.app_service: IAppService` and `event_bus: IGameEventBus`.
   - Update `__repr__` to include all fields.
   - Type `app_service` and `event_bus` as the interfaces in `create_test_container`; keep the real `AppService` / `GameEventBus` as defaults because many tests rely on their behavior.
3. In `app_service.py` / `game_event_bus.py`:
   - Add explicit `implements`/`Protocol` declarations (via inheritance or `typing.Protocol` runtime check in tests).
   - Add `AppService.get_filesystem_root_id()` to avoid leaking `game_state` through the interface; update `path_resolver.py`, `glob.py`, `completion.py`, and filesystem programs to use it.
4. Run `mypy` and fix any call-site type errors.

**Tests:**

- Add `tests/unit/test_interfaces.py` asserting that `AppService` implements `IAppService` and `GameEventBus` implements `IGameEventBus`.
- Update mocks in `tests/conftest.py` to use `spec=IAppService`, `spec=IGameEventBus`, `spec=IOllamaClient`, etc.

**Acceptance criteria:**

- `mypy` passes with no `Any`-typed service access in `shell/`, `editor/`, `main.py`, or `terminal.py`.
- No direct `AppService`/`GameEventBus` construction outside factories/tests.

### 2.2 Convert persistence and I/O methods to async

**Goal:** Remove blocking disk I/O and psutil calls from the async event loop.

**Files:**

- `backend/src/recursive_neon/services/app_service.py`
- `backend/src/recursive_neon/services/npc_manager.py`
- `backend/src/recursive_neon/services/process_manager.py`
- `backend/src/recursive_neon/dependencies.py`
- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/terminal.py`
- `backend/src/recursive_neon/shell/shell.py`
- `backend/src/recursive_neon/shell/__main__.py`
- `backend/src/recursive_neon/models/game_state.py`

**Detailed changes:**

1. In `app_service.py`:
   - Change `save_all_to_disk`, `load_all_from_disk`, `save_filesystem`, `load_filesystem`, `save_notes`, `load_notes`, `save_tasks`, `load_tasks` to `async def`.
   - Internally use `asyncio.to_thread(_sync_save_json)` / `asyncio.to_thread(_sync_load_json)`.
   - Add an `asyncio.Lock` (`self._save_lock`) and acquire it in `save_all_to_disk` to prevent concurrent writes.
2. In `npc_manager.py`:
   - Make `save_npcs_to_disk` and `load_npcs_from_disk` `async def`, using `asyncio.to_thread`.
3. In `process_manager.py`:
   - Make `get_status` `async def` and wrap the `psutil` calls in `asyncio.to_thread`.
   - Redirect `stdout=subprocess.DEVNULL` for the Ollama subprocess, or spawn a task to drain `self.process.stdout`.
4. In `dependencies.py`:
   - Make `create_production_container` `async def` and wrap the initial load/save calls in `asyncio.to_thread`.
5. In `main.py` lifespan:
   - `await ServiceFactory.create_production_container()`.
   - `await container.app_service.load_all_to_disk()` etc.
   - Make Ollama startup non-fatal: if `start()` or `wait_for_ready()` fails, log the exception, set `system_state.status = SystemStatus.DEGRADED`, and continue. Only chat endpoints fail when Ollama is unavailable.
6. In `terminal.py`:
   - `await self._save_game_state()` in `_auto_save_loop` and `remove_session`.
   - Remove the misleading docstring reference to `container.app_service.lock`; reference the real `AppService` lock instead.
7. In `shell/shell.py`:
   - On exit, `await container.app_service.save_all_to_disk()` and `await container.npc_manager.save_npcs_to_disk()`.
8. In `shell/__main__.py`:
   - Wrap startup in an async helper so `await ServiceFactory.create_production_container()` works for the local CLI.
9. In `models/game_state.py`:
   - Add `DEGRADED = "degraded"` to `SystemStatus`.

**Tests:**

- Update `test_app_service.py`, `test_npc_manager.py`, `test_filesystem_security.py`, and `tests/integration/test_full_flows.py` to be `async def` and `await` persistence calls.
- Add `test_save_runs_in_thread` and `test_concurrent_save_is_serialized` to `test_app_service.py`.
- Update `test_terminal.py` auto-save test to assert `filesystem.json` / `npcs.json` are written.
- Add `test_chat_returns_503_when_ollama_degraded` to `test_main.py`.

**Acceptance criteria:**

- `ruff` / `mypy` pass.
- No blocking disk I/O or `cpu_percent` calls in async paths.
- Server starts successfully when Ollama is missing, with chat endpoints returning a clear error.
- Local CLI (`python -m recursive_neon.shell`) still works.

### 2.3 Refactor `ServiceFactory`/`NPCManager` construction

**Goal:** Remove direct `ChatOllama` construction from the DI factory and the service.

**Files:**

- `backend/src/recursive_neon/dependencies.py`
- `backend/src/recursive_neon/services/npc_manager.py`
- `backend/src/recursive_neon/services/ollama_client.py`
- `backend/src/recursive_neon/services/interfaces.py`

**Detailed changes:**

1. In `ollama_client.py`, add `OllamaLangChainAdapter` implementing `LLMInterface` by converting LangChain messages to dicts and calling `IOllamaClient.chat`, returning an `AIMessage`.
2. In `dependencies.py`:
   - Remove the `ChatOllama` import.
   - `create_npc_manager(ollama_client=None, llm=None)` builds the adapter from `ollama_client` when no `llm` is injected.
3. In `npc_manager.py`:
   - Remove the deprecated `llm is None` fallback branch that constructs `ChatOllama`.
   - Remove `create_with_ollama`.
   - Type the constructor parameter as `LLMInterface` and raise `TypeError` if `None`.

**Tests:**

- Update `test_npc_manager.py` to inject `Mock(spec=LLMInterface)`.
- Remove the legacy default-LLM and `create_with_ollama` tests.
- Add `test_npc_manager_requires_llm`.
- Add adapter tests in `test_ollama_client.py`.

**Acceptance criteria:**

- `dependencies.py` does not import `ChatOllama`.
- `NPCManager` always receives an injected `LLMInterface`.
- All NPC tests use mocks.
- `OllamaLangChainAdapter` correctly maps messages and returns an `AIMessage`.

### Section 2 verification

Implemented in the working tree. Quality gates:

```bash
cd backend
../.venv/Scripts/ruff check .
../.venv/Scripts/mypy
../.venv/Scripts/pytest -q
```

Result: **2484 passed**, ruff clean, mypy clean.

---

## 3. Work Stream A: Virtual Filesystem & Security

### 3.1 Move editor config loader to a controlled path

**Goal:** Close the real-filesystem isolation breach.

**Files:**

- `backend/src/recursive_neon/editor/config_loader.py`
- `backend/src/recursive_neon/shell/programs/edit.py`
- `backend/src/recursive_neon/config.py`
- `backend/FILESYSTEM_SECURITY.md`
- `backend/tests/unit/editor/test_config_loader.py` (new)

**Detailed changes:**

1. In `config.py`, add a new setting `editor_config_path: Path = Field(default=Path("game_data") / ".neon-edit.py")`.
2. In `config_loader.py`:
   - Remove the default `~/.neon-edit.py` path.
   - Resolve the config path relative to `settings.data_dir`.
   - Validate the resolved path is inside `settings.data_dir`.
   - Keep the sandbox (restricted builtins, no `__import__`, limited `editor` object) but document that it is now for trusted game config only.
3. In `edit.py`:
   - Pass `settings.editor_config_path` to the editor's config loader.
4. In `FILESYSTEM_SECURITY.md`:
   - Document the controlled config path as a third legitimate real-filesystem touch point.
   - State that the file is executed in a restricted sandbox and must be trusted.

**Tests:**

- `test_config_loader_reads_controlled_path`
- `test_config_loader_rejects_path_outside_data_dir`
- `test_config_loader_blocked_builtins`
- `test_config_loader_whitelisted_imports`

**Acceptance criteria:**

- No code reads `~/.neon-edit.py` or `Path.home()` for editor config.
- Path traversal outside `data_dir` is rejected.
- Security docs describe the new boundary.

### 3.2 Return immutable filesystem nodes

**Goal:** Prevent callers from corrupting `AppService` indexes by mutating returned `FileNode` objects.

**Files:**

- `backend/src/recursive_neon/services/app_service.py`
- `backend/src/recursive_neon/models/file_node.py` (if exists)

**Detailed changes:**

1. Audit all public methods returning `FileNode` (`get_node`, `resolve_path`, `create_file`, etc.).
2. Return `node.model_copy()` in methods where mutation by callers is a risk.
3. Alternatively, add a config flag to `FileNode` making it frozen in production; benchmark first because immutability may affect editor/dired performance.

**Tests:**

- `test_mutating_returned_file_node_does_not_affect_index`

**Acceptance criteria:**

- Mutating a returned `FileNode` does not change `AppService`'s internal indexes.

### 3.3 Validate action input fields

**Goal:** Turn `KeyError` crashes into client-friendly errors.

**Files:**

- `backend/src/recursive_neon/services/app_service.py`

**Detailed changes:**

1. In `handle_action`, define a small helper `_require(data, *keys)` that raises `ValueError(f"Missing required field: {key}")` instead of using bare `data[key]`.
2. Apply it to every action (`list`, `read`, `write`, etc.).

**Tests:**

- Add parametrized `test_handle_action_missing_fields_returns_valueerror`.

**Acceptance criteria:**

- Missing action fields return `400` with a clear message, not `500`.

### 3.4 Validate initial filesystem path

**Goal:** Prevent `INITIAL_FS_PATH` misconfiguration from reading arbitrary host directories.

**Files:**

- `backend/src/recursive_neon/services/app_service.py`

**Detailed changes:**

1. In `load_initial_filesystem`, resolve `initial_fs_dir` to an absolute path.
2. Resolve a known safe root (the package's `initial_fs/` directory or `settings.data_dir`) and reject `initial_fs_dir` if it is not a subpath.
3. While walking, avoid following symlinks outside the root; or resolve each item and re-validate.

**Tests:**

- `test_load_initial_filesystem_rejects_path_outside_root`
- `test_load_initial_filesystem_rejects_symlink_escape`

**Acceptance criteria:**

- Misconfigured `INITIAL_FS_PATH` raises a clear error at startup.
- Symlinks cannot escape the initial FS root.

---

## 4. Work Stream B: Shell, Output Abstraction, and Pipelines

### 4.1 Fix `Output` abstraction composition

**Goal:** Make stderr redirect/merge work over WebSocket and pipes without dropping output.

**Files:**

- `backend/src/recursive_neon/shell/output.py`
- `backend/src/recursive_neon/shell/shell.py`
- `backend/src/recursive_neon/shell/builtins.py`

**Detailed changes:**

1. In `output.py`:
   - Make `Output` an abstract base or add public methods:
     - `with_stderr(self, other: Output) -> Output`
     - `merge_stderr(self) -> Output`
   - Implement these in `CapturedOutput`, `QueueOutput`, and `MergedStderrOutput`.
   - `QueueOutput.with_stderr` must return a new `QueueOutput` whose `error` method sends `{"type":"output",...}` messages to the same queue (so stderr becomes visible in the browser).
   - Remove any external access to `._stream` / `._err_stream`.
2. In `shell.py`:
   - Replace the builtin wrapper that builds `Output(stream=qo._stream, err_stream=stderr_cap._err_stream)` with `qo.with_stderr(stderr_cap)`.
   - Replace `MergedStderrOutput` direct stream access with the new composition API.
3. In `builtins.py`:
   - Ensure builtins use only public `Output` methods.

**Tests:**

- `test_stderr_redirect_to_file_over_websocket`
- `test_2and1_redirect_over_websocket`
- `test_builtin_stderr_redirect_in_pipeline`

**Acceptance criteria:**

- `export 2> err.txt`, `cmd 2>&1`, and builtins in pipelines produce correct browser-terminal output.
- No code accesses `Output._stream` or `Output._err_stream` outside `output.py`.

### 4.2 Remove blocking `input()` fallback from `chat`

**Goal:** Enforce async input in the chat program.

**Files:**

- `backend/src/recursive_neon/shell/programs/chat.py`

**Detailed changes:**

1. Remove the `input()` fallback branch.
2. If `ctx.get_line` is `None`, write a clear error to `ctx.stderr` and return `1`.
3. Update tests to always inject `ctx.get_line`.

**Tests:**

- `test_chat_without_input_source_returns_error`
- Update existing chat tests to provide `get_line`.

**Acceptance criteria:**

- `chat` never calls the blocking built-in `input()`.

### 4.3 Tighten exception handling in shell dispatch

**Goal:** Prevent broad `except Exception` from hiding bugs.

**Files:**

- `backend/src/recursive_neon/shell/shell.py`

**Detailed changes:**

1. Define a small exception hierarchy:
   - `ShellError(Exception)` — user-facing errors (file not found, invalid args, etc.).
   - `ProgramNotFoundError(ShellError)`
2. Catch `ShellError` and `NotADirectoryError`/`FileNotFoundError` explicitly.
3. For unexpected exceptions, log the full traceback via the configured logger and return a generic "Internal error" message to the user.

**Tests:**

- `test_unexpected_exception_logs_traceback`
- `test_program_not_found_returns_user_friendly_error`

**Acceptance criteria:**

- No bare `except Exception:` in command dispatch.
- Programming errors produce logs, not silent failures.

### 4.4 Align `export` and `env` internal-variable filtering

**Goal:** Prevent `export` from leaking internal `_data_dir` path.

**Files:**

- `backend/src/recursive_neon/shell/builtins.py`
- `backend/src/recursive_neon/shell/programs/utility.py`

**Detailed changes:**

1. In `builtin_export`, filter out keys starting with `_` unless a `-a` / `--all` flag is passed.
2. Document the internal-variable convention in help text.

**Tests:**

- `test_export_hides_underscore_variables`
- `test_export_all_shows_internal_variables`

**Acceptance criteria:**

- `export` and `env` agree on which variables are visible by default.

### 4.5 Unify quote-state parsing

**Goal:** Eliminate duplicated quote/escape walkers.

**Files:**

- `backend/src/recursive_neon/shell/parser.py`
- `backend/src/recursive_neon/shell/completion.py`

**Detailed changes:**

1. In `parser.py`, expose a public iterator:
   - `walk_tokens(line: str) -> Iterator[Token | QuoteStateChange]`
   - or a lower-level `QuoteWalker` class that tracks state and yields characters with metadata.
2. Replace the inline quote walkers in `completion.get_current_argument` and `parser._extract_redirect_target` with the shared iterator.

**Tests:**

- Ensure existing parser and completion tests still pass.
- Add `test_redirect_target_with_nested_quotes` and `test_completion_with_escaped_quotes`.

**Acceptance criteria:**

- Only one quote-state walker exists.
- Completion and redirect extraction behave identically for quoting edge cases.

### 4.6 Fix `find` completer after `-name`

**Goal:** Stop offering directory completions where a glob pattern is expected.

**Files:**

- `backend/src/recursive_neon/shell/programs/filesystem.py`
- `backend/src/recursive_neon/shell/completion.py`

**Detailed changes:**

1. In the `find` completer, track whether the previous token is `-name`, `-iname`, `-path`, or `-regex`.
2. If completing the argument to one of these options, return `[]`.
3. Otherwise return `complete_paths(ctx, dirs_only=True)`.

**Tests:**

- `test_find_complete_after_name_returns_empty`
- `test_find_complete_path_returns_directories`

**Acceptance criteria:**

- Tab after `find . -name ` produces no completions.
- Tab after `find ` still completes directories.

### 4.7 Shell polish

**Goal:** Address minor shell issues.

**Files:**

- `backend/src/recursive_neon/shell/session.py`
- `backend/src/recursive_neon/shell/shell.py`
- `backend/src/recursive_neon/shell/output.py`

**Detailed changes:**

1. **PS1:** Either honor `env["PS1"]` in `_build_prompt` (with a safe fallback) or remove the unused `env["PS1"]` initialization.
2. **Flush:** Add an explicit `flush()` method to `Output`; make `write`/`writeln` not auto-flush. Update callers that need immediate flush.
3. **History:** Cap `session.history` to a configurable limit (e.g., 1000 entries). Persist/load via prompt_toolkit `FileHistory` if desired.

**Tests:**

- `test_ps1_env_var_is_respected_or_removed`
- `test_history_capped_at_limit`

**Acceptance criteria:**

- No dead `PS1` variable.
- History does not grow unbounded.

---

## 5. Work Stream C: WebSocket Terminal & Session Architecture

### 5.1 Move terminal session manager into DI container

**Goal:** Remove global singleton and `app.state` access.

**Files:**

- `backend/src/recursive_neon/dependencies.py`
- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/terminal.py`

**Detailed changes:**

1. In `dependencies.py`:
   - Add `terminal_manager: TerminalSessionManager` to `ServiceContainer`.
   - Build it in `create_production_container` and `create_test_container`.
2. In `main.py`:
   - Remove module-level `ws_manager = ConnectionManager()` (or fold it into the container if still needed for legacy `/ws`).
   - Provide `get_terminal_manager(container: ServiceContainer = Depends(get_container)) -> TerminalSessionManager`.
   - Inject it into `terminal_websocket`.
   - Remove `app.state.terminal_manager` mutation.
3. In `terminal.py`:
   - Ensure `TerminalSessionManager` does not depend on global state.

**Tests:**

- Update `test_main.py` and `test_terminal.py` to use `dependency_overrides` instead of mutating `app.state`.
- Reset global container *before* each test in the autouse fixture.

**Acceptance criteria:**

- No `app.state.terminal_manager` access.
- Terminal manager is injectable.

### 5.2 Per-session `ShellSession` isolation

**Goal:** Make concurrent terminal sessions safe.

**Files:**

- `backend/src/recursive_neon/terminal.py`
- `backend/src/recursive_neon/shell/shell.py`
- `backend/src/recursive_neon/shell/session.py`

**Detailed changes:**

1. In `terminal.py`:
   - When creating a `Shell`, pass a per-session `ShellSession` initialized from defaults.
   - Share the same `ServiceContainer` for services, but not shell state.
2. In `shell.py`:
   - Accept an optional `session: ShellSession` parameter in `Shell.__init__`.
   - If not provided, create one internally (backwards compatible for local CLI).
3. Ensure compound operations that must be atomic use the service-layer lock added in 2.2.

**Tests:**

- `test_two_terminal_sessions_have_independent_cwd`
- `test_two_terminal_sessions_have_independent_env`
- `test_concurrent_file_creation_is_safe`

**Acceptance criteria:**

- Two browser tabs can `cd` independently without affecting each other.
- Shared game state mutations remain consistent.

### 5.3 Typed WebSocket message models

**Goal:** Make `/ws/terminal` protocol type-safe and validated.

**Files:**

- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/models/ws_messages.py` (new)
- `frontend/src/terminal/protocol.ts`

**Detailed changes:**

1. Create Pydantic models matching the protocol:
   - `InputMessage`, `KeyMessage`, `ResizeMessage`, `CompleteMessage`.
2. In `main.py`:
   - Validate `websocket.receive_json()` into these models.
   - Use `msg.type` dispatch with exhaustiveness checking.
3. Update the docstring for `completions` to include the `replace` field.

**Tests:**

- `test_terminal_rejects_malformed_message`
- `test_terminal_resize_message_validated`

**Acceptance criteria:**

- Malformed client messages return a typed error, not a 500.
- Backend and frontend protocol definitions match exactly.

### 5.4 Route completions through the shell task

**Goal:** Eliminate the completion/state race.

**Files:**

- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/terminal.py`
- `backend/src/recursive_neon/shell/shell.py`

**Detailed changes:**

1. Add an `asyncio.Lock` to `Shell` for read-only state operations.
2. In `main.py`, acquire the shell lock before calling `get_completions_ext`.
3. Alternatively, send a special completion request through the input queue and await the response.

**Tests:**

- `test_completion_does_not_race_with_command_execution`

**Acceptance criteria:**

- Completions are computed against a consistent shell state.

### 5.5 Connection limits and cleanup

**Goal:** Prevent resource exhaustion and dead-socket leaks.

**Files:**

- `backend/src/recursive_neon/main.py`
- `backend/src/recursive_neon/terminal.py`

**Detailed changes:**

1. Apply `MAX_CONNECTIONS` logic to `/ws/terminal`.
2. On `ConnectionManager.broadcast` send failure, remove the connection.
3. On terminal disconnect, ensure `TerminalSessionManager.remove_session` cleans up tasks and queues.

**Tests:**

- `test_terminal_rejects_connection_over_limit`
- `test_broadcast_removes_dead_connection`

**Acceptance criteria:**

- Connection count is bounded.
- Failed sockets are removed from active sets.

### 5.6 Clean up terminal.py internals

**Goal:** Fix minor terminal issues.

**Files:**

- `backend/src/recursive_neon/terminal.py`
- `backend/src/recursive_neon/main.py`

**Detailed changes:**

1. Type `TerminalSession.mode` as `Literal["cooked", "raw"]`.
2. Move module-level `logging.basicConfig` in `main.py` into the lifespan, or guard it.
3. Improve lifespan error context: raise `RuntimeError(...) from exc` instead of discarding the original exception.
4. Type `_ws_reader` and `_ws_writer` `session` parameters as `TerminalSession`.
5. Wake raw-mode input on resize so TUI apps process resize immediately.

**Tests:**

- Existing type checks.

**Acceptance criteria:**

- `mypy` passes on `terminal.py` and `main.py`.
- Resize events reach TUI apps without waiting for the next keystroke.

---

## 6. Work Stream D: Editor Architecture

### 6.1 Introduce `IEditorHost` and decouple game services

**Goal:** Remove `Any`-typed service access and private-attribute coupling.

**Files:**

- `backend/src/recursive_neon/editor/interfaces.py` (new)
- `backend/src/recursive_neon/editor/editor.py`
- `backend/src/recursive_neon/editor/game_bridge.py`
- `backend/src/recursive_neon/shell/programs/edit.py`
- `backend/tests/unit/editor/test_editor_game_bridge.py`

**Detailed changes:**

1. Define `IEditorHost` protocol with methods:
   - `open_note(note_id: str) -> None`
   - `open_task_list() -> None`
   - `list_npcs() -> None`
   - `send_npc_message(npc_id: str, message: str, callback: Callable[[str], None]) -> None`
   - `subscribe_to_events(handler: Callable[[GameEvent], None]) -> None`
   - `save_buffer_as_note(buffer_name: str, content: str) -> None`
2. In `edit.py`, implement a concrete `EditorHost` adapter around `ServiceContainer`.
3. In `editor.py`:
   - Replace `game_state`, `app_service`, `npc_manager`, `event_bus: Any` with a single `host: IEditorHost`.
   - Update `open_callback`, `save_callback`, and NPC/event wiring to use `host`.
4. In `game_bridge.py`, make functions operate on the host adapter rather than reaching into `editor.app_service`.

**Tests:**

- `test_editor_host_is_required`
- `test_editor_uses_host_for_open_note`
- Update `test_editor_game_bridge.py` to use `Mock(spec=IEditorHost)`.

**Acceptance criteria:**

- `Editor` has no `Any`-typed game-service attributes.
- No code accesses `editor.app_service` or `editor.npc_manager` directly.

### 6.2 Refactor `Editor` god class into coordinators

**Goal:** Reduce `Editor` size and responsibility.

**Files:**

- `backend/src/recursive_neon/editor/editor.py`
- New files:
  - `editor/prefix_controller.py`
  - `editor/register_controller.py`
  - `editor/search_controller.py` (isearch + query-replace)
  - `editor/window_coordinator.py`
  - `editor/minibuffer_controller.py` (optional)

**Detailed changes:**

1. Extract prefix argument handling into `PrefixArgController`.
2. Extract register read/write into `RegisterController`.
3. Extract isearch/query-replace session state and capture-mode routing into `SearchController`.
4. Extract window-tree operations into `WindowCoordinator`.
5. `Editor` becomes the composition root: it owns coordinators and delegates.
6. While refactoring, fix:
   - `C-u` ignored while prefix keymap pending.
   - Duplicate command execution logic in `_execute_command_by_name` / `execute_command`.

**Tests:**

- Existing editor tests should pass with minimal changes.
- Add unit tests for each coordinator in isolation.

**Acceptance criteria:**

- `Editor.__init__` is under 80 lines.
- `C-x C-u` correctly accumulates a prefix arg for the pending command.

### 6.3 Fix shell-mode async/memory issues

**Goal:** Stop leaking tasks and mutating state unsafely.

**Files:**

- `backend/src/recursive_neon/editor/shell_mode.py`
- `backend/src/recursive_neon/editor/editor.py`

**Detailed changes:**

1. In `shell_mode.py`:
   - Add a done-callback to each background task that removes it from `Editor._background_tasks`.
   - Or stop storing fire-and-forget tasks if the list is unused.
2. Define a public `IShellHost` protocol for the attributes currently accessed via private attributes (`_input_source`, `_build_prompt`, `_run_tui_factory`, `session.history`, `get_completions_ext`).
3. In `editor.py`, route NPC responses through `after_key()` / `request_render` instead of mutating state directly from the async callback.

**Tests:**

- `test_shell_mode_task_is_removed_when_done`
- `test_npc_event_uses_async_bridge`

**Acceptance criteria:**

- `_background_tasks` does not grow unbounded.
- `on_npc_event` does not mutate editor state outside the key/render cycle.

### 6.4 Fix editor performance hot paths

**Goal:** Keep the editor responsive for large files.

**Files:**

- `backend/src/recursive_neon/editor/buffer.py`
- `backend/src/recursive_neon/editor/view.py`

**Detailed changes:**

1. In `buffer.py`:
   - Cache the joined buffer text.
   - Invalidate the cache on `insert_string`, `delete_region`, `replace_region`, etc.
   - Use the cache in the `text` property.
2. In `view.py`:
   - Start highlight search from `max(0, first_visible - len(term))` and stop at `last_visible`.
   - Use the line string (not `hash(line)`) as the syntax-highlight cache key.

**Tests:**

- `test_buffer_text_cache_invalidation`
- `test_highlight_scan_bounded_to_visible_region`

**Acceptance criteria:**

- Opening a 10,000-line file and searching does not cause per-keystroke lag.
- Highlight cache does not produce collisions across different lines.

### 6.5 Editor correctness and minor cleanups

**Goal:** Fix correctness bugs and code smells.

**Files:**

- `backend/src/recursive_neon/editor/mark.py`
- `backend/src/recursive_neon/editor/window.py`
- `backend/src/recursive_neon/editor/buffer.py`
- `backend/src/recursive_neon/editor/variables.py`
- `backend/src/recursive_neon/editor/view.py`
- `backend/src/recursive_neon/editor/default_commands.py`
- `backend/src/recursive_neon/editor/minibuffer.py`

**Detailed changes:**

1. **Mark hash contract:** Change `__hash__` to hash only `(self.line, self.col)` to match `__eq__`.
2. **Window cleanup:** Simplify `WindowTree.delete_window` active-window assignment; remove redundant `type: ignore`.
3. **Dead code:** Remove `Buffer._clamp_point` or call it defensively.
4. **truncate-lines:** Either implement line wrapping or remove the unused variable.
5. **Monolith split:** Split `default_commands.py` into focused modules:
   - `movement_commands.py`
   - `editing_commands.py`
   - `kill_commands.py`
   - `file_commands.py`
   - `window_commands.py`
   - `help_commands.py`
   Keep `default_commands.py` as a thin re-export module for backwards compatibility during transition.
6. **Minibuffer hooks:** Replace monkey-patched `Minibuffer.process_key` in isearch, query-replace, dired, and shell-mode with first-class hooks (`on_cancel`, `on_unknown_key`, `on_backspace`).

**Tests:**

- Existing tests continue to pass.
- Add `test_mark_hash_contract`.

**Acceptance criteria:**

- `default_commands.py` is under 400 lines or removed after transition.
- No monkey-patched `process_key` remains.
- `truncate-lines` is implemented or removed.

---

## 7. Work Stream E: Frontend Terminal

### 7.1 Validate server messages and add resilience

**Goal:** Prevent malformed JSON from crashing the UI and recover from disconnects.

**Files:**

- `frontend/src/terminal/NeonTerminal.tsx`
- `frontend/src/terminal/session.ts`
- `frontend/src/terminal/protocol.ts`

**Detailed changes:**

1. In `NeonTerminal.tsx`:
   - Wrap `JSON.parse` in `try/catch`.
   - Add a runtime `isServerMessage` type guard that checks `type` and required fields.
   - Render `[Protocol error]` for invalid messages.
2. Add connection-state machine (`connecting`, `open`, `closed`, `error`) with exponential back-off retry.
3. Surface status to the user (`[Reconnecting…]`).
4. Add an `onConnectionChange` prop for parent components.

**Tests:**

- Add `NeonTerminal.test.tsx` with mocked `WebSocket`, `xterm.js`, and `ResizeObserver`.
- Test mount/unmount, message routing, malformed message handling, and reconnection.

**Acceptance criteria:**

- Malformed server messages do not crash the terminal.
- A transient disconnect triggers retry with visible status.

### 7.2 Fix paste behavior

**Goal:** Match Python CLI paste semantics.

**Files:**

- `frontend/src/terminal/session.ts`

**Detailed changes:**

1. **Cooked mode:** Split pasted text on line endings and submit each non-empty line as a separate `input` message.
2. **Raw mode:**
   - Normalize `\r\n` and `\r` to `Enter` (matching `shell/keys.py`).
   - Batch consecutive key messages; send at most N keys per frame or use a small throttle.
   - Cap paste size to avoid flooding.

**Tests:**

- `test_cooked_paste_submits_multiple_lines`
- `test_raw_paste_normalizes_cr_to_enter`
- `test_raw_paste_batches_keys`

**Acceptance criteria:**

- Multi-line shell scripts paste correctly in cooked mode.
- Raw-mode paste does not generate one WebSocket message per character.

### 7.3 Frontend terminal polish

**Goal:** Address remaining frontend issues.

**Files:**

- `frontend/src/terminal/NeonTerminal.tsx`
- `frontend/src/terminal/session.ts`
- `frontend/src/terminal/lineEditor.ts`
- `frontend/src/terminal/__tests__/session.test.ts`

**Detailed changes:**

1. Make `NeonTerminal` accept `url?: string` and `theme?: ITheme` props; fall back to current defaults.
2. Type `THEME` as `ITheme` from `@xterm/xterm`.
3. Add `C-h`, `C-w`, and `C-l` bindings to `lineEditor.ts`.
4. Guard `handleResize` with `if (this.exited) return;`.
5. Make `mode` and `exited` private with read-only getters.
6. Fix `ESC = ''` in `session.test.ts` to `const ESC = '\u001b';`.
7. Debounce `ResizeObserver` callback.
8. Add accessibility attributes (`role="log"`, `aria-live="polite"`, `aria-label="Terminal"`).

**Tests:**

- Update `session.test.ts` assertions to actually check for escape byte.
- Add tests for new line-editor bindings.

**Acceptance criteria:**

- `ESC` constant is correct.
- Theme is typed.
- Resize is debounced.
- Component is reusable with different URLs/themes.

---

## 8. Work Stream F: Testing Infrastructure

### 8.1 Add markers to all tests

**Goal:** Make `pytest -m unit/integration/slow` reliable.

**Files:**

- All `backend/tests/**/*.py` files
- `backend/pyproject.toml`
- `backend/tests/conftest.py`

**Detailed changes:**

1. Add `@pytest.mark.unit` to fast, isolated tests.
2. Add `@pytest.mark.integration` to WebSocket/flow tests.
3. Add `@pytest.mark.slow` to tutorial walkthrough, parity-style, or heavy tests.
4. Remove `pytest_configure` marker registration from `tests/conftest.py` (already in `pyproject.toml`).
5. Optionally add a `pytest_collection_modifyitems` hook that marks unmarked tests as `unit` by default, then gradually make markers explicit.

**Tests:**

- `pytest -m unit` collects ~90% of tests.
- `pytest -m integration` collects WebSocket/flow tests.

**Acceptance criteria:**

- No unmarked tests (or unmarked tests default to `unit`).
- Selective test runs produce useful subsets.

### 8.2 Clean up fixtures

**Goal:** Remove duplication and shadowing.

**Files:**

- `backend/tests/conftest.py`
- `backend/tests/unit/shell/conftest.py`
- `backend/tests/unit/shell/test_pipeline.py`
- `backend/tests/unit/shell/test_builtins.py`
- `backend/tests/unit/test_npc_manager.py`

**Detailed changes:**

1. Delete local `output`/`shell` fixtures in `test_pipeline.py` and `test_builtins.py`.
2. Delete duplicate `mock_llm` / `sample_npc` fixtures in `test_npc_manager.py`.
3. Add `spec=` to shared mocks.
4. Add return-type annotations to all fixture functions.
5. Move `langchain_core.messages` import to the top of `tests/conftest.py`.
6. Annotate the `make_ctx` factory closure.

**Tests:**

- All existing tests pass.

**Acceptance criteria:**

- No fixture shadowing warnings.
- Shared mocks have `spec=`.

### 8.3 Hermetic initial filesystem for tests

**Goal:** Decouple tests from bundled world content.

**Files:**

- `backend/tests/conftest.py`
- `backend/tests/unit/shell/conftest.py`
- `backend/tests/integration/conftest.py`
- New: `backend/tests/fixtures/initial_fs/` and `backend/tests/fixtures/initial_fs_manifest.py`

**Detailed changes:**

1. Create a small deterministic test initial filesystem under `tests/fixtures/initial_fs/`.
2. Create `initial_fs_manifest.py` with constants for expected file/directory names.
3. Update conftest fixtures to use the test fixture path by default, not `settings.initial_fs_path`.
4. Replace hardcoded names in tests with manifest constants.

**Tests:**

- All shell and editor tests pass using the test fixture FS.

**Acceptance criteria:**

- Changing `initial_fs/` world content does not break tests.
- Tests do not import `settings` for FS paths unless testing config loading.

### 8.4 Fix global container state in endpoint tests

**Goal:** Eliminate cross-test pollution.

**Files:**

- `backend/tests/unit/test_main.py`
- `backend/tests/unit/test_terminal.py`

**Detailed changes:**

1. Change `_reset_global_container` to reset *before* yield.
2. Use `app.dependency_overrides[get_container] = lambda: container` instead of mutating `app.state`.
3. Reset overrides in teardown.

**Tests:**

- Existing endpoint tests pass in random order.

**Acceptance criteria:**

- `pytest-randomly` or manual randomization does not reveal order dependencies.

### 8.5 Replace brittle tests

**Goal:** Make tests verify behavior, not source code shape.

**Files:**

- `backend/tests/unit/test_main.py`
- `backend/tests/unit/test_filesystem_security.py`
- `backend/tests/unit/editor/harness.py`

**Detailed changes:**

1. In `test_main.py`:
   - Replace AST-based lifespan tests with lifespan invocation using mocked services.
   - Assert `save_all_to_disk` and `save_npcs_to_disk` are called on shutdown.
2. In `test_filesystem_security.py`:
   - Add behavioral tests: attempt to create files with host paths, monkey-patch `open`/`os.path` and run operations.
   - Assert persistence only touches `data_dir`.
   - Remove strict file-count assertions.
3. In `harness.py`:
   - After every key, force a redraw so `_screen` is never stale.

**Tests:**

- New behavioral tests pass.

**Acceptance criteria:**

- No AST parsing in tests.
- Security tests prove isolation behavior.

### 8.6 Remove redundant `@pytest.mark.asyncio`

**Goal:** Align with auto-asyncio convention.

**Files:**

- ~90 test files (see review list).

**Detailed changes:**

1. Remove all explicit `@pytest.mark.asyncio` decorators.

**Tests:**

- Full suite passes.

**Acceptance criteria:**

- No redundant markers remain.

---

## 9. Work Stream G: Parity Harness Quality

### 9.1 Decouple data classes from pty imports

**Goal:** Make `--list` and verdict unit tests work without `pexpect`/`pyte`.

**Files:**

- New: `parity/snapshot.py`
- `parity/harness.py`
- `parity/compare.py`
- `parity/report.py`
- `parity/run.py`
- `parity/tests/test_compare.py`

**Detailed changes:**

1. Move `Snapshot`, `ScenarioResult`, `StepResult`, and highlight-capture helpers into `parity/snapshot.py` with no third-party imports.
2. Have `harness.py` import them from `parity.snapshot`.
3. Update all consumers.

**Tests:**

- `python -m parity.run --list` works without `pexpect`.
- `pytest parity/tests/test_compare.py` collects and passes without pty extras.

**Acceptance criteria:**

- Verdict logic is testable on any platform.

### 9.2 Add parity harness to quality gates

**Goal:** Stop type/style drift in `parity/`.

**Files:**

- `backend/pyproject.toml`
- `.pre-commit-config.yaml`
- `parity/harness.py`
- Other `parity/*.py` files

**Detailed changes:**

1. Add `parity` to `tool.ruff.src` in `pyproject.toml`, or create a separate `parity/pyproject.toml`.
2. Add a mypy pass for `parity/`.
3. Update pre-commit hooks to cover `parity/*.py`.
4. Fix the invalid `callable[[], Driver]` annotation to `Callable[[], Driver]`.
5. Quote shell paths with `shlex.quote` in `targets.py` and `fixtures.py`.
6. Tighten scenario typing to `dict[str, list[Snapshot]]`.

**Tests:**

- `ruff check parity/`
- `mypy parity/`

**Acceptance criteria:**

- `parity/` passes Ruff and mypy in CI.

### 9.3 Parity harness robustness

**Goal:** Improve diagnostics and reduce flakiness.

**Files:**

- `parity/harness.py`
- `parity/run.py`
- `parity/targets.py`
- `parity/keys.py`
- `parity/compare.py`

**Detailed changes:**

1. Make `Driver.wait_for` raise `TimeoutError` by default.
2. Stop swallowing exceptions in `Driver.close`; log them.
3. Tighten scenario selection in `run.py` to exact or prefix matching instead of substring.
4. Wrap `mod.run()` in try/except and record failures cleanly.
5. Refactor `make_emacs_target` startup readiness into a helper with configurable timeouts.
6. Make `make_neon_target` wait for the marker in row -2 plus prompt disappearance.
7. Make trailing-whitespace handling configurable per scenario.
8. Add `parity/tests/test_keys.py` and fix the docstring example.

**Tests:**

- New `test_keys.py`.

**Acceptance criteria:**

- Scenario failures produce clear diagnostics.
- `--list` does not match unintended scenarios.

---

## 10. Work Stream H: Documentation Cleanup

**Goal:** Bring all docs in line with working code.

**Files:**

- `README.md`
- `docs/QUICKSTART.md`
- `docs/ARCHITECTURE.md`
- `docs/SHELL_DESIGN.md`
- `docs/V2_HANDOVER.md`
- `docs/BACKEND_CONVENTIONS.md`
- `AGENTS.md`
- `CLAUDE.md`

**Detailed changes:**

1. **README.md / QUICKSTART.md:**
   - Update Python version to `3.13` everywhere.
   - Fix architecture layer numbers to 3 (Browser Terminal) and 4 (Desktop GUI).
2. **ARCHITECTURE.md:**
   - Mark Layer 3 as implemented (xterm.js over `/ws/terminal`).
   - Mark Layer 4 as planned.
3. **SHELL_DESIGN.md:**
   - Update status banner to Phases 0-7f + Phase 8 tasks 1-3.
   - Remove obsolete "future" language for pipes, redirects, TUI apps, WebSocket transport.
4. **V2_HANDOVER.md:**
   - Update test count to 2,477 (or current collect).
   - Refresh file inventory to include `editor/dired.py`, `editor/app_host.py`, `frontend/src/terminal/`, split command modules, etc.
   - Remove outdated O(n) scan note.
   - Clarify that `/ws/terminal` lives in `terminal.py`.
   - Create `CHANGELOG.md` or remove references to it.
5. **BACKEND_CONVENTIONS.md:**
   - Fix `create_test_container` to `@classmethod`.
   - Document the actual DI + global service-locator pattern if it stays.
6. **AGENTS.md:**
   - Correct Pydantic version claim.
   - Fix coverage output location note.
   - Remove `CHANGELOG.md` reference or create the file.
   - Commit the uncommitted rewrite.
7. **CLAUDE.md:**
   - Ensure it stays consistent with the above.

**Tests:**

- Manual review of docs.

**Acceptance criteria:**

- A new contributor can follow README/QUICKSTART without hitting Python 3.14 issues.
- No doc claims a feature is "future" when it is implemented.

---

## 11. Suggested Implementation Order

1. **Sprint 0 — Foundations:**
   - 2.1 Define interfaces
   - 2.2 Async persistence
   - 2.3 NPCManager DI cleanup
   - 3.1 Config loader controlled path

2. **Sprint 1 — Shell & Output:**
   - 4.1 Output composition API
   - 4.2-4.7 Shell fixes

3. **Sprint 2 — WebSocket Terminal:**
   - 5.1 DI for terminal manager
   - 5.2 Per-session isolation
   - 5.3 Typed WS messages
   - 5.4-5.6 Terminal polish

4. **Sprint 3 — Editor Architecture:**
   - 6.1 IEditorHost
   - 6.2 Coordinator extraction
   - 6.3 Shell-mode async fixes
   - 6.4 Performance fixes
   - 6.5 Editor correctness

5. **Sprint 4 — Frontend Terminal:**
   - 7.1 Validation/reconnection
   - 7.2 Paste parity
   - 7.3 Frontend polish

6. **Sprint 5 — Testing & Docs:**
   - 8.1-8.6 Test infrastructure
   - 9.1-9.3 Parity harness
   - 10. Documentation cleanup

---

## 12. Traceability to Review Issues

| Review # | Issue | Handover Section |
|----------|-------|------------------|
| 1 | Blocking sync I/O in async paths | 2.2 |
| 2 | `~/.neon-edit.py` arbitrary code execution | 3.1 |
| 3 | `Output` abstraction leaks private streams | 4.1 |
| 4 | `chat` blocking `input()` fallback | 4.2 |
| 5 | `OllamaProcessManager` blocks loop / undrained stdout | 2.2 |
| 6 | Missing service interfaces | 2.1 |
| 7 | `ServiceFactory` constructs `ChatOllama` | 2.3 |
| 8 | Global `ConnectionManager` / `app.state` | 5.1 |
| 9 | `TerminalSession` mutates `Shell._run_tui_factory` | 5.1, 5.2 |
| 10 | Shared `ServiceContainer` across sessions | 5.2 |
| 11 | `Editor` god class | 6.2 |
| 12 | Editor depends on `Any`-typed services | 6.1 |
| 13 | Private-attribute coupling | 6.1, 6.3 |
| 14 | Shell-mode task memory leak | 6.3 |
| 15 | `on_npc_event` direct async mutation | 6.3 |
| 16 | `Buffer.text` O(n) | 6.4 |
| 17 | Full-buffer highlight scan | 6.4 |
| 18 | No Pydantic WS validation | 5.3 |
| 19 | Completion race | 5.4 |
| 20 | No `/ws/terminal` connection limit | 5.5 |
| 21 | Frontend validation/reconnection/paste | 7.1, 7.2 |
| 22 | Missing test markers | 8.1 |
| 23 | Duplicate/shadowed fixtures | 8.2 |
| 24 | Global container mutation in tests | 8.4 |
| 25 | Tests depend on real `initial_fs_path` | 8.3 |
| 26 | AST-based brittle tests | 8.5 |
| 27 | Static-name security test | 8.5 |
| 28 | Broad `except Exception` | 4.3 |
| 29 | `export`/`env` filtering mismatch | 4.4 |
| 30 | Duplicated quote parsing | 4.5 |
| 31 | `find` completer after `-name` | 4.6 |
| 32 | Parity harness import coupling | 9.1 |
| 33 | Parity excluded from quality gates | 9.2 |
| 34 | Unused `PS1` | 4.7 |
| 35 | `Output` flushes every write | 4.7 |
| 36 | Unbounded shell history | 4.7 |
| 37 | `Mark.__hash__` contract | 6.5 |
| 38 | `C-u` ignored during prefix keymap | 6.2 |
| 39 | `truncate-lines` unused | 6.5 |
| 40 | `default_commands.py` monolith | 6.5 |
| 41 | Monkey-patched `Minibuffer.process_key` | 6.5 |
| 42 | Highlight cache uses `hash(line)` | 6.4 |
| 43 | `WindowTree.delete_window` cleanup | 6.5 |
| 44 | `Buffer._clamp_point` dead code | 6.5 |
| 45 | `ConnectionManager.broadcast` leaks | 5.5 |
| 46 | Module-level `logging.basicConfig` | 5.6 |
| 47 | `TerminalSession.mode` typed as `str` | 5.6 |
| 48 | `create_ollama_client` ignores timeout | 2.1 (config alignment) |
| 49 | `ServiceContainer.__repr__` | 2.1 |
| 50 | `LLMInterface.invoke` shadows `input` | 2.1 |
| 51 | Mutable `FileNode` returns | 3.2 |
| 52 | `handle_action` raises `KeyError` | 3.3 |
| 53 | `load_initial_filesystem` symlinks | 3.4 |
| 54 | `GameEventBus` only sync handlers | 2.1 |
| 55 | `OllamaClient` dead code | 2.1 |
| 56 | Frontend `ESC = ''` test constant | 7.3 |
| 57 | Hardcoded URL/theme/untyped theme | 7.3 |
| 58 | Missing readline bindings | 7.3 |
| 59 | `handleResize` after exit | 7.3 |
| 60 | `ResizeObserver` not debounced | 7.3 |
| Docs | Python version / layer mismatch | 10 |
| Docs | ARCHITECTURE/SHELL_DESIGN/V2_HANDOVER drift | 10 |
| Docs | BACKEND_CONVENTIONS snippet | 10 |
| Docs | AGENTS.md Pydantic/CHANGELOG/coverage | 10 |

---

## 13. Final Notes

- **No new features** should be added until these foundational issues are closed. The project's own rule — *"Don't add features beyond what's tested"* — applies doubly here.
- **All changes must pass:** `ruff check .`, `ruff format --check .`, `mypy`, `pytest`.
- **Every issue in this handover has a concrete acceptance criterion.** When all acceptance criteria are met, the review is fully addressed.
- If any section proves too large for a single PR, split it along subsystem boundaries (e.g., "Async persistence" PR, "Editor IEditorHost" PR) rather than mixing unrelated changes.
