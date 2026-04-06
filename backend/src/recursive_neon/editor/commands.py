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
    coalesce_key: str | None = None


# Global command registry
COMMANDS: dict[str, Command] = {}


def defcommand(
    name: str, doc: str = "", *, coalesce_key: str | None = None
) -> Callable[[CommandFn], CommandFn]:
    """Decorator to register a named editor command.

    *coalesce_key*: when non-``None``, consecutive commands that share
    the same key are coalesced into a single undo group.  For example,
    a run of ``delete-backward-char`` keystrokes becomes one undo step.

    Usage::

        @defcommand("forward-char", "Move point forward one character.")
        def forward_char(ed: Editor, prefix: int | None) -> None:
            n = prefix if prefix is not None else 1
            ed.buffer.forward_char(n)
    """

    def wrapper(fn: CommandFn) -> CommandFn:
        COMMANDS[name] = Command(
            name=name, function=fn, doc=doc, coalesce_key=coalesce_key
        )
        return fn

    return wrapper


def get_command(name: str) -> Command | None:
    """Look up a command by name."""
    return COMMANDS.get(name)
