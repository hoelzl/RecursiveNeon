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
- ``text-mode`` — major mode for plain text (auto-fill is a separate
  minor mode, not enabled by default — matching GNU Emacs)

Language modes (Python, Markdown, shell) live in sub-modules and are
registered on import via :func:`register_language_modes`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor
    from recursive_neon.editor.keymap import Keymap


# ═══════════════════════════════════════════════════════════════════════
# Core types
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SyntaxRule:
    """A single syntax highlighting rule.

    *pattern* is compiled once; *face* is a face name resolved at render
    time via :func:`~recursive_neon.editor.faces.resolve_face`.
    """

    pattern: re.Pattern[str]
    face: str


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
    indicator: str = ""  # short modeline string; falls back to name if empty
    syntax_rules: list[SyntaxRule] = field(default_factory=list)
    # Minimum width of the buffer name in the modeline. GNU Emacs's
    # default ``mode-line-buffer-identification`` is ``%12b``; some modes
    # widen it — dired uses ``%17b`` (verified against Emacs 29.3).
    buffer_id_width: int = 12
    # Per-mode TAB behaviour (Emacs's ``indent-line-function``). When set,
    # ``indent-for-tab-command`` calls it instead of the text-mode default
    # (``indent-relative``). python-mode uses it for syntactic indentation.
    indent_line_function: Callable[[Editor], None] | None = None


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
    indicator: str = "",
    syntax_rules: list[SyntaxRule] | None = None,
    indent_line_function: Callable[[Editor], None] | None = None,
    buffer_id_width: int = 12,
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
        indicator=indicator,
        syntax_rules=syntax_rules or [],
        indent_line_function=indent_line_function,
        buffer_id_width=buffer_id_width,
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
    doc="Major mode for editing plain text.",
)
# Note: GNU Emacs's text-mode does NOT enable auto-fill by default — it is a
# separate minor mode (M-x auto-fill-mode, or text-mode-hook). So no
# ``auto-fill`` variable here; ``.txt`` buffers start with it off.

defmode(
    "auto-fill-mode",
    is_major=False,
    variables={"auto-fill": True},
    doc="Automatically break lines at fill-column during typing.",
    indicator="Fill",
)

defmode(
    "help-mode",
    doc="Major mode for ``*Help*`` buffers (read-only documentation).",
)

defmode(
    "isearch-mode",
    is_major=False,
    doc="Minor mode that's active while incremental search is running.",
    indicator="Isearch",
)

defmode(
    "eldoc-mode",
    is_major=False,
    doc=(
        "Minor-mode lighter for ElDoc. GNU Emacs enables eldoc-mode in "
        "python-mode (modeline reads ``(Python ElDoc)``); neon-edit shows the "
        "lighter but does not yet implement the echo-area documentation."
    ),
    indicator="ElDoc",
)

defmode(
    "completion-list-mode",
    doc="Major mode for ``*Completions*`` buffers; modeline reads ``(Completion List)``.",
    indicator="Completion List",
)

defmode(
    "buffer-menu-mode",
    doc="Major mode for the ``*Buffer List*`` buffer; modeline reads ``(Buffer Menu)``.",
    indicator="Buffer Menu",
)


# ═══════════════════════════════════════════════════════════════════════
# Auto-mode detection
# ═══════════════════════════════════════════════════════════════════════

# Extension → mode-name mapping (Emacs: auto-mode-alist).
# Populated by language mode modules when they register.
AUTO_MODE_ALIST: dict[str, str] = {
    # Text files use text-mode in GNU Emacs.
    ".txt": "text-mode",
    ".text": "text-mode",
}


def detect_mode(filepath: str) -> str:
    """Return the mode name for *filepath* based on its extension.

    Falls back to ``"fundamental-mode"`` if no match is found.
    """
    dot = filepath.rfind(".")
    if dot >= 0:
        ext = filepath[dot:]
        mode = AUTO_MODE_ALIST.get(ext)
        if mode is not None:
            return mode
    return "fundamental-mode"


def register_language_modes() -> None:
    """Import all built-in language modes, populating MODES and AUTO_MODE_ALIST."""
    import recursive_neon.editor.modes.markdown_mode  # noqa: F401
    import recursive_neon.editor.modes.python_mode  # noqa: F401
    import recursive_neon.editor.modes.sh_mode  # noqa: F401
