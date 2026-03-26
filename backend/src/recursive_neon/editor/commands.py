"""
Command system — named editing operations.

Commands are named functions registered in a global table.  Each
command takes an ``Editor`` instance and an optional prefix argument
(integer or None).  The ``@defcommand`` decorator handles registration.

This follows Hemlock's ``defcommand`` model: commands are the unit
of key binding and undo grouping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor

CommandFn = Callable[["Editor", int | None], None]


@dataclass
class Command:
    """A named editing command."""

    name: str
    function: CommandFn
    doc: str


# Global command registry
COMMANDS: dict[str, Command] = {}


def defcommand(name: str, doc: str = "") -> Callable[[CommandFn], CommandFn]:
    """Decorator to register a named editor command.

    Usage::

        @defcommand("forward-char", "Move point forward one character.")
        def forward_char(ed: Editor, prefix: int | None) -> None:
            n = prefix if prefix is not None else 1
            ed.buffer.forward_char(n)
    """

    def wrapper(fn: CommandFn) -> CommandFn:
        COMMANDS[name] = Command(name=name, function=fn, doc=doc)
        return fn

    return wrapper


def get_command(name: str) -> Command | None:
    """Look up a command by name."""
    return COMMANDS.get(name)
