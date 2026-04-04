"""
Editor modes — major and minor mode infrastructure.

A mode bundles a keymap, variable defaults, and lifecycle hooks into a
named, reusable unit.  Each buffer has exactly one major mode and zero
or more minor modes.

Keymap resolution order:
    buffer-local  >  minor-mode keymaps  >  major-mode keymap  >  global

Variable resolution order:
    buffer-local  >  minor-mode variables  >  major-mode variables  >  global default

Built-in modes:
- ``fundamental-mode`` — the default, no special behaviour
- ``text-mode`` — sets ``auto-fill`` to True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor
    from recursive_neon.editor.keymap import Keymap


@dataclass
class Mode:
    """Describes a major or minor mode."""

    name: str
    is_major: bool = True
    keymap: Keymap | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    on_enter: Callable[[Editor], None] | None = None
    on_exit: Callable[[Editor], None] | None = None
    doc: str = ""


# Global registry: mode name -> Mode
MODES: dict[str, Mode] = {}


def defmode(
    name: str,
    *,
    is_major: bool = True,
    keymap: Keymap | None = None,
    variables: dict[str, Any] | None = None,
    on_enter: Callable[[Editor], None] | None = None,
    on_exit: Callable[[Editor], None] | None = None,
    doc: str = "",
) -> Mode:
    """Register a new mode and return it."""
    mode = Mode(
        name=name,
        is_major=is_major,
        keymap=keymap,
        variables=variables or {},
        on_enter=on_enter,
        on_exit=on_exit,
        doc=doc,
    )
    MODES[name] = mode
    return mode


# ═══════════════════════════════════════════════════════════════════════
# Built-in modes
# ═══════════════════════════════════════════════════════════════════════

defmode(
    "fundamental-mode",
    doc="The default major mode with no special behaviour.",
)

defmode(
    "text-mode",
    variables={"auto-fill": True},
    doc="Major mode for editing plain text.  Enables auto-fill by default.",
)
