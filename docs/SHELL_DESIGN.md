# Shell Design Document

> **Status**: Phases 1-2 implemented. Design document kept for architecture reference.
> **Date**: 2026-03-23 (updated 2026-03-24)

## 1. Overview

The shell is the primary interface to Recursive://Neon. It runs in any terminal via `python -m recursive_neon.shell` and provides a Unix-like command-line experience over the virtual filesystem. Programs like `chat`, `note`, and `task` are standalone executables launched by the shell, not features baked into it.

The shell is **Layer 2** in the V2 architecture:

```
Layer 1: Application Core (Python)     ← exists (AppService, NPCManager, etc.)
Layer 2: CLI Interface (Python)        ← THIS DOCUMENT
Layer 3: Terminal Emulator (Browser)   ← future
Layer 4: Desktop GUI (Browser)         ← future
```

### Design goals

- **Real terminal, real experience.** The shell should feel like SSHing into a remote system. ANSI colors, tab completion, history, a polished prompt.
- **Builtins vs programs.** Like a real Unix shell, only commands that *must* modify shell state (e.g., `cd`) are builtins. Everything else — including `ls`, `cat`, `chat` — is a standalone program with a restricted interface. This models real system behavior and opens the door for player-written scripts.
- **Testable without a human.** Every command can be driven programmatically. Claude Code can play the game.
- **Output abstraction.** Programs write to an `Output` object, not directly to stdout. This lets us later pipe the same output through a WebSocket to the browser terminal (Layer 3) without changing any program code.
- **Two input modes.** Cooked mode (line-edited shell) and raw mode (future TUI apps/minigames get raw keystrokes). Only cooked mode is implemented in Phase 1.

## 2. Package Structure

```
backend/src/recursive_neon/shell/
├── __init__.py
├── __main__.py          # Entry point: python -m recursive_neon.shell
├── session.py           # ShellSession: cwd, env vars, prompt, path resolution
├── shell.py             # REPL loop using prompt_toolkit
├── parser.py            # Command-line tokenizer (quoting, escaping)
├── output.py            # Output abstraction (ANSI helpers, write/error/table)
├── path_resolver.py     # Virtual path → FileNode resolution
├── builtins.py          # Shell builtins (cd, exit, export)
└── programs/
    ├── __init__.py      # ProgramRegistry + Program protocol + ProgramContext
    ├── filesystem.py    # ls, pwd, cat, mkdir, touch, rm, cp, mv, grep, find, write
    ├── utility.py       # help, clear, echo, env, whoami, hostname, date, save
    ├── chat.py          # chat <npc> — NPC conversation mode with /commands
    ├── notes.py         # note list/show/create/edit/delete
    └── tasks.py         # task lists/list/add/done/undone/delete
```

## 3. Builtins vs Programs

This is the central architectural decision: **what is built into the shell, and what is an external program?**

### 3.1 The Distinction

In a real Unix shell, `cd` is a builtin because it must modify the shell's own working directory — an external process can't do that. But `ls`, `cat`, and `grep` are external programs. They receive arguments, read stdin, write to stdout, and return an exit code. They cannot change the shell's state.

We follow the same model:

| Category | What it can access | Examples |
|----------|-------------------|----------|
| **Shell builtins** | Full `ShellSession` — can modify cwd, env vars, aliases, history | `cd`, `exit`, `export`, `alias`, `source`, `history` |
| **System programs** | Restricted `ProgramContext` — args, I/O, env (read-only copy), services | `ls`, `cat`, `chat`, `note`, `mkdir`, `rm`, `help`, `echo` |
| **User scripts** *(Phase 2+)* | Same `ProgramContext` — `.py` files stored in the virtual filesystem | Player-written scripts, NPC-given tools |

### 3.2 Why This Matters

- **It models how real systems work**, which fits the game narrative perfectly (you've SSHed into a remote server).
- **Player-written programs** become a natural gameplay mechanic ("write a script to crack the password database"). The `ProgramContext` interface is the same whether the program is a shipped Python module or a player's `.py` file in `/usr/local/bin/`.
- **NPCs can give you programs** that you place in the filesystem and run.
- **Discovery during gameplay** — finding a hidden `portscan.py` in a directory is more interesting when you can actually execute it.
- **Security boundary** — programs cannot mutate shell state, which prevents bugs and makes reasoning about the system easier.

### 3.3 Command Resolution Order

When the user types a command, the shell resolves it in this order:

```
1. Shell builtins           (cd, exit, export, alias, source, history)
2. System programs          (registered Python modules — ls, cat, chat, etc.)
3. Virtual filesystem PATH  (Phase 2+ — executable .py files on PATH)
```

If nothing matches: `nsh: command not found: <name>` (exit code 127).

In Phase 2, the `PATH` environment variable (e.g., `/bin:/usr/local/bin`) will be checked for executable files. This is not implemented in Phase 1 — system programs are sufficient.

## 4. Component Design

### 4.1 ShellSession (`session.py`)

Holds all mutable state for a shell session. One session per running shell instance.

```python
class ShellSession:
    container: ServiceContainer     # Access to all services via DI
    cwd_id: str                     # Current working directory (FileNode UUID)
    env: dict[str, str]             # Virtual environment variables
    last_exit_code: int             # Exit code of last command (for prompt)
    username: str                   # "user" (could become player name)
    hostname: str                   # "neon-proxy" (thematic)

    # Path resolution
    def resolve_path(self, path: str) -> FileNode: ...
    def resolve_parent_and_name(self, path: str) -> tuple[FileNode, str]: ...
    def get_node_path(self, node: FileNode) -> str: ...
    def get_cwd_path(self) -> str: ...
```

**Path resolution** is the critical bridge between the user-facing path strings and the UUID-based virtual filesystem. See [Section 6](#6-path-resolution--detailed-design) for the full algorithm.

#### Environment Variables

Predefined virtual env vars:

| Variable | Value | Purpose |
|----------|-------|---------|
| `USER` | `"user"` | Current user identity |
| `HOME` | `"/"` | Home directory path |
| `HOSTNAME` | `"neon-proxy"` | System hostname (thematic) |
| `SHELL` | `"/bin/nsh"` | Shell name |
| `TERM` | `"neon-256color"` | Terminal type |
| `PATH` | `"/bin:/usr/local/bin"` | Program search path (Phase 2 — cosmetic for now) |
| `PS1` | (see prompt) | Prompt format |

These are cosmetic — they make `env` output look authentic and feed the game narrative ("you've SSHed into a compromised proxy server").

### 4.2 Shell Builtins (`builtins.py`)

Builtins are a small set of commands that **must** modify shell session state. They receive the full `ShellSession`.

```python
BuiltinFn = Callable[[ShellSession, list[str], Output], Awaitable[int]]
```

**Phase 1 builtins:**

| Builtin | Purpose | Why it must be a builtin |
|---------|---------|--------------------------|
| `cd [path]` | Change working directory | Modifies `session.cwd_id` |
| `exit [code]` | Exit the shell | Terminates the REPL loop |
| `export VAR=val` | Set environment variable | Modifies `session.env` |

**Future builtins** (Phase 2+): `alias`, `unalias`, `source`, `history`.

### 4.3 Program Protocol (`programs/__init__.py`)

Programs are standalone executables with a restricted interface. They cannot modify shell state.

```python
@dataclass
class ProgramContext:
    args: list[str]              # argv-style (args[0] is program name)
    stdout: Output               # Standard output
    stderr: Output               # Standard error
    env: dict[str, str]          # Environment variables (read-only copy)
    services: ServiceContainer   # Access to AppService, NPCManager, etc.
    cwd_id: str                  # Current working directory UUID (read-only)
    # Note: NO ShellSession reference — programs cannot modify shell state.

    # Convenience: path resolution (delegates to AppService + cwd_id)
    def resolve_path(self, path: str) -> FileNode: ...

class Program(Protocol):
    """Interface for all executable programs."""
    async def run(self, ctx: ProgramContext) -> int: ...

class ProgramRegistry:
    """Maps program names to Program implementations."""
    _programs: dict[str, Program]
    _help: dict[str, str]

    def register(self, name: str, program: Program, help_text: str) -> None: ...
    def get(self, name: str) -> Program | None: ...
    def list_programs(self) -> list[str]: ...
    def get_help(self, name: str) -> str | None: ...
```

Programs return an `int` exit code (0 = success, nonzero = error). This mirrors Unix convention.

#### Why the Program protocol uses a class

Unlike builtins (which are simple enough to be functions), programs benefit from being classes because:
- Some programs (like `chat`) have complex setup/teardown (entering a sub-REPL, connecting to Ollama).
- Programs can carry metadata (help text, argument specs for completion hints).
- The `Program` protocol makes it trivial to add user scripts later — a `ScriptRunner` class wraps a `.py` file and exposes the same interface.

However, for simple programs like `pwd` or `whoami`, a lightweight `FunctionProgram` adapter wraps a plain function into the `Program` protocol:

```python
class FunctionProgram:
    """Wraps a simple async function as a Program."""
    def __init__(self, fn: Callable[[ProgramContext], Awaitable[int]]):
        self._fn = fn

    async def run(self, ctx: ProgramContext) -> int:
        return await self._fn(ctx)
```

### 4.4 Output Abstraction (`output.py`)

```python
class Output:
    def write(self, text: str) -> None: ...
    def writeln(self, text: str = "") -> None: ...
    def error(self, text: str) -> None: ...      # Writes to stderr, red color
    def table(self, rows: list[list[str]], headers: list[str] | None = None) -> None: ...
    def styled(self, text: str, **styles) -> str: ...  # Bold, color, etc.
```

For the CLI, `Output` wraps `sys.stdout`/`sys.stderr` with ANSI escape codes. For the future browser terminal (Layer 3), a `WebSocketOutput` subclass will send structured messages instead.

#### ANSI Color Palette

Consistent with the cyberpunk theme:

| Element | Color | ANSI |
|---------|-------|------|
| Directories | Cyan | `\033[36m` |
| Executable/special files | Green | `\033[32m` |
| Errors | Red | `\033[31m` |
| Prompts/emphasis | Magenta/Bold | `\033[35m` / `\033[1m` |
| NPC names | Yellow | `\033[33m` |
| Timestamps/meta | Dim | `\033[2m` |

### 4.5 Parser (`parser.py`)

Tokenizes a raw input line into argv-style arguments, handling:

- **Quoting**: `cat "my file.txt"` → `["cat", "my file.txt"]`
- **Single quotes**: `echo 'hello world'` → `["echo", "hello world"]`
- **Escape sequences**: `cat my\ file.txt` → `["cat", "my file.txt"]`
- **No pipes/redirects in Phase 1.** These can be added later, but the parser should be designed to not break when we do.

The parser is deliberately simple — we're not building bash. We just need correct tokenization of quoted arguments, since the virtual filesystem allows filenames with spaces and special characters.

```python
def tokenize(line: str) -> list[str]: ...
```

### 4.6 Shell REPL (`shell.py`)

Uses `prompt_toolkit` for the interactive loop. Reasons for choosing `prompt_toolkit` over `readline`:

1. **Cross-platform**: Works on Windows without pyreadline hacks.
2. **Async-native**: `prompt_toolkit` has `PromptSession` with async support, which we need for NPC chat (Ollama calls are async).
3. **Rich completion**: Custom completers for file paths and command names.
4. **Future-proof**: Supports full-screen TUI apps (for Phase 2 raw mode).

```python
class Shell:
    session: ShellSession
    builtins: dict[str, BuiltinFn]
    programs: ProgramRegistry
    prompt_session: PromptSession

    async def run(self) -> None:
        """Main REPL loop."""
        # 1. Initialize services (filesystem, default NPCs)
        # 2. Print welcome banner
        # 3. Loop: prompt → parse → dispatch → repeat
        # 4. Handle Ctrl+C (cancel current line), Ctrl+D (exit)

    async def execute_line(self, line: str) -> int:
        """Parse and execute a single command line. Returns exit code."""
        tokens = tokenize(line)
        if not tokens:
            return 0
        name = tokens[0]

        # 1. Check builtins
        if name in self.builtins:
            return await self.builtins[name](self.session, tokens, self.output)

        # 2. Check system programs
        program = self.programs.get(name)
        if program is not None:
            ctx = ProgramContext(
                args=tokens,
                stdout=self.output,
                stderr=self.output,  # Could be separate in future
                env=dict(self.session.env),  # Read-only copy
                services=self.session.container,
                cwd_id=self.session.cwd_id,
            )
            return await program.run(ctx)

        # 3. Future: check PATH for executable scripts

        self.output.error(f"nsh: command not found: {name}")
        return 127
```

#### Prompt Format

```
user@neon-proxy:/Documents$ _
```

Components: `{username}@{hostname}:{cwd_path}$ `. Colored: username in green, `@` dim, hostname in cyan, `:` dim, path in bold, `$` in magenta.

If the last command failed (exit code != 0), the `$` turns red.

#### Welcome Banner

```
╔══════════════════════════════════════════════════╗
║  Recursive://Neon                                ║
║  Connection established to neon-proxy            ║
║  Type 'help' for available commands              ║
╚══════════════════════════════════════════════════╝
```

### 4.7 Tab Completion

Three completers, composed:

1. **Builtin completer**: Completes builtin names when the cursor is at the first word.
2. **Program completer**: Completes system program names when the cursor is at the first word.
3. **Path completer**: Completes file/directory names for subsequent arguments. Walks the virtual filesystem (not the real one).

In Phase 2, the path completer also checks PATH directories for executable scripts when completing the first word.

```python
class ShellCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if " " not in text:
            # Complete builtin names + program names
            yield from builtin_completions(text, self.builtins)
            yield from program_completions(text, self.programs)
            # Phase 2: yield from path_executable_completions(text, self.session)
        else:
            # Complete file paths for arguments
            yield from path_completions(text, self.session)
```

### 4.8 Entry Point (`__main__.py`)

```python
"""Entry point: python -m recursive_neon.shell"""

import asyncio
from recursive_neon.shell.shell import Shell

def main():
    shell = Shell()
    asyncio.run(shell.run())

if __name__ == "__main__":
    main()
```

## 5. Programs

### 5.1 Filesystem Programs (`programs/filesystem.py`)

| Program | Syntax | Description |
|---------|--------|-------------|
| `pwd` | `pwd` | Print current working directory path |
| `ls` | `ls [path]` | List directory contents (colorized, dirs first) |
| `cat` | `cat <file> [file...]` | Print file contents |
| `mkdir` | `mkdir <path>` | Create directory (with `-p` for parents) |
| `touch` | `touch <path>` | Create empty file (or update timestamp) |
| `rm` | `rm <path>` | Remove file or directory (`-r` for recursive) |
| `cp` | `cp <src> <dest>` | Copy file or directory |
| `mv` | `mv <src> <dest>` | Move/rename file or directory |
| `grep` | `grep [-i] <pattern> [path...]` | Search file contents (regex, recursive) |
| `find` | `find [path] -name <pattern>` | Find files by name (glob matching) |
| `write` | `write <file> [content...]` | Write content to a file (create or overwrite) |

Note: `cd` is a **builtin**, not a program (it modifies `session.cwd_id`).

**`ls` output format:**

```
user@neon-proxy:/$ ls
Documents/    Pictures/    Projects/
My Folder/    welcome.txt
```

Directories in cyan with trailing `/`, files in default color. Sorted: directories first, then files, alphabetical within each group.

With `-l` flag (long format):

```
user@neon-proxy:/$ ls -l
drwx  2025-03-23 14:00  Documents/
drwx  2025-03-23 14:00  My Folder/
drwx  2025-03-23 14:00  Pictures/
drwx  2025-03-23 14:00  Projects/
-rw-  2025-03-23 14:00  welcome.txt
```

### 5.2 Utility Programs (`programs/utility.py`)

| Program | Syntax | Description |
|---------|--------|-------------|
| `help` | `help [command]` | List builtins + programs, or show detailed help for one |
| `clear` | `clear` | Clear terminal screen |
| `echo` | `echo [text...]` | Print text (supports `$VAR` expansion) |
| `env` | `env` | Print all environment variables |
| `whoami` | `whoami` | Print current username |
| `hostname` | `hostname` | Print system hostname |
| `date` | `date` | Print current date/time (in-game or real) |
| `save` | `save` | Save game state (filesystem, notes, tasks, NPCs) to disk |

Note: `exit` and `export` are **builtins**, not programs.

### 5.3 Chat Program (`programs/chat.py`)

```
user@neon-proxy:/$ chat
Available NPCs:
  cipher   - The cryptic informant
  proxy    - The system administrator
  echo     - The memory fragment

user@neon-proxy:/$ chat cipher
Connecting to cipher...
cipher> Hey, what do you know about the system breach?

[cipher]: Ah, you're asking the right questions. But are you
ready for the answers? The breach wasn't from outside...

cipher> exit
Connection closed.
user@neon-proxy:/$
```

The `chat` program enters a sub-REPL with its own prompt (`{npc_name}> `). The NPC response is rendered with the NPC's name colored. `exit` or Ctrl+D returns to the main shell.

Internally, `chat` uses `services.npc_manager.chat(npc_id, message, player_id)` from its `ProgramContext`, which is async (Ollama HTTP call).

`chat` is a good example of why the `Program` class is useful — it manages its own REPL loop and cleanup, but it still can't touch the shell's state.

Chat also supports slash commands: `/help`, `/relationship`, `/status`. These are handled within the chat sub-REPL (prefixed with `/` to distinguish from messages to the NPC).

### 5.4 Note Program (`programs/notes.py`)

| Subcommand | Syntax | Description |
|------------|--------|-------------|
| `note list` | `note list` | List all notes with index, title, preview |
| `note show` | `note show <ref>` | Show full note (by 1-based index or UUID prefix) |
| `note create` | `note create <title> [-c <content>]` | Create a note |
| `note edit` | `note edit <ref> [-t <title>] [-c <content>]` | Update a note |
| `note delete` | `note delete <ref>` | Delete a note |

Aliases: `ls` for `list`, `new` for `create`, `rm` for `delete`.

### 5.5 Task Program (`programs/tasks.py`)

| Subcommand | Syntax | Description |
|------------|--------|-------------|
| `task lists` | `task lists` | List all task lists with completion counts |
| `task list` | `task list [name]` | Show tasks in a list (defaults to single/default list) |
| `task add` | `task add <title> [--list <name>]` | Add a task (auto-creates "default" list) |
| `task done` | `task done <ref>` | Mark task as complete |
| `task undone` | `task undone <ref>` | Mark task as incomplete |
| `task delete` | `task delete <ref>` | Delete a task |

Tasks are referenced by 1-based index within their list, or by UUID prefix.

## 6. Path Resolution — Detailed Design

This is the most important piece of the shell, as it bridges human-readable paths and the UUID-based filesystem.

### 6.1 Terminology

- **Absolute path**: Starts with `/`. Resolved from root.
- **Relative path**: Does not start with `/`. Resolved from cwd.
- **Path segments**: Components between `/` separators.
- **Node**: A `FileNode` in the virtual filesystem (identified by UUID).

### 6.2 Resolution Rules

```
resolve_path("/Documents/readme.txt")
  1. Start at root (filesystem.root_id)
  2. "Documents" → find child of root with name "Documents" → UUID-abc
  3. "readme.txt" → find child of UUID-abc with name "readme.txt" → UUID-def
  4. Return FileNode(id=UUID-def)

resolve_path("../Pictures")  (cwd = /Documents)
  1. Start at cwd (UUID-abc, which is /Documents)
  2. ".." → parent_id of UUID-abc → root UUID
  3. "Pictures" → find child of root with name "Pictures" → UUID-ghi
  4. Return FileNode(id=UUID-ghi)
```

### 6.3 Where Path Resolution Lives

Path resolution needs to be available to both builtins and programs:

- **Builtins** access it via `ShellSession.resolve_path()`.
- **Programs** access it via `ProgramContext.resolve_path()`, which delegates to the same underlying logic using the read-only `cwd_id` snapshot.

The resolution logic itself is a standalone function (not a method on `ShellSession`) so that `ProgramContext` can reuse it without depending on the session:

```python
def resolve_path(
    path: str,
    cwd_id: str,
    app_service: AppService,
) -> FileNode:
    """Resolve a path string to a FileNode."""
    ...
```

Both `ShellSession.resolve_path()` and `ProgramContext.resolve_path()` are thin wrappers around this function.

### 6.4 Error Handling

Path resolution produces clear error messages:

- `FileNotFoundError("No such file or directory: /Documents/nonexistent")` — when a path segment doesn't match any child.
- `NotADirectoryError("Not a directory: /welcome.txt")` — when traversing through a file as if it were a directory.
- Programs catch these and print user-friendly errors via `ctx.stderr.error()`.

### 6.5 Performance Note

The current `AppService.list_directory()` does O(n) scans over all nodes. For the initial filesystem (~20 nodes), this is fine. If the filesystem grows large (hundreds of nodes), we should add an index (`dict[str, list[str]]` mapping parent_id to child_ids) in `AppService`. This is a future optimization, not a Phase 1 concern.

## 7. Initialization Flow

When the shell starts (`Shell.run()`):

```
1. Create ServiceContainer via ServiceFactory
   (initializes GameState, AppService, NPCManager, etc.)

2. Load all saved state from game_data/:
   a. AppService.load_filesystem_from_disk()
      → If no saved state, load_initial_filesystem() from initial_fs/
   b. AppService.load_notes_from_disk() (non-fatal if missing)
   c. AppService.load_tasks_from_disk() (non-fatal if missing)
   d. NPCManager.load_npcs_from_disk()
      → If no saved state, create_default_npcs()

3. Create ShellSession
   → cwd_id = filesystem root_id
   → env = default environment variables

4. Register builtins (cd, exit, export)

5. Create ProgramRegistry
   → Register programs from filesystem, utility, chat, notes, tasks

6. Create PromptSession with FileHistory (persistent) or InMemoryHistory

7. Print welcome banner

8. Enter REPL loop

9. On exit: auto-save all state to game_data/
```

## 8. Testing Strategy

### 8.1 Unit Tests

Each component is independently testable:

- **Path resolution**: Create a mock filesystem with known structure, test resolve_path with absolute, relative, `.`, `..`, nonexistent, and through-file paths.
- **Parser**: Test tokenization of quoted strings, escapes, edge cases.
- **Programs**: Create a `ProgramContext` with a test container and a captured `Output`, call `program.run(ctx)` directly. Assert on output text and exit code. Programs are easy to test because they have a well-defined restricted interface.
- **Builtins**: Test with a real `ShellSession` since they need to modify state. Assert on session state changes.

### 8.2 Integration Tests

- **Full command flow**: Initialize shell, run a sequence of commands (`mkdir /test`, `cd /test`, `touch foo.txt`, `cat foo.txt`, `ls`, `pwd`), verify state after each.
- **NPC chat**: With a mock LLM, verify the chat program sends messages and receives responses.

### 8.3 Test Fixtures

Extend `conftest.py` with:

```python
@pytest.fixture
def shell_session(test_container):
    """A ShellSession with initialized filesystem for testing."""
    test_container.app_service.load_initial_filesystem()
    return ShellSession(container=test_container)

@pytest.fixture
def program_context(test_container):
    """A ProgramContext for testing programs in isolation."""
    test_container.app_service.load_initial_filesystem()
    root_id = test_container.game_state.filesystem.root_id
    return ProgramContext(
        args=[],
        stdout=CapturedOutput(),
        stderr=CapturedOutput(),
        env={"USER": "test", "HOME": "/"},
        services=test_container,
        cwd_id=root_id,
    )

@pytest.fixture
def captured_output():
    """An Output that captures to a buffer for assertion."""
    return CapturedOutput()
```

## 9. Dependencies

### New Python Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| `prompt_toolkit` | Interactive REPL, completion, key bindings | Well-maintained, no transitive bloat |

No other new dependencies needed. ANSI colors are handled with raw escape codes (no `colorama` or `rich` needed for Phase 1).

### Existing Dependencies Used

- `AppService` — filesystem, notes, tasks CRUD
- `NPCManager` — NPC chat
- `ServiceContainer` / `ServiceFactory` — DI wiring
- `GameState`, `FileNode`, etc. — data models

## 10. Virtual I/O Layer (Phase 2 — Design Now, Build Later)

User scripts need to interact with the virtual filesystem using familiar Python APIs like `open()`, `os.path.exists()`, and `os.listdir()`. This section describes the virtual I/O layer that makes this possible.

**This does not require any changes to the existing `FileNode` model or `AppService`.** The virtual I/O layer sits on top of the existing infrastructure, using path resolution and `AppService` CRUD operations.

### 10.1 VirtualFile — File-Like Object

`VirtualFile` wraps a `FileNode`'s content in a standard Python file-like interface (`io.TextIOBase` for text, `io.RawIOBase` for binary). Reads come from an in-memory buffer loaded on open. Writes accumulate in the buffer and flush to `AppService.update_file()` on close.

```python
# shell/virtual_io.py

class VirtualFile(io.TextIOBase):
    """File-like object backed by a FileNode."""

    def __init__(self, node_id: str, mode: str, app_service: AppService, content: str):
        self._node_id = node_id
        self._mode = mode
        self._app_service = app_service
        self._buffer = io.StringIO(content)
        self._dirty = False

    def read(self, size: int = -1) -> str:
        return self._buffer.read(size)

    def write(self, s: str) -> int:
        self._dirty = True
        return self._buffer.write(s)

    def readline(self, limit: int = -1) -> str:
        return self._buffer.readline(limit)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._buffer.seek(offset, whence)

    def tell(self) -> int:
        return self._buffer.tell()

    def close(self) -> None:
        if self._dirty:
            self._app_service.update_file(
                self._node_id, {"content": self._buffer.getvalue()}
            )
        super().close()
```

A `VirtualBinaryFile(io.RawIOBase)` variant handles binary mode by decoding/encoding base64 content from/to `FileNode.content`.

### 10.2 virtual_open() — Drop-In open() Replacement

```python
def make_virtual_open(
    cwd_id: str,
    app_service: AppService,
) -> Callable:
    """Create a virtual open() function bound to a filesystem context."""

    def virtual_open(path: str, mode: str = "r", **kwargs) -> VirtualFile:
        binary = "b" in mode
        base_mode = mode.replace("b", "")

        if "r" in base_mode:
            node = resolve_path(path, cwd_id, app_service)
            if node.type == "directory":
                raise IsADirectoryError(f"Is a directory: '{path}'")
            content = node.content or ""
            if binary:
                return VirtualBinaryFile(node.id, mode, app_service, content)
            return VirtualFile(node.id, mode, app_service, content)

        elif "w" in base_mode:
            try:
                node = resolve_path(path, cwd_id, app_service)
                # Truncate: open with empty content
                return VirtualFile(node.id, mode, app_service, "")
            except FileNotFoundError:
                # Create new file
                parent, name = resolve_parent_and_name(path, cwd_id, app_service)
                node = app_service.create_file({
                    "name": name, "parent_id": parent.id
                })
                return VirtualFile(node.id, mode, app_service, "")

        elif "a" in base_mode:
            try:
                node = resolve_path(path, cwd_id, app_service)
                content = node.content or ""
            except FileNotFoundError:
                parent, name = resolve_parent_and_name(path, cwd_id, app_service)
                node = app_service.create_file({
                    "name": name, "parent_id": parent.id
                })
                content = ""
            vf = VirtualFile(node.id, mode, app_service, content)
            vf.seek(0, io.SEEK_END)  # Position at end for append
            return vf

        elif "x" in base_mode:
            try:
                resolve_path(path, cwd_id, app_service)
                raise FileExistsError(f"File exists: '{path}'")
            except FileNotFoundError:
                parent, name = resolve_parent_and_name(path, cwd_id, app_service)
                node = app_service.create_file({
                    "name": name, "parent_id": parent.id
                })
                return VirtualFile(node.id, mode, app_service, "")

        raise ValueError(f"Unsupported mode: '{mode}'")

    return virtual_open
```

### 10.3 Virtual os Module

Scripts expect `os.path.exists()`, `os.listdir()`, etc. We provide a virtual `os` module that delegates to the virtual filesystem:

```python
class VirtualPath:
    """Virtual replacement for os.path, backed by AppService."""

    def __init__(self, cwd_id: str, app_service: AppService):
        self._cwd_id = cwd_id
        self._app_service = app_service

    def exists(self, path: str) -> bool:
        try:
            resolve_path(path, self._cwd_id, self._app_service)
            return True
        except (FileNotFoundError, NotADirectoryError):
            return False

    def isfile(self, path: str) -> bool:
        try:
            node = resolve_path(path, self._cwd_id, self._app_service)
            return node.type == "file"
        except (FileNotFoundError, NotADirectoryError):
            return False

    def isdir(self, path: str) -> bool:
        try:
            node = resolve_path(path, self._cwd_id, self._app_service)
            return node.type == "directory"
        except (FileNotFoundError, NotADirectoryError):
            return False

    def join(self, *parts: str) -> str:
        return "/".join(parts).replace("//", "/")

    # basename, dirname, splitext — pure string operations, delegate to posixpath


class VirtualOS:
    """Virtual replacement for os, backed by AppService."""

    def __init__(self, cwd_id: str, app_service: AppService):
        self.path = VirtualPath(cwd_id, app_service)
        self._cwd_id = cwd_id
        self._app_service = app_service

    def listdir(self, path: str = ".") -> list[str]:
        node = resolve_path(path, self._cwd_id, self._app_service)
        children = self._app_service.list_directory(node.id)
        return [child.name for child in children]

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        # Walk path segments, creating directories as needed
        ...

    def remove(self, path: str) -> None:
        node = resolve_path(path, self._cwd_id, self._app_service)
        if node.type == "directory":
            raise IsADirectoryError(f"Is a directory: '{path}'")
        self._app_service.delete_file(node.id)

    def getcwd(self) -> str:
        return get_node_path(self._cwd_id, self._app_service)
```

### 10.4 Script Sandbox

When the `ScriptRunner` executes a user script, it injects virtual I/O into the script's globals:

```python
class ScriptRunner(Program):
    """Runs a .py file from the virtual filesystem as a program."""

    def __init__(self, script_node: FileNode):
        self.script_node = script_node

    async def run(self, ctx: ProgramContext) -> int:
        app_service = ctx.services.app_service
        virtual_os = VirtualOS(ctx.cwd_id, app_service)

        script_globals = {
            # Override builtins
            "open": make_virtual_open(ctx.cwd_id, app_service),
            "print": lambda *args, **kw: ctx.stdout.writeln(" ".join(str(a) for a in args)),
            "input": ...,  # Read from ctx.stdin

            # Virtual modules
            "os": virtual_os,

            # Script metadata
            "__name__": "__main__",
            "argv": ctx.args,

            # Safe builtins (math, strings, collections, etc.)
            "__builtins__": _make_safe_builtins(),
        }

        try:
            exec(compile(self.script_node.content, self.script_node.name, "exec"), script_globals)
            return 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        except Exception as e:
            ctx.stderr.error(f"{type(e).__name__}: {e}")
            return 1
```

**Design notes:**
- `open()` is replaced with `virtual_open()` — scripts use standard Python file I/O syntax and it transparently operates on the virtual filesystem.
- `print()` routes to `ctx.stdout` — output goes through the Output abstraction.
- `os` is replaced with `VirtualOS` — `os.path.exists()`, `os.listdir()`, etc. work on the virtual filesystem.
- `__builtins__` is restricted to safe operations (no `__import__`, no `eval` on arbitrary code, no `exec`). The exact safe set is a Phase 2 design decision.
- `SystemExit` is caught so scripts can call `sys.exit(0)` without killing the shell.

**Thematic note on sandboxing:** The game narrative is about hacking into a system. The sandbox isn't about protecting the player's real machine (they're the one running the game) — it's about making the virtual system feel real. If a player cleverly breaks out of the sandbox, that's arguably an easter egg, not a security flaw. Still, a reasonable sandbox prevents accidental real-filesystem access.

### 10.5 What This Means for Phase 1

No changes to `FileNode`, `AppService`, or any existing code. The decisions that matter for Phase 1 are:

1. **Path resolution as a standalone function** — already designed in Section 6.3. This is shared by `ShellSession`, `ProgramContext`, and (later) `virtual_open()`.
2. **`ProgramContext` does not expose `ShellSession`** — this boundary is what makes it safe to pass the same interface to user scripts.
3. **`Output` abstraction** — `print()` override routes through it, keeping script output capturable and redirectable.

These are all already in the Phase 1 design. The virtual I/O layer adds no new requirements to Phase 1 — it validates that the current design is sound.

### 10.6 Future: FileNode Permissions

When user scripts land, we'll need to distinguish executable from non-executable files. Options (decide in Phase 2):

- **`permissions: str = "rw-"`** field on `FileNode` — most thematic, mimics `ls -l` output
- **`executable: bool = False`** field — simplest
- **Convention-based** — `.py` extension = executable (no schema change)

This is a small addition to `FileNode`, not a redesign.

## 11. Future Extensibility (Phases 2-3)

### 11.1 Pipes and Redirects

The parser can be extended to recognize `|`, `>`, `<` tokens. Program output already goes through `Output`, which can be redirected. Pipes would create an `Output` → `Input` bridge between two programs.

### 11.2 Raw Mode / TUI Apps

`prompt_toolkit` supports full-screen applications. A future TUI program (minigame, text editor) would signal the shell to enter raw mode, take over the terminal, and return to cooked mode on exit.

### 11.3 WebSocket Transport

`Output` is abstract enough to be backed by a WebSocket. `ProgramContext` can be created per-connection on the server side. The `Shell` REPL loop would be replaced by a message handler that calls `execute_line()` per incoming message.

### 11.4 Additional System Programs

The following programs from Phase 2 are now implemented (see Sections 5.1, 5.4, 5.5):
- `note` — Notes CRUD
- `task` — Task management
- `grep` — Search file contents (regex)
- `find` — Find files by name pattern (glob)
- `write` — Write content to files
- `save` — Save game state to disk

Still planned for future phases:
| Program | Description |
|---------|-------------|
| `edit` | Simple text editor (TUI, raw mode — requires Phase 3 infrastructure) |
