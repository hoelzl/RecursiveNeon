"""
Recursive://Neon CLI Shell

A Unix-like command-line shell over the virtual filesystem.
Run with: python -m recursive_neon.shell
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from recursive_neon.shell.shell import InputSource, Shell


def __getattr__(name: str) -> Any:
    """Load the interactive shell only when its public API is requested."""
    if name in {"InputSource", "Shell"}:
        value = getattr(import_module("recursive_neon.shell.shell"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include lazy public exports in runtime introspection."""
    return sorted(set(globals()) | set(__all__))


__all__ = ["InputSource", "Shell"]
