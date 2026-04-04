"""
Window system — Emacs-style window splitting.

A *window* is a view onto a buffer with independent cursor (point) and
scroll state.  Windows are arranged in a binary tree of splits
(horizontal = top/bottom, vertical = left/right).  The ``WindowTree``
manages the tree structure and active-window tracking.

Each window's ``_point`` is a tracked ``Mark`` in its buffer, so
insert/delete operations in other windows keep the cursor correct.
Movement commands only touch ``buffer.point``; EditorView syncs
``buffer.point ↔ active_window._point`` around each keystroke.

Implements the ``Viewport`` protocol so scroll commands work per-window.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from recursive_neon.editor.mark import Mark

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer


class Window:
    """A view onto a buffer with independent cursor and scroll state."""

    __slots__ = (
        "buffer",
        "_point",
        "scroll_top",
        "_height",
        "_width",
        "_top",
        "_left",
    )

    def __init__(self, buffer: Buffer, point: Mark) -> None:
        self.buffer = buffer
        self._point = point
        self.scroll_top: int = 0
        # Layout fields — set by EditorView during rendering
        self._height: int = 0
        self._width: int = 0
        self._top: int = 0
        self._left: int = 0

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def for_buffer(cls, buf: Buffer) -> Window:
        """Create a window showing *buf* with a tracked point at buf.point."""
        pt = Mark(buf.point.line, buf.point.col, kind="right")
        buf.track_mark(pt)
        return cls(buf, pt)

    # ------------------------------------------------------------------
    # Viewport protocol
    # ------------------------------------------------------------------

    @property
    def text_height(self) -> int:
        """Rows available for buffer text (height minus modeline)."""
        return max(1, self._height - 1)

    def scroll_to(self, line: int) -> None:
        """Set the first visible line, clamped >= 0."""
        self.scroll_top = max(0, line)

    # ------------------------------------------------------------------
    # Point sync
    # ------------------------------------------------------------------

    def sync_from_buffer(self) -> None:
        """Copy ``buffer.point`` into this window's tracked mark."""
        self._point.move_to(self.buffer.point.line, self.buffer.point.col)

    def sync_to_buffer(self) -> None:
        """Copy this window's tracked mark into ``buffer.point``."""
        self.buffer.point.move_to(self._point.line, self._point.col)

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def ensure_cursor_visible(self) -> None:
        """Adjust ``scroll_top`` so the window's point is on screen."""
        cursor_line = self._point.line
        if cursor_line < self.scroll_top:
            self.scroll_top = cursor_line
        elif cursor_line >= self.scroll_top + self.text_height:
            self.scroll_top = cursor_line - self.text_height + 1

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def detach(self) -> None:
        """Untrack this window's point from its buffer."""
        self.buffer.untrack_mark(self._point)


# ======================================================================
# Split tree
# ======================================================================


class SplitDirection(Enum):
    HORIZONTAL = "horizontal"  # top / bottom  (C-x 2)
    VERTICAL = "vertical"  # left / right  (C-x 3)


class WindowSplit:
    """An internal node: two children separated by a split."""

    __slots__ = ("direction", "first", "second")

    def __init__(
        self,
        direction: SplitDirection,
        first: WindowNode,
        second: WindowNode,
    ) -> None:
        self.direction = direction
        self.first = first
        self.second = second


# The tree is a tagged union of leaf (Window) and internal (WindowSplit).
WindowNode = Window | WindowSplit


# ======================================================================
# Window tree manager
# ======================================================================


class WindowTree:
    """Manages a binary tree of windows and tracks the active window."""

    def __init__(self, root: Window) -> None:
        self.root: WindowNode = root
        self.active: Window = root

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_single(self) -> bool:
        """True when the tree contains exactly one window."""
        return isinstance(self.root, Window)

    def windows(self) -> list[Window]:
        """Return all windows in depth-first (left-to-right) order."""
        result: list[Window] = []
        self._collect(self.root, result)
        return result

    @staticmethod
    def _collect(node: WindowNode, out: list[Window]) -> None:
        if isinstance(node, Window):
            out.append(node)
        else:
            WindowTree._collect(node.first, out)
            WindowTree._collect(node.second, out)

    def other_window(self) -> Window | None:
        """Return the 'other' window (next in cycle), or None if single."""
        wins = self.windows()
        if len(wins) < 2:
            return None
        idx = wins.index(self.active)
        return wins[(idx + 1) % len(wins)]

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def next_window(self) -> Window:
        """Cycle ``active`` to the next window and return it."""
        wins = self.windows()
        idx = wins.index(self.active)
        self.active = wins[(idx + 1) % len(wins)]
        return self.active

    def prev_window(self) -> Window:
        """Cycle ``active`` to the previous window and return it."""
        wins = self.windows()
        idx = wins.index(self.active)
        self.active = wins[(idx - 1) % len(wins)]
        return self.active

    # ------------------------------------------------------------------
    # Splitting
    # ------------------------------------------------------------------

    def split(self, direction: SplitDirection) -> Window:
        """Split the active window.  Returns the new (second) window.

        The active window stays active (Emacs behaviour).  The new
        window shows the same buffer, same scroll position, same point.
        """
        old = self.active
        new = Window.for_buffer(old.buffer)
        new._point.move_to(old._point.line, old._point.col)
        new.scroll_top = old.scroll_top

        split_node = WindowSplit(direction, old, new)
        self._replace_node(old, split_node)
        return new

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_window(self) -> Window | None:
        """Delete the active window.

        Returns the new active window, or ``None`` if this is the sole
        window (deletion is not allowed).
        """
        if self.is_single():
            return None

        target = self.active
        parent = self._find_parent(target)
        if parent is None:
            return None  # shouldn't happen if not single

        # The sibling replaces the parent split
        sibling = parent.second if parent.first is target else parent.first
        self._replace_node(parent, sibling)
        target.detach()

        # Activate the first leaf of the sibling subtree
        wins = self.windows()
        self.active = wins[0] if wins else sibling  # type: ignore[assignment]
        # Prefer the sibling's first leaf closest to where the old window was
        leaves: list[Window] = []
        self._collect(sibling, leaves)
        if leaves:
            self.active = leaves[0]
        return self.active

    def delete_other_windows(self) -> None:
        """Remove all windows except the active one."""
        # Detach all other windows' tracked marks
        for win in self.windows():
            if win is not self.active:
                win.detach()
        self.root = self.active

    # ------------------------------------------------------------------
    # Internal tree surgery
    # ------------------------------------------------------------------

    def _find_parent(self, target: WindowNode) -> WindowSplit | None:
        """Find the parent split of *target*, or None if it's the root."""
        return self._find_parent_in(self.root, target)

    def _find_parent_in(
        self, node: WindowNode, target: WindowNode
    ) -> WindowSplit | None:
        if isinstance(node, WindowSplit):
            if node.first is target or node.second is target:
                return node
            result = self._find_parent_in(node.first, target)
            if result is not None:
                return result
            return self._find_parent_in(node.second, target)
        return None

    def _replace_node(self, old: WindowNode, new: WindowNode) -> None:
        """Replace *old* with *new* in the tree."""
        if self.root is old:
            self.root = new
            return
        parent = self._find_parent(old)
        if parent is not None:
            if parent.first is old:
                parent.first = new
            else:
                parent.second = new
