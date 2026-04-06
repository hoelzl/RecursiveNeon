"""
Undo system — Emacs-style unlimited undo with boundary markers.

The undo list is a per-buffer stack of entries.  Each mutating
primitive pushes one or more entries.  ``UndoBoundary`` markers
separate command groups so that one ``undo()`` call reverses an
entire command's worth of changes.

Undo is itself undoable: performing an undo pushes new entries
that reverse the undo, so repeated undo walks further back, and
"undo the undo" (redo) falls out naturally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from recursive_neon.editor.text_attr import TextAttr


@dataclass(frozen=True)
class UndoInsert:
    """Records that text was inserted.  Undo = delete the range."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass(frozen=True)
class UndoDelete:
    """Records that text was deleted.  Undo = reinsert at position.

    The optional ``attrs`` field captures per-character attributes so
    that undo restores colours correctly.  Structure: a tuple of
    per-line attr tuples, parallel to ``text.split('\\n')``.
    """

    line: int
    col: int
    text: str
    attrs: tuple[tuple[TextAttr | None, ...], ...] | None = field(
        default=None, compare=False
    )


@dataclass(frozen=True)
class UndoCursorMove:
    """Records the cursor position before an operation.

    Undo restores point to this position after reversing the edit.
    """

    line: int
    col: int


@dataclass(frozen=True)
class UndoBoundary:
    """Separator between command groups.

    One undo invocation reverses everything back to the previous
    boundary (or the start of the undo list).
    """

    pass


UndoEntry = UndoInsert | UndoDelete | UndoCursorMove | UndoBoundary
