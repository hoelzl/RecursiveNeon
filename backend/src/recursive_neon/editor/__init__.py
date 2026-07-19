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

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from recursive_neon.editor.ansi_parser import parse_ansi
from recursive_neon.editor.buffer import Buffer, ReadOnlyRegion
from recursive_neon.editor.commands import COMMANDS, Command, defcommand, get_command
from recursive_neon.editor.core import (
    CoreEditorFinished,
    CoreEditorFinishReason,
    CoreEditorFrame,
    CoreEditorNotQuiescent,
    CoreEditorPosition,
    CoreEditorSession,
    CoreEditorStep,
    EditorObservationV1,
    EditorObservationV1Dict,
    EditorPositionV1Dict,
    create_core_editor,
)
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.faces import FACES, face_reset, resolve_face
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.modes import MODES, Mode, SyntaxRule, defmode
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

if TYPE_CHECKING:
    from recursive_neon.editor.config_loader import ConfigNamespace, load_config
    from recursive_neon.editor.default_commands import build_default_keymap
    from recursive_neon.editor.shell_mode import (
        BufferOutput,
        ShellBufferInput,
        ShellState,
        setup_shell_buffer,
        strip_ansi,
    )

_LAZY_EXPORT_MODULES = {
    "BufferOutput": "recursive_neon.editor.shell_mode",
    "ConfigNamespace": "recursive_neon.editor.config_loader",
    "ShellBufferInput": "recursive_neon.editor.shell_mode",
    "ShellState": "recursive_neon.editor.shell_mode",
    "build_default_keymap": "recursive_neon.editor.default_commands",
    "load_config": "recursive_neon.editor.config_loader",
    "setup_shell_buffer": "recursive_neon.editor.shell_mode",
    "strip_ansi": "recursive_neon.editor.shell_mode",
}


def __getattr__(name: str) -> Any:
    """Load optional compatibility exports only when requested."""
    module_name = _LAZY_EXPORT_MODULES.get(name)
    if module_name is not None:
        value = getattr(import_module(module_name), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include lazy public exports in runtime introspection."""
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "Buffer",
    "BufferOutput",
    "COMMANDS",
    "Command",
    "ConfigNamespace",
    "CoreEditorFinished",
    "CoreEditorFinishReason",
    "CoreEditorFrame",
    "CoreEditorNotQuiescent",
    "CoreEditorPosition",
    "CoreEditorSession",
    "CoreEditorStep",
    "Editor",
    "EditorObservationV1",
    "EditorObservationV1Dict",
    "EditorPositionV1Dict",
    "EditorVariable",
    "Keymap",
    "KillRing",
    "FACES",
    "MODES",
    "Mark",
    "ReadOnlyRegion",
    "TextAttr",
    "parse_ansi",
    "Mode",
    "SyntaxRule",
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
    "create_core_editor",
    "defcommand",
    "defmode",
    "defvar",
    "face_reset",
    "resolve_face",
    "get_command",
    "load_config",
    "setup_shell_buffer",
    "strip_ansi",
]
