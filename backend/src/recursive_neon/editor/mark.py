"""
Mark — a position in a buffer.

A mark tracks a (line, col) position.  Marks come in three kinds
(following Hemlock's model):

- **temporary**: lightweight, not tracked by the buffer.  Invalidated
  by edits — the caller is responsible for knowing when they're stale.
- **left-inserting**: when text is inserted *at* the mark's exact
  position, the mark stays to the **left** of the new text.
- **right-inserting**: the mark stays to the **right** of the new text.

Point (the cursor) is typically a right-inserting mark so that typed
characters appear before it.  The region mark is typically
left-inserting so that point and mark naturally bracket inserted text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MarkKind = Literal["temporary", "left", "right"]


@dataclass
class Mark:
    """A position in a buffer, identified by line and column."""

    line: int
    col: int
    kind: MarkKind = "temporary"

    # ------------------------------------------------------------------
    # Comparison — total ordering by (line, col)
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mark):
            return NotImplemented
        return self.line == other.line and self.col == other.col

    def __lt__(self, other: Mark) -> bool:
        if self.line != other.line:
            return self.line < other.line
        return self.col < other.col

    def __le__(self, other: Mark) -> bool:
        return self == other or self < other

    def __gt__(self, other: Mark) -> bool:
        return not self <= other

    def __ge__(self, other: Mark) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return hash((self.line, self.col, self.kind))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def copy(self, *, kind: MarkKind | None = None) -> Mark:
        """Return a new Mark at the same position, optionally changing kind."""
        return Mark(self.line, self.col, kind if kind is not None else self.kind)

    def to_tuple(self) -> tuple[int, int]:
        """Return (line, col) as a plain tuple."""
        return (self.line, self.col)

    def move_to(self, line: int, col: int) -> None:
        """Move the mark to a new position in place."""
        self.line = line
        self.col = col
