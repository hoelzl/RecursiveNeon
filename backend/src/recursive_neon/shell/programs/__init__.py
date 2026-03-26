"""
Program registry, protocol, and context for shell programs.

Programs are standalone executables with a restricted interface.
They cannot modify shell state (cwd, env vars, aliases).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol

from recursive_neon.models.app_models import FileNode
from recursive_neon.shell.output import Output
from recursive_neon.shell.path_resolver import resolve_parent_and_name, resolve_path

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer
    from recursive_neon.shell.completion import CompletionFn


@dataclass
class ProgramContext:
    """Restricted execution context for programs.

    Programs receive this instead of ShellSession — they can read
    filesystem state and use services, but cannot modify shell state
    (cwd, env vars, etc.).
    """

    args: list[str]
    stdout: Output
    stderr: Output
    env: dict[str, str]
    services: ServiceContainer
    cwd_id: str
    builtin_help: dict[str, str] | None = None
    program_help: dict[str, str] | None = None
    get_line: Callable[..., Awaitable[str]] | None = None
    run_tui: Callable[[Any], Awaitable[int]] | None = None
    stdin: str | None = None

    def resolve_path(self, path: str) -> FileNode:
        """Resolve a path string to a FileNode."""
        return resolve_path(path, self.cwd_id, self.services.app_service)

    def resolve_parent_and_name(self, path: str) -> tuple[FileNode, str]:
        """Resolve all but the last path segment, returning (parent_dir, name)."""
        return resolve_parent_and_name(path, self.cwd_id, self.services.app_service)


class Program(Protocol):
    """Interface for all executable programs."""

    async def run(self, ctx: ProgramContext) -> int: ...


ProgramFn = Callable[[ProgramContext], Awaitable[int]]


class FunctionProgram:
    """Wraps a simple async function as a Program."""

    def __init__(self, fn: ProgramFn) -> None:
        self._fn = fn

    async def run(self, ctx: ProgramContext) -> int:
        return await self._fn(ctx)


@dataclass
class ProgramEntry:
    """A registered program with metadata."""

    program: Program
    help_text: str
    completer: CompletionFn | None = None


class ProgramRegistry:
    """Maps program names to Program implementations."""

    def __init__(self) -> None:
        self._programs: dict[str, ProgramEntry] = {}

    def register(
        self,
        name: str,
        program: Program,
        help_text: str,
        completer: CompletionFn | None = None,
    ) -> None:
        """Register a program by name."""
        self._programs[name] = ProgramEntry(
            program=program, help_text=help_text, completer=completer
        )

    def register_fn(
        self,
        name: str,
        fn: ProgramFn,
        help_text: str,
        completer: CompletionFn | None = None,
    ) -> None:
        """Register a plain async function as a program."""
        self._programs[name] = ProgramEntry(
            program=FunctionProgram(fn), help_text=help_text, completer=completer
        )

    def get(self, name: str) -> Program | None:
        """Look up a program by name."""
        entry = self._programs.get(name)
        return entry.program if entry else None

    def get_completer(self, name: str) -> CompletionFn | None:
        """Get the completion callback for a program."""
        entry = self._programs.get(name)
        return entry.completer if entry else None

    def list_programs(self) -> list[str]:
        """Return sorted list of registered program names."""
        return sorted(self._programs.keys())

    def get_help(self, name: str) -> str | None:
        """Get the help text for a program."""
        entry = self._programs.get(name)
        return entry.help_text if entry else None
