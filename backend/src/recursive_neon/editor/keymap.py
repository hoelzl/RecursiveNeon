"""
Keymap — layered key binding tables.

A keymap maps key sequences to command names or sub-keymaps (for
prefix keys like C-x).  Keymaps support inheritance via a parent
pointer: if a key is not found locally, the parent is consulted.

Key encoding follows the TUI key convention:
- Printable characters: ``"a"``, ``"Z"``, ``" "``
- Named keys: ``"Enter"``, ``"Backspace"``, ``"Tab"``, ``"Escape"``
- Ctrl combos: ``"C-f"``, ``"C-x"``
- Meta/Alt combos: ``"M-f"``, ``"M-x"``
- Special: ``"C-space"`` for set-mark

Layered resolution order (Hemlock-inspired):
  buffer-local > minor modes > major mode > global
The Editor class handles the layering; Keymap handles single-table
lookup with parent fallback.
"""

from __future__ import annotations

from typing import Union

# A binding target is either a command name or a sub-keymap
BindingTarget = Union[str, "Keymap"]


class Keymap:
    """A key binding table with optional parent for inheritance."""

    def __init__(
        self,
        name: str = "keymap",
        parent: Keymap | None = None,
    ) -> None:
        self.name = name
        self.parent = parent
        self._bindings: dict[str, BindingTarget] = {}

    def bind(self, key: str, target: BindingTarget) -> None:
        """Bind a single key to a command name or sub-keymap.

        For multi-key sequences like ``C-x C-s``, bind the first key
        to a sub-keymap and then bind the second key within that
        sub-keymap::

            cx_map = Keymap("C-x prefix")
            cx_map.bind("C-s", "save-buffer")
            global_map.bind("C-x", cx_map)
        """
        self._bindings[key] = target

    def lookup(self, key: str) -> BindingTarget | None:
        """Look up a single key in this keymap (then parent chain).

        Returns a command name ``str``, a sub-``Keymap`` (for prefix
        keys), or ``None`` if unbound.
        """
        result = self._bindings.get(key)
        if result is not None:
            return result
        if self.parent is not None:
            return self.parent.lookup(key)
        return None

    def unbind(self, key: str) -> None:
        """Remove a binding for a key (local only, does not affect parent)."""
        self._bindings.pop(key, None)

    def bindings(self) -> dict[str, BindingTarget]:
        """Return a copy of the local bindings (not including parent)."""
        return dict(self._bindings)

    def all_bindings(self) -> dict[str, BindingTarget]:
        """Return effective bindings (parent first, then local overrides)."""
        result: dict[str, BindingTarget] = {}
        if self.parent is not None:
            result.update(self.parent.all_bindings())
        result.update(self._bindings)
        return result
