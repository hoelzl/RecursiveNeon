"""
Viewport protocol — decouples scroll commands from the view layer.

Commands that need viewport information (scroll-up, scroll-down,
recenter) call methods on ``Editor.viewport`` instead of depending
on EditorView directly.  EditorView implements this protocol; when
no view is attached (headless / tests), ``viewport`` is None and
scroll commands gracefully no-op.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Viewport(Protocol):
    """Read/write access to the visible region of the editor."""

    @property
    def scroll_top(self) -> int:
        """First visible line index."""
        ...

    @property
    def text_height(self) -> int:
        """Number of screen rows available for buffer text."""
        ...

    def scroll_to(self, line: int) -> None:
        """Set the first visible line (clamped to >= 0)."""
        ...
