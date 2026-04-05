"""
Editor variables — typed, documented, buffer-overridable settings.

Each variable has a name, default value, documentation string, and a
Python type for validation.  Variables can be set globally or overridden
per-buffer (buffer-local).  The lookup cascade is:

    buffer-local  >  minor-mode defaults  >  major-mode defaults  >  global default

The ``defvar`` function registers a variable in the global ``VARIABLES``
registry.  Built-in variables (fill-column, tab-width, etc.) are
registered at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EditorVariable:
    """Metadata for a single editor variable."""

    name: str
    default: Any
    doc: str = ""
    type: type = str  # expected Python type for validation

    def validate(self, value: Any) -> Any:
        """Coerce *value* to the variable's type.  Raises ValueError."""
        if isinstance(value, self.type):
            return value
        # Bool must come before int (bool is an int subclass)
        if self.type is bool:
            if isinstance(value, str):
                low = value.lower()
                if low in ("true", "t", "yes", "1", "on"):
                    return True
                if low in ("false", "f", "no", "0", "off"):
                    return False
            raise ValueError(f"Variable {self.name}: expected bool, got {value!r}")
        if self.type is int:
            return int(value)
        if self.type is float:
            return float(value)
        if self.type is str:
            return str(value)
        raise ValueError(
            f"Variable {self.name}: cannot convert {value!r} to {self.type.__name__}"
        )


# Global registry: variable name -> EditorVariable
VARIABLES: dict[str, EditorVariable] = {}


def defvar(
    name: str,
    default: Any,
    doc: str = "",
    *,
    var_type: type | None = None,
) -> EditorVariable:
    """Register a new editor variable and return it.

    If *var_type* is not given, it is inferred from *default*.
    """
    if var_type is None:
        var_type = type(default)
    var = EditorVariable(name=name, default=default, doc=doc, type=var_type)
    VARIABLES[name] = var
    return var


# ═══════════════════════════════════════════════════════════════════════
# Built-in variables
# ═══════════════════════════════════════════════════════════════════════

defvar("fill-column", 70, "Column at which auto-fill breaks lines.", var_type=int)
defvar("tab-width", 8, "Width of a tab stop.", var_type=int)
defvar(
    "indent-tabs-mode",
    False,
    "If True, use tabs for indentation; otherwise use spaces.",
    var_type=bool,
)
defvar(
    "truncate-lines",
    True,
    "If True, long lines are truncated at the window edge.",
    var_type=bool,
)
defvar(
    "auto-fill",
    False,
    "If True, automatically break lines at fill-column during typing.",
    var_type=bool,
)
defvar(
    "case-fold-search",
    True,
    "If True, search commands fold case by default (isearch, query-replace). "
    "Isearch applies smart-case on top: folding stays active only while the "
    "search string is all lowercase; typing an uppercase character disables "
    "folding for that session.",
    var_type=bool,
)
