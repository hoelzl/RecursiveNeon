"""
Neon-edit: an Emacs-inspired text editor core.

This package contains the pure editor model — buffers, marks, text
manipulation primitives, and movement commands.  It has no I/O or TUI
dependencies and can be driven by any frontend (TUI, GUI, tests).

Architecture follows the Zwei → Hemlock → GNU Emacs lineage:
- Text stored as a list of line strings (Hemlock-style)
- Marks with left/right-inserting kinds (Hemlock)
- Named commands with prefix arg (Hemlock defcommand model)
- Layered keymaps with prefix key support (Hemlock)
- Unlimited undo via an undo list with boundaries (Emacs)
- Kill ring with consecutive-kill merging (Emacs)
"""

from recursive_neon.editor.ansi_parser import parse_ansi
from recursive_neon.editor.buffer import Buffer, ReadOnlyRegion
from recursive_neon.editor.commands import COMMANDS, Command, defcommand, get_command
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.modes import MODES, Mode, defmode
from recursive_neon.editor.shell_mode import (
    BufferOutput,
    ShellBufferInput,
    ShellState,
    setup_shell_buffer,
    strip_ansi,
)
from recursive_neon.editor.text_attr import TextAttr
from recursive_neon.editor.undo import (
    UndoBoundary,
    UndoCursorMove,
    UndoDelete,
    UndoEntry,
    UndoInsert,
)
from recursive_neon.editor.variables import VARIABLES, EditorVariable, defvar
from recursive_neon.editor.viewport import Viewport
from recursive_neon.editor.window import (
    SplitDirection,
    Window,
    WindowSplit,
    WindowTree,
)

__all__ = [
    "Buffer",
    "BufferOutput",
    "COMMANDS",
    "Command",
    "Editor",
    "EditorVariable",
    "Keymap",
    "KillRing",
    "MODES",
    "Mark",
    "ReadOnlyRegion",
    "TextAttr",
    "parse_ansi",
    "Mode",
    "ShellBufferInput",
    "ShellState",
    "UndoBoundary",
    "UndoCursorMove",
    "UndoDelete",
    "UndoEntry",
    "UndoInsert",
    "VARIABLES",
    "Viewport",
    "Window",
    "WindowSplit",
    "WindowTree",
    "SplitDirection",
    "build_default_keymap",
    "defcommand",
    "defmode",
    "defvar",
    "get_command",
    "setup_shell_buffer",
    "strip_ansi",
]
