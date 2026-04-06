"""
Face definitions — named styles for syntax highlighting.

A *face* is a named visual style (like Emacs faces).  Each face maps
to an ANSI SGR escape sequence used by the rendering pipeline.

The ``FACES`` dict is the canonical registry.  Language modes reference
faces by name (e.g., ``"keyword"``, ``"string"``); the view layer
resolves them to ANSI sequences at render time.

Users can override faces via ``defvar`` (e.g.,
``defvar("face-keyword", "\\033[36m")``).  The lookup function
``resolve_face`` checks for a variable override before falling back
to the built-in default.
"""

from __future__ import annotations

from recursive_neon.editor.variables import VARIABLES

# Built-in face → ANSI escape mapping.
#
# Palette rationale: 256-colour indices for broad terminal support.
# The defaults aim for a dark-background theme (the common case for
# cyberpunk aesthetics) but every face can be overridden at runtime.

_RESET = "\033[0m"

FACES: dict[str, str] = {
    # Language constructs
    "keyword": "\033[1;38;5;204m",  # bold pinkish-red
    "builtin": "\033[38;5;81m",  # sky blue
    "string": "\033[38;5;114m",  # soft green
    "comment": "\033[3;38;5;245m",  # italic grey
    "number": "\033[38;5;209m",  # orange
    "decorator": "\033[38;5;141m",  # lavender
    "type": "\033[38;5;81m",  # sky blue (same as builtin)
    "constant": "\033[38;5;209m",  # orange (same as number)
    "function-name": "\033[38;5;81m",  # sky blue
    "variable-name": "\033[38;5;252m",  # bright white
    # Markup / prose
    "heading": "\033[1;38;5;81m",  # bold sky blue
    "bold": "\033[1m",  # bold
    "italic": "\033[3m",  # italic
    "code": "\033[38;5;114m",  # same as string
    "link": "\033[4;38;5;81m",  # underline sky blue
    # Shell
    "sh-variable": "\033[38;5;81m",  # sky blue
    "sh-redirect": "\033[38;5;204m",  # pinkish-red
}


def resolve_face(name: str) -> str:
    """Return the ANSI escape sequence for face *name*.

    Checks for a user override via the variable ``face-<name>`` first,
    then falls back to the built-in ``FACES`` dict.  Returns an empty
    string if the face is unknown.
    """
    var_name = f"face-{name}"
    var = VARIABLES.get(var_name)
    if var is not None:
        return str(var.default)
    return FACES.get(name, "")


def face_reset() -> str:
    """Return the ANSI reset sequence."""
    return _RESET
