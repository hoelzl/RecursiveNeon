"""
Neon-edit: an Emacs-inspired text editor core.

This package contains the pure editor model — buffers, marks, text
manipulation primitives, and movement commands.  It has no I/O or TUI
dependencies and can be driven by any frontend (TUI, GUI, tests).

Architecture follows the Zwei → Hemlock → GNU Emacs lineage:
- Text stored as a list of line strings (Hemlock-style)
- Marks with left/right-inserting kinds (Hemlock)
- Named commands with prefix arg (Hemlock defcommand model)
- Unlimited undo via an undo list with boundaries (Emacs)
- Kill ring with consecutive-kill merging (Emacs)
"""

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.undo import (
    UndoBoundary,
    UndoCursorMove,
    UndoDelete,
    UndoEntry,
    UndoInsert,
)

__all__ = [
    "Buffer",
    "KillRing",
    "Mark",
    "UndoBoundary",
    "UndoCursorMove",
    "UndoDelete",
    "UndoEntry",
    "UndoInsert",
]
