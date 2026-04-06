"""
Config loader — execute user configuration from ``~/.neon-edit.py``.

The config loader runs a user-provided Python file in a curated
namespace that exposes the editor's public extension API.  This gives
users the same level of customisation as Emacs's ``~/.emacs``:
defining commands, binding keys, registering modes, and setting
variables.

**Sandboxing**: The namespace uses a restricted ``__builtins__`` that
excludes ``open``, ``exec``, ``eval``, ``compile``, ``__import__``,
``globals``, and ``locals``.  This is *accidental-mistake protection*
(preventing copy-pasted snippets from doing unexpected I/O), **not**
adversarial sandboxing — a determined attacker who can write arbitrary
Python files has already won.

**Error handling**: Any exception during config loading is caught and
written to the ``*Messages*`` buffer.  The editor always starts
cleanly, even with a broken config.

Architecture
~~~~~~~~~~~~
The loader is structured as two layers:

1. **ConfigNamespace** — builds the curated ``dict`` of names exposed
   to user code.  It takes an ``Editor`` instance and constructs
   convenience wrappers (``bind``, ``unbind``, etc.) that delegate to
   the editor's public API.  Future extensions (e.g., exposing the
   game state, registering hooks) add entries here.

2. **load_config** / **reload_config** — locate the config file,
   compile it, execute it in the namespace, and report errors.
   ``reload_config`` is also registered as an ``M-x`` command.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.commands import COMMANDS, defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.modes import MODES, Mode, SyntaxRule, defmode
from recursive_neon.editor.variables import defvar

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor

# Default config path — overridable via RECURSIVE_NEON_CONFIG_PATH.
_DEFAULT_CONFIG = Path.home() / ".neon-edit.py"

# Builtins to exclude from the config namespace.  This is
# accidental-mistake protection, not adversarial sandboxing.
_BLOCKED_BUILTINS = frozenset(
    {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "globals",
        "locals",
        "breakpoint",
    }
)

# Standard library modules that config code is allowed to import.
# This whitelist keeps the "import X" statement working for modules
# needed to build modes and extensions, while blocking dangerous
# modules like os, subprocess, sys, etc.
_SAFE_MODULES = frozenset(
    {
        "re",
        "string",
        "textwrap",
        "math",
        "functools",
        "itertools",
        "collections",
        "dataclasses",
        "enum",
        "typing",
        "operator",
        "copy",
    }
)


def _config_path() -> Path:
    """Return the config file path, respecting the env var override."""
    env = os.environ.get("RECURSIVE_NEON_CONFIG_PATH")
    if env:
        return Path(env)
    return _DEFAULT_CONFIG


def _make_restricted_import() -> Any:
    """Build a restricted ``__import__`` that only allows safe modules."""
    real_import = (
        __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__
    )

    def restricted_import(
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        top = name.split(".")[0]
        if top not in _SAFE_MODULES:
            raise ImportError(
                f"Module {name!r} is not available in config. "
                f"Allowed modules: {', '.join(sorted(_SAFE_MODULES))}"
            )
        return real_import(name, globals, locals, fromlist, level)

    return restricted_import


def _make_safe_builtins() -> dict[str, Any]:
    """Build a restricted ``__builtins__`` dict.

    Excludes dangerous builtins but provides a restricted ``__import__``
    that whitelists safe standard library modules.
    """
    import builtins

    safe: dict[str, Any] = {}
    for name in dir(builtins):
        if name.startswith("_") and name != "__name__":
            continue
        if name in _BLOCKED_BUILTINS:
            continue
        safe[name] = getattr(builtins, name)
    # Provide a restricted __import__ so 'import re' etc. work
    safe["__import__"] = _make_restricted_import()
    return safe


class ConfigNamespace:
    """Builds the namespace dict exposed to user config code.

    Each public method returns a callable or object suitable for
    inclusion in the config namespace.  The ``build()`` method
    assembles the full dict.
    """

    def __init__(self, editor: Editor) -> None:
        self._editor = editor

    def build(self) -> dict[str, Any]:
        """Return the complete namespace dict for ``exec()``."""
        ns: dict[str, Any] = {
            "__builtins__": _make_safe_builtins(),
            # Core classes — useful for type hints and isinstance checks
            "Buffer": Buffer,
            "Mark": Mark,
            "Keymap": Keymap,
            "Mode": Mode,
            "SyntaxRule": SyntaxRule,
            # Registration helpers
            "defcommand": defcommand,
            "defvar": defvar,
            "defmode": defmode,
            # Key binding helpers (convenience wrappers)
            "bind": self._bind,
            "unbind": self._unbind,
            # The running editor instance — powerful but necessary
            "editor": self._editor,
            # Registries (read access)
            "COMMANDS": COMMANDS,
            "MODES": MODES,
        }
        return ns

    # ── Convenience wrappers ──────────────────────────────────────────

    def _bind(self, key: str, command: str, *, keymap: str = "global") -> None:
        """Bind *key* to *command* in the named keymap.

        ``keymap`` is ``"global"`` by default; pass ``"C-x"`` to bind
        inside the C-x prefix map, etc.
        """
        km = self._resolve_keymap(keymap)
        if km is None:
            self._message(f"config: unknown keymap {keymap!r}")
            return
        km.bind(key, command)

    def _unbind(self, key: str, *, keymap: str = "global") -> None:
        """Remove the binding for *key* in the named keymap."""
        km = self._resolve_keymap(keymap)
        if km is None:
            self._message(f"config: unknown keymap {keymap!r}")
            return
        km.unbind(key)

    def _resolve_keymap(self, name: str) -> Keymap | None:
        """Resolve a keymap name to a ``Keymap`` instance.

        ``"global"`` → the editor's global keymap.  Prefix names like
        ``"C-x"`` look up the binding in the global keymap and return
        the sub-keymap if it is one.
        """
        if name == "global":
            return self._editor.global_keymap
        # Try looking up as a prefix key in the global keymap
        target = self._editor.global_keymap.lookup(name)
        if isinstance(target, Keymap):
            return target
        return None

    def _message(self, text: str) -> None:
        """Write a message to the *Messages* buffer (or editor.message)."""
        self._editor.message = text


def load_config(editor: Editor) -> None:
    """Load and execute the user's config file.

    Safe to call at any time.  Errors are caught and reported in the
    editor message area.  A missing config file is silently ignored.
    """
    path = _config_path()
    if not path.is_file():
        return

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        editor.message = f"Config load error: {e}"
        return

    _exec_config(editor, source, str(path))


def _exec_config(editor: Editor, source: str, filename: str) -> bool:
    """Compile and execute *source* in the config namespace.

    Returns True on success, False if an error was reported.
    """
    ns = ConfigNamespace(editor).build()
    try:
        code = compile(source, filename, "exec")
    except SyntaxError as e:
        editor.message = f"Config syntax error: {e}"
        return False

    try:
        exec(code, ns)  # noqa: S102 — intentional; sandboxed namespace
    except Exception as e:
        editor.message = f"Config error: {e}"
        return False
    return True


# ── M-x reload-config command ────────────────────────────────────────


@defcommand("reload-config", "Re-execute the user config file (~/.neon-edit.py).")
def reload_config(ed: Editor, prefix: int | None) -> None:
    path = _config_path()
    if not path.is_file():
        ed.message = f"No config file at {path}"
        return
    load_config(ed)
    # load_config sets ed.message on error; report success otherwise
    if not ed.message.startswith("Config"):
        ed.message = f"Config reloaded from {path}"
