"""
Buffer — the core text container.

A buffer holds a list of line strings, a point (cursor), an optional
mark (for the region), and a set of tracked marks that are kept
consistent through all edits.

Text storage follows the Hemlock model: each line is a Python ``str``,
newlines are implicit between lines.  An empty buffer has one empty
line (like Emacs: a buffer always has at least one line).

All mutating operations go through a small set of primitives that
maintain mark consistency.  Higher-level operations are built on top.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.mark import Mark

if TYPE_CHECKING:
    from recursive_neon.editor.keymap import Keymap
    from recursive_neon.editor.modes import Mode
    from recursive_neon.editor.text_attr import TextAttr
from recursive_neon.editor.undo import (
    UndoBoundary,
    UndoCursorMove,
    UndoDelete,
    UndoEntry,
    UndoInsert,
)


@dataclass
class ReadOnlyRegion:
    """A range of text that cannot be modified.

    Both marks should be tracked on the buffer so they follow edits
    automatically.  ``kind="left"`` is recommended so that text inserted
    exactly at a boundary goes *outside* the protected region.
    """

    start: Mark
    end: Mark

    def contains(self, line: int, col: int) -> bool:
        """True if *(line, col)* is strictly inside this region."""
        s = (self.start.line, self.start.col)
        e = (self.end.line, self.end.col)
        if s > e:
            s, e = e, s
        pos = (line, col)
        return s <= pos < e

    def overlaps(self, sl: int, sc: int, el: int, ec: int) -> bool:
        """True if the range [sl:sc, el:ec) overlaps this region."""
        rs = (self.start.line, self.start.col)
        re_ = (self.end.line, self.end.col)
        if rs > re_:
            rs, re_ = re_, rs
        # Two ranges [A, B) and [C, D) overlap iff A < D and C < B
        return rs < (el, ec) and (sl, sc) < re_


def _undo_attrs_to_runs(
    text: str,
    attrs: tuple[tuple[TextAttr | None, ...], ...],
) -> list[tuple[str, TextAttr | None]]:
    """Convert undo-captured text + attrs back to runs for reinsertion."""
    from recursive_neon.editor.text_attr import TextAttr as _TA  # noqa: F811

    runs: list[tuple[str, _TA | None]] = []
    lines = text.split("\n")
    for i, line_text in enumerate(lines):
        if i < len(attrs):
            line_a = attrs[i]
            # Build runs by grouping consecutive identical attrs
            j = 0
            while j < len(line_text) and j < len(line_a):
                attr = line_a[j]
                start = j
                while j < len(line_text) and j < len(line_a) and line_a[j] == attr:
                    j += 1
                runs.append((line_text[start:j], attr))
            # Any remaining text (if attrs shorter than text)
            if j < len(line_text):
                runs.append((line_text[j:], None))
        else:
            runs.append((line_text, None))
        # Add newline between lines (not after last)
        if i < len(lines) - 1:
            runs.append(("\n", None))
    return runs


class Buffer:
    """A named text buffer with point, mark, and tracked marks."""

    def __init__(
        self,
        name: str = "*scratch*",
        text: str = "",
        *,
        filepath: str | None = None,
    ) -> None:
        self.name = name
        self.filepath = filepath
        self.modified: bool = False
        self.read_only: bool = False
        self.keymap: Keymap | None = None  # buffer-local keymap (checked first)
        self.on_focus: Callable[[], None] | None = (
            None  # called when buffer becomes current
        )

        # Mode system
        self.major_mode: Mode | None = None
        self.minor_modes: list[Mode] = []

        # Buffer-local variable overrides (name -> value)
        self.local_variables: dict[str, Any] = {}

        # Text storage — always at least one line
        if text:
            self.lines: list[str] = text.split("\n")
        else:
            self.lines = [""]

        # Point is right-inserting: typed chars appear before it
        self.point = Mark(0, 0, kind="right")
        # Mark (region anchor) is None until set
        self.mark: Mark | None = None

        # All non-temporary marks tracked for automatic maintenance.
        # Point is always tracked; mark is added/removed as set/cleared.
        self._tracked_marks: list[Mark] = [self.point]

        # Goal column for vertical movement (-1 = not set)
        self._goal_col: int = -1

        # Undo list — Emacs-style unlimited undo
        self.undo_list: list[UndoEntry] = []
        self._undo_recording: bool = True
        # Cursor for consecutive undo: when set, undo scans backward
        # from this position (so reverse entries at the tail are skipped)
        self._undo_cursor: int = -1

        # Kill ring (shared across buffers in a real editor, but
        # per-buffer for now — the Editor class will share one instance)
        self.kill_ring: KillRing = KillRing()

        # Last command type — used for consecutive kill merging
        self.last_command_type: str = ""

        # Read-only regions — mark-pair ranges where mutations are refused
        self._read_only_regions: list[ReadOnlyRegion] = []
        self._read_only_error: bool = False

        # Per-character text attributes (e.g., ANSI colours from shell
        # output).  None = no attribute layer (zero cost for plain-text
        # buffers).  When not None, parallel to self.lines — each inner
        # list has the same length as the corresponding line string.
        self._line_attrs: list[list[TextAttr | None]] | None = None

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def from_text(cls, text: str, *, name: str = "*scratch*") -> Buffer:
        """Create a buffer pre-loaded with text."""
        return cls(name=name, text=text)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def current_line(self) -> str:
        """The text of the line containing point."""
        return self.lines[self.point.line]

    @property
    def text(self) -> str:
        """The full buffer text as a single string."""
        return "\n".join(self.lines)

    @property
    def region_active(self) -> bool:
        """True if the mark is set (region is active)."""
        return self.mark is not None

    @property
    def region_text(self) -> str | None:
        """Return the text of the region (point to mark), or None."""
        if self.mark is None:
            return None
        return self.get_text(self.point, self.mark)

    def set_variable_local(self, name: str, value: Any) -> None:
        """Set a buffer-local variable override."""
        from recursive_neon.editor.variables import VARIABLES

        var = VARIABLES.get(name)
        if var is not None:
            value = var.validate(value)
        self.local_variables[name] = value

    # ------------------------------------------------------------------
    # Mark tracking
    # ------------------------------------------------------------------

    def track_mark(self, m: Mark) -> None:
        """Register a mark for automatic maintenance during edits."""
        if not any(t is m for t in self._tracked_marks):
            self._tracked_marks.append(m)

    def untrack_mark(self, m: Mark) -> None:
        """Remove a mark from automatic maintenance."""
        self._tracked_marks = [t for t in self._tracked_marks if t is not m]

    def set_mark(self, line: int | None = None, col: int | None = None) -> Mark:
        """Set the mark at the given position (default: point's position).

        Returns the mark.
        """
        if line is None:
            line = self.point.line
        if col is None:
            col = self.point.col

        if self.mark is not None:
            self.untrack_mark(self.mark)
        self.mark = Mark(line, col, kind="left")
        self.track_mark(self.mark)
        return self.mark

    def clear_mark(self) -> None:
        """Deactivate the region by clearing the mark."""
        if self.mark is not None:
            self.untrack_mark(self.mark)
            self.mark = None

    # ------------------------------------------------------------------
    # Read-only regions
    # ------------------------------------------------------------------

    def add_read_only_region(self, start: Mark, end: Mark) -> ReadOnlyRegion:
        """Mark a range as read-only.  Returns the region for later removal.

        Both marks are tracked so they follow edits automatically.
        """
        self.track_mark(start)
        self.track_mark(end)
        region = ReadOnlyRegion(start=start, end=end)
        self._read_only_regions.append(region)
        return region

    def remove_read_only_region(self, region: ReadOnlyRegion) -> None:
        """Remove a previously-added read-only region."""
        try:
            self._read_only_regions.remove(region)
        except ValueError:
            return
        self.untrack_mark(region.start)
        self.untrack_mark(region.end)

    def clear_read_only_regions(self) -> None:
        """Remove all read-only regions."""
        for region in self._read_only_regions:
            self.untrack_mark(region.start)
            self.untrack_mark(region.end)
        self._read_only_regions.clear()

    def is_read_only_at(self, line: int, col: int) -> bool:
        """True if position falls inside any read-only region."""
        return any(region.contains(line, col) for region in self._read_only_regions)

    def _check_read_only_range(
        self, start_line: int, start_col: int, end_line: int, end_col: int
    ) -> bool:
        """True if any part of the range overlaps a read-only region."""
        for region in self._read_only_regions:
            if region.overlaps(start_line, start_col, end_line, end_col):
                return True
        return False

    # ------------------------------------------------------------------
    # Text attributes
    # ------------------------------------------------------------------

    def enable_attrs(self) -> None:
        """Lazily initialise the attribute layer (all positions default)."""
        if self._line_attrs is None:
            self._line_attrs = [[None] * len(line) for line in self.lines]

    def insert_string_attributed(self, runs: list[tuple[str, TextAttr | None]]) -> None:
        """Insert text with per-character attributes at point.

        Each run is a ``(text, attr)`` pair.  ``attr=None`` means
        default styling.  Enables the attribute layer if not already
        enabled.
        """
        if not runs:
            return
        if self.read_only:
            return
        if self._undo_recording and self.is_read_only_at(
            self.point.line, self.point.col
        ):
            self._read_only_error = True
            return

        self.enable_attrs()

        # Build full text and per-character attr list
        full_text = "".join(text for text, _ in runs)
        if not full_text:
            return
        char_attrs: list[TextAttr | None] = []
        for text, attr in runs:
            char_attrs.extend([attr] * len(text))

        start = self.point.to_tuple()

        # Insert using the same primitive pattern as insert_string,
        # passing _attrs to _insert_within_line.
        parts = full_text.split("\n")
        offset = 0
        seg = parts[0]
        self._insert_within_line(seg, _attrs=char_attrs[offset : offset + len(seg)])
        offset += len(seg)
        for part in parts[1:]:
            self._insert_newline()
            offset += 1  # skip the \n in char_attrs
            if part:
                self._insert_within_line(
                    part, _attrs=char_attrs[offset : offset + len(part)]
                )
                offset += len(part)

        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*start))
            self.undo_list.append(UndoInsert(*start, self.point.line, self.point.col))

    def _capture_single_attr(
        self, line: int, col: int, ch: str
    ) -> tuple[tuple[TextAttr | None, ...], ...] | None:
        """Capture the attr of a single character (for single-char undo)."""
        if self._line_attrs is None:
            return None
        if ch == "\n":
            # Newline has no attr entry (it's between lines)
            return ((),)
        return ((self._line_attrs[line][col],),)

    def _capture_line_attrs(
        self,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
    ) -> tuple[tuple[TextAttr | None, ...], ...] | None:
        """Capture attrs for a range (for undo).  None if no attr layer."""
        if self._line_attrs is None:
            return None
        if start_line == end_line:
            return (tuple(self._line_attrs[start_line][start_col:end_col]),)
        result: list[tuple[TextAttr | None, ...]] = []
        result.append(tuple(self._line_attrs[start_line][start_col:]))
        for ln in range(start_line + 1, end_line):
            result.append(tuple(self._line_attrs[ln]))
        result.append(tuple(self._line_attrs[end_line][:end_col]))
        return tuple(result)

    # ------------------------------------------------------------------
    # Text access
    # ------------------------------------------------------------------

    def get_text(self, start: Mark, end: Mark) -> str:
        """Return text between two positions (order-independent)."""
        a, b = (start, end) if start <= end else (end, start)
        if a.line == b.line:
            return self.lines[a.line][a.col : b.col]
        parts = [self.lines[a.line][a.col :]]
        for ln in range(a.line + 1, b.line):
            parts.append(self.lines[ln])
        parts.append(self.lines[b.line][: b.col])
        return "\n".join(parts)

    def char_after_point(self) -> str | None:
        """The character immediately after point, or None at end of buffer."""
        line = self.lines[self.point.line]
        if self.point.col < len(line):
            return line[self.point.col]
        if self.point.line < len(self.lines) - 1:
            return "\n"
        return None

    def char_before_point(self) -> str | None:
        """The character immediately before point, or None at start of buffer."""
        if self.point.col > 0:
            return self.lines[self.point.line][self.point.col - 1]
        if self.point.line > 0:
            return "\n"
        return None

    # ------------------------------------------------------------------
    # Insertion primitives
    # ------------------------------------------------------------------

    def insert_char(self, ch: str) -> None:
        """Insert a single character at point."""
        if self.read_only:
            return
        if self._undo_recording and self.is_read_only_at(
            self.point.line, self.point.col
        ):
            self._read_only_error = True
            return
        start = self.point.to_tuple()
        if ch == "\n":
            self._insert_newline()
        else:
            self._insert_within_line(ch)
        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*start))
            self.undo_list.append(UndoInsert(*start, self.point.line, self.point.col))

    def insert_string(self, s: str) -> None:
        """Insert a (possibly multi-line) string at point."""
        if not s:
            return
        if self.read_only:
            return
        if self._undo_recording and self.is_read_only_at(
            self.point.line, self.point.col
        ):
            self._read_only_error = True
            return
        start = self.point.to_tuple()
        # Split into lines and insert one segment at a time
        parts = s.split("\n")
        # First segment: insert on current line
        self._insert_within_line(parts[0])
        # Remaining segments: newline + text
        for part in parts[1:]:
            self._insert_newline()
            if part:
                self._insert_within_line(part)
        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*start))
            self.undo_list.append(UndoInsert(*start, self.point.line, self.point.col))

    def _insert_within_line(
        self,
        text: str,
        *,
        _attrs: list[TextAttr | None] | None = None,
    ) -> None:
        """Insert text (no newlines) at point on the current line."""
        if not text:
            return
        ln = self.point.line
        col = self.point.col
        line = self.lines[ln]
        self.lines[ln] = line[:col] + text + line[col:]
        length = len(text)

        # --- attrs ---
        if self._line_attrs is not None:
            la = self._line_attrs[ln]
            new_attrs = _attrs if _attrs is not None else [None] * length
            self._line_attrs[ln] = la[:col] + new_attrs + la[col:]

        # Update tracked marks on the same line
        for m in self._tracked_marks:
            if m.line != ln:
                continue
            if m is self.point:
                # Point always advances past inserted text
                m.col += length
                continue
            if m.col < col:
                pass  # before insertion — no change
            elif m.col > col:
                m.col += length  # after insertion — shift right
            else:
                # At the insertion point: kind determines behavior
                if m.kind == "right":
                    m.col += length  # stay right of new text
                # "left" and "temporary" stay put

    def _insert_newline(self) -> None:
        """Split the current line at point, inserting a newline."""
        ln = self.point.line
        col = self.point.col
        line = self.lines[ln]
        before = line[:col]
        after = line[col:]
        self.lines[ln] = before
        self.lines.insert(ln + 1, after)

        # --- attrs ---
        if self._line_attrs is not None:
            la = self._line_attrs[ln]
            self._line_attrs[ln] = la[:col]
            self._line_attrs.insert(ln + 1, la[col:])

        # Update tracked marks
        for m in self._tracked_marks:
            if m.line < ln:
                continue
            if m.line > ln:
                # Lines below shift down by one
                m.line += 1
                continue
            # Same line as the split
            if m is self.point:
                m.line = ln + 1
                m.col = 0
                continue
            if m.col < col:
                pass  # stays on the original line
            elif m.col > col:
                # After the split point — moves to the new line
                m.line = ln + 1
                m.col = m.col - col
            else:
                # Exactly at the split point — kind decides
                if m.kind == "right":
                    m.line = ln + 1
                    m.col = 0
                # "left" and "temporary" stay on original line

    # ------------------------------------------------------------------
    # Deletion primitives
    # ------------------------------------------------------------------

    def delete_char_forward(self) -> str | None:
        """Delete the character after point.  Returns the deleted char."""
        if self.read_only:
            return None
        if self._undo_recording and self.is_read_only_at(
            self.point.line, self.point.col
        ):
            self._read_only_error = True
            return None
        ch = self.char_after_point()
        if ch is None:
            return None
        pos = self.point.to_tuple()
        # Capture attr of the char being deleted
        del_attr = self._capture_single_attr(pos[0], pos[1], ch)
        if ch == "\n":
            self._join_line_forward()
        else:
            self._delete_within_line_forward()
        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*pos))
            self.undo_list.append(UndoDelete(*pos, ch, attrs=del_attr))
        return ch

    def delete_char_backward(self) -> str | None:
        """Delete the character before point.  Returns the deleted char."""
        if self.read_only:
            return None
        # Check the position of the char that would be deleted
        bl, bc = self.point.line, self.point.col
        if bc > 0:
            check_line, check_col = bl, bc - 1
        elif bl > 0:
            check_line, check_col = bl - 1, len(self.lines[bl - 1])
        else:
            check_line, check_col = bl, bc
        if self._undo_recording and self.is_read_only_at(check_line, check_col):
            self._read_only_error = True
            return None
        ch = self.char_before_point()
        if ch is None:
            return None
        orig_pos = self.point.to_tuple()
        # Capture attr of the char being deleted
        del_attr = self._capture_single_attr(check_line, check_col, ch)
        if ch == "\n":
            self._join_line_backward()
        else:
            self._delete_within_line_backward()
        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*orig_pos))
            self.undo_list.append(
                UndoDelete(self.point.line, self.point.col, ch, attrs=del_attr)
            )
        return ch

    def delete_region(self, start: Mark, end: Mark) -> str:
        """Delete text between two positions.  Returns deleted text.

        Marks inside the deleted region collapse to the deletion point.
        """
        if self.read_only and self._undo_recording:
            return ""
        if self._undo_recording and self._read_only_regions:
            a, b = (start, end) if start <= end else (end, start)
            if self._check_read_only_range(a.line, a.col, b.line, b.col):
                self._read_only_error = True
                return ""
        a, b = (
            (start.copy(), end.copy()) if start <= end else (end.copy(), start.copy())
        )
        deleted = self.get_text(a, b)
        if not deleted:
            return ""

        orig_point = self.point.to_tuple()

        # Capture attrs before deletion (for undo)
        captured_attrs = self._capture_line_attrs(a.line, a.col, b.line, b.col)

        if a.line == b.line:
            # Single-line deletion
            line = self.lines[a.line]
            self.lines[a.line] = line[: a.col] + line[b.col :]
            # --- attrs ---
            if self._line_attrs is not None:
                la = self._line_attrs[a.line]
                self._line_attrs[a.line] = la[: a.col] + la[b.col :]
            self._adjust_marks_after_delete_single(a.line, a.col, b.col)
        else:
            # Multi-line deletion: join first and last line remnants
            before = self.lines[a.line][: a.col]
            after = self.lines[b.line][b.col :]
            self.lines[a.line] = before + after
            # Remove the lines in between (and b's line)
            del self.lines[a.line + 1 : b.line + 1]
            # --- attrs ---
            if self._line_attrs is not None:
                before_a = self._line_attrs[a.line][: a.col]
                after_a = self._line_attrs[b.line][b.col :]
                self._line_attrs[a.line] = before_a + after_a
                del self._line_attrs[a.line + 1 : b.line + 1]
            self._adjust_marks_after_delete_multi(a.line, a.col, b.line, b.col)

        self.modified = True
        if self._undo_recording:
            self.undo_list.append(UndoCursorMove(*orig_point))
            self.undo_list.append(
                UndoDelete(a.line, a.col, deleted, attrs=captured_attrs)
            )
        return deleted

    def _delete_within_line_forward(self) -> None:
        """Delete one character after point on the same line."""
        ln = self.point.line
        col = self.point.col
        line = self.lines[ln]
        self.lines[ln] = line[:col] + line[col + 1 :]

        # --- attrs ---
        if self._line_attrs is not None:
            la = self._line_attrs[ln]
            self._line_attrs[ln] = la[:col] + la[col + 1 :]

        # Marks after the deleted char shift left by 1
        for m in self._tracked_marks:
            if m.line != ln:
                continue
            if m.col > col:
                m.col -= 1
            # Marks at col (point) or before are unaffected

    def _delete_within_line_backward(self) -> None:
        """Delete one character before point on the same line."""
        ln = self.point.line
        col = self.point.col
        line = self.lines[ln]
        self.lines[ln] = line[: col - 1] + line[col:]

        # --- attrs ---
        if self._line_attrs is not None:
            la = self._line_attrs[ln]
            self._line_attrs[ln] = la[: col - 1] + la[col:]

        # Marks at or after the deleted position shift left
        for m in self._tracked_marks:
            if m.line != ln:
                continue
            if m.col >= col:
                m.col -= 1

    def _join_line_forward(self) -> None:
        """Join the next line onto the current line (delete newline after point)."""
        ln = self.point.line
        if ln >= len(self.lines) - 1:
            return
        join_col = len(self.lines[ln])
        next_line = self.lines[ln + 1]
        self.lines[ln] = self.lines[ln] + next_line
        del self.lines[ln + 1]

        # --- attrs ---
        if self._line_attrs is not None:
            self._line_attrs[ln] = self._line_attrs[ln] + self._line_attrs[ln + 1]
            del self._line_attrs[ln + 1]

        # Marks on the removed line move up; marks below shift up by 1
        for m in self._tracked_marks:
            if m.line == ln + 1:
                m.line = ln
                m.col += join_col
            elif m.line > ln + 1:
                m.line -= 1

    def _join_line_backward(self) -> None:
        """Join current line onto the previous line (delete newline before point)."""
        ln = self.point.line
        if ln <= 0:
            return
        prev_len = len(self.lines[ln - 1])
        current_line = self.lines[ln]
        self.lines[ln - 1] = self.lines[ln - 1] + current_line
        del self.lines[ln]

        # --- attrs ---
        if self._line_attrs is not None:
            self._line_attrs[ln - 1] = self._line_attrs[ln - 1] + self._line_attrs[ln]
            del self._line_attrs[ln]

        # Marks on the current line move up; marks below shift up by 1
        for m in self._tracked_marks:
            if m.line == ln:
                m.line = ln - 1
                m.col += prev_len
            elif m.line > ln:
                m.line -= 1

    def _adjust_marks_after_delete_single(
        self, ln: int, start_col: int, end_col: int
    ) -> None:
        """Adjust marks after a single-line region deletion."""
        width = end_col - start_col
        for m in self._tracked_marks:
            if m.line != ln:
                continue
            if m.col <= start_col:
                pass  # before deleted region
            elif m.col >= end_col:
                m.col -= width  # after region — shift left
            else:
                m.col = start_col  # inside region — collapse

    def _adjust_marks_after_delete_multi(
        self, start_ln: int, start_col: int, end_ln: int, end_col: int
    ) -> None:
        """Adjust marks after a multi-line region deletion."""
        lines_removed = end_ln - start_ln
        for m in self._tracked_marks:
            if m.line < start_ln:
                continue
            if m.line == start_ln:
                if m.col > start_col:
                    m.col = start_col  # in first line of region — collapse
            elif m.line <= end_ln:
                if m.line == end_ln and m.col >= end_col:
                    # After the deletion on the last line — adjust
                    m.col = start_col + (m.col - end_col)
                    m.line = start_ln
                else:
                    # Inside the deleted region — collapse
                    m.line = start_ln
                    m.col = start_col
            else:
                # Below the deleted region — shift up
                m.line -= lines_removed

    # ------------------------------------------------------------------
    # Point movement
    # ------------------------------------------------------------------

    def forward_char(self, n: int = 1) -> bool:
        """Move point forward by *n* characters.  Returns True if moved."""
        self._goal_col = -1
        moved = False
        for _ in range(abs(n)):
            if n > 0:
                if self.point.col < len(self.lines[self.point.line]):
                    self.point.col += 1
                    moved = True
                elif self.point.line < len(self.lines) - 1:
                    self.point.line += 1
                    self.point.col = 0
                    moved = True
            else:
                if self.point.col > 0:
                    self.point.col -= 1
                    moved = True
                elif self.point.line > 0:
                    self.point.line -= 1
                    self.point.col = len(self.lines[self.point.line])
                    moved = True
        return moved

    def backward_char(self, n: int = 1) -> bool:
        """Move point backward by *n* characters."""
        return self.forward_char(-n)

    def forward_line(self, n: int = 1) -> bool:
        """Move point down by *n* lines, preserving goal column."""
        if self._goal_col < 0:
            self._goal_col = self.point.col
        moved = False
        for _ in range(abs(n)):
            if n > 0:
                if self.point.line < len(self.lines) - 1:
                    self.point.line += 1
                    moved = True
                else:
                    break
            else:
                if self.point.line > 0:
                    self.point.line -= 1
                    moved = True
                else:
                    break
        # Clamp col to line length, but preserve goal column
        self.point.col = min(self._goal_col, len(self.lines[self.point.line]))
        return moved

    def backward_line(self, n: int = 1) -> bool:
        """Move point up by *n* lines, preserving goal column."""
        return self.forward_line(-n)

    def beginning_of_line(self) -> None:
        """Move point to the beginning of the current line."""
        self.point.col = 0
        self._goal_col = -1

    def end_of_line(self) -> None:
        """Move point to the end of the current line."""
        self.point.col = len(self.lines[self.point.line])
        self._goal_col = -1

    def beginning_of_buffer(self) -> None:
        """Move point to the beginning of the buffer."""
        self.point.line = 0
        self.point.col = 0
        self._goal_col = -1

    def end_of_buffer(self) -> None:
        """Move point to the end of the buffer."""
        self.point.line = len(self.lines) - 1
        self.point.col = len(self.lines[-1])
        self._goal_col = -1

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def add_undo_boundary(self, *, break_undo_chain: bool = True) -> None:
        """Insert an undo boundary.

        Call this between commands so that one ``undo()`` invocation
        reverses exactly one command's worth of changes.  Consecutive
        boundaries are collapsed.

        By default this also breaks any active undo chain so the next
        ``undo()`` starts scanning from the end — the correct behaviour
        for dispatching a fresh command on top of a recent undo.  Pass
        ``break_undo_chain=False`` when you need a boundary inside an
        ongoing undo (see ``Buffer.undo``'s use): the boundary
        partitions the entries, but ``last_command_type`` and
        ``_undo_cursor`` are left alone so the chain survives.
        """
        if self.undo_list and isinstance(self.undo_list[-1], UndoBoundary):
            return
        self.undo_list.append(UndoBoundary())
        if break_undo_chain:
            # Break undo chain — next undo() scans from the new end
            self._undo_cursor = -1
            if self.last_command_type == "undo":
                self.last_command_type = ""

    def undo(self) -> bool:
        """Undo one command group.

        Uses an internal cursor so that consecutive undo calls walk
        further back through history.  Reverse entries are appended
        to the tail so that "undo the undo" works after a non-undo
        command resets the cursor.

        Returns True if anything was undone.
        """
        # First undo in a chain: snapshot the scan position
        if self.last_command_type != "undo":
            self._undo_cursor = len(self.undo_list)

        cursor = self._undo_cursor

        # Skip boundaries at cursor
        while cursor > 0 and isinstance(self.undo_list[cursor - 1], UndoBoundary):
            cursor -= 1

        if cursor == 0:
            return False

        # Collect one group (scanning backward from cursor)
        group: list[UndoEntry] = []
        while cursor > 0:
            entry = self.undo_list[cursor - 1]
            if isinstance(entry, UndoBoundary):
                break
            cursor -= 1
            group.append(entry)

        if not group:
            return False

        self._undo_cursor = cursor

        # Process collected entries and build reverse entries
        reverse: list[UndoEntry] = []
        for entry in group:
            if isinstance(entry, UndoInsert):
                start = Mark(entry.start_line, entry.start_col)
                end = Mark(entry.end_line, entry.end_col)
                # Capture attrs of the region about to be deleted
                cap = self._capture_line_attrs(
                    entry.start_line,
                    entry.start_col,
                    entry.end_line,
                    entry.end_col,
                )
                self._undo_recording = False
                deleted = self.delete_region(start, end)
                self._undo_recording = True
                reverse.append(
                    UndoDelete(entry.start_line, entry.start_col, deleted, attrs=cap)
                )

            elif isinstance(entry, UndoDelete):
                self.point.move_to(entry.line, entry.col)
                self._undo_recording = False
                if entry.attrs is not None and self._line_attrs is not None:
                    # Restore with attrs
                    runs = _undo_attrs_to_runs(entry.text, entry.attrs)
                    self.insert_string_attributed(runs)
                else:
                    self.insert_string(entry.text)
                self._undo_recording = True
                reverse.append(
                    UndoInsert(
                        entry.line,
                        entry.col,
                        self.point.line,
                        self.point.col,
                    )
                )

            elif isinstance(entry, UndoCursorMove):
                self.point.move_to(entry.line, entry.col)

        # Append reverse entries to the tail so "undo the undo" works
        # once the cursor resets (i.e., after a non-undo command).
        #
        # Insert a boundary first so the reverse entries form their own
        # group.  Without this, a later chain-break followed by another
        # undo would walk the reverse entries AND the original source
        # group in a single pass, collapsing two user-visible states
        # into one keystroke (Phase 6l-5 regression — see
        # ``test_undo_chain.py``).  Pass ``break_undo_chain=False`` so
        # we don't clobber our own chain state mid-undo.
        if reverse:
            self.add_undo_boundary(break_undo_chain=False)
        self.undo_list.extend(reverse)
        self.last_command_type = "undo"
        return True

    # ------------------------------------------------------------------
    # Kill / yank
    # ------------------------------------------------------------------

    def kill_line(self) -> str:
        """Kill from point to end of line (C-k).

        If point is at end of line, kills the newline (joining lines).
        Consecutive kills merge into the kill ring.
        """
        line = self.lines[self.point.line]
        if self.point.col < len(line):
            # Kill to end of line
            killed = line[self.point.col :]
            end = Mark(self.point.line, len(line))
        elif self.point.line < len(self.lines) - 1:
            # At end of line — kill the newline
            killed = "\n"
            end = Mark(self.point.line + 1, 0)
        else:
            return ""

        self.delete_region(self.point.copy(), end)
        if self.last_command_type == "kill":
            self.kill_ring.append_to_top(killed)
        else:
            self.kill_ring.push(killed)
        self.last_command_type = "kill"
        return killed

    def kill_region(self) -> str:
        """Kill the region (text between point and mark, C-w).

        Returns the killed text, or empty string if no mark.
        """
        if self.mark is None:
            return ""
        start = self.point.copy()
        end = self.mark.copy()
        killed = self.delete_region(start, end)
        self.clear_mark()
        if killed:
            if self.last_command_type == "kill":
                self.kill_ring.append_to_top(killed)
            else:
                self.kill_ring.push(killed)
        self.last_command_type = "kill"
        return killed

    def kill_sentence(self) -> str:
        """Kill from point to end of current sentence (M-k).

        If point is at a sentence end (punctuation), kills through the
        whitespace up to the next sentence.
        """
        start = self.point.copy()
        self._move_sentence_forward()
        end = self.point.copy()
        if start == end:
            return ""
        self.point.move_to(start.line, start.col)
        killed = self.delete_region(start, end)
        if self.last_command_type == "kill":
            self.kill_ring.append_to_top(killed)
        else:
            self.kill_ring.push(killed)
        self.last_command_type = "kill"
        return killed

    def kill_word_forward(self) -> str:
        """Kill from point to the end of the current word (M-d)."""
        start = self.point.copy()
        self._move_word_forward()
        end = self.point.copy()
        if start == end:
            return ""
        # Move point back to start — delete_region will handle position
        self.point.move_to(start.line, start.col)
        killed = self.delete_region(start, end)
        if self.last_command_type == "kill":
            self.kill_ring.append_to_top(killed)
        else:
            self.kill_ring.push(killed)
        self.last_command_type = "kill"
        return killed

    def kill_word_backward(self) -> str:
        """Kill from point to the start of the current/previous word (M-Backspace)."""
        end = self.point.copy()
        self._move_word_backward()
        start = self.point.copy()
        if start == end:
            return ""
        killed = self.delete_region(start, end)
        if self.last_command_type == "kill":
            self.kill_ring.append_to_top(killed, before=True)
        else:
            self.kill_ring.push(killed)
        self.last_command_type = "kill"
        return killed

    def yank(self) -> str | None:
        """Yank (paste) the most recent kill at point (C-y).

        Returns the yanked text, or None if kill ring is empty.
        """
        text = self.kill_ring.yank()
        if text is None:
            return None
        # Record the start so yank_pop can replace
        self._yank_start = self.point.copy()
        self.insert_string(text)
        self._yank_end = self.point.copy()
        self.last_command_type = "yank"
        return text

    def yank_pop(self) -> str | None:
        """Replace the just-yanked text with the next kill ring entry (M-y).

        Only works immediately after yank or yank_pop.  Returns the
        new text, or None if not applicable.
        """
        if self.last_command_type != "yank":
            return None
        text = self.kill_ring.rotate()
        if text is None:
            return None
        # Delete the previously yanked text
        if hasattr(self, "_yank_start") and hasattr(self, "_yank_end"):
            self.delete_region(self._yank_start, self._yank_end)
            self.point.move_to(self._yank_start.line, self._yank_start.col)
        # Insert the rotated text
        self._yank_start = self.point.copy()
        self.insert_string(text)
        self._yank_end = self.point.copy()
        self.last_command_type = "yank"
        return text

    def forward_word(self, n: int = 1) -> bool:
        """Move point forward by *n* words (M-f).

        A word is a sequence of alphanumeric or underscore characters.
        Skips non-word chars first, then the word itself.
        """
        self._goal_col = -1
        moved = False
        for _ in range(n):
            if self._move_word_forward():
                moved = True
        return moved

    def backward_word(self, n: int = 1) -> bool:
        """Move point backward by *n* words (M-b).

        Moves to the beginning of the current or previous word.
        """
        self._goal_col = -1
        moved = False
        for _ in range(n):
            if self._move_word_backward():
                moved = True
        return moved

    def _move_word_forward(self) -> bool:
        """Move point forward by one word.  Returns True if moved."""
        start = self.point.to_tuple()
        # Skip non-word characters
        while self.point.col < len(self.lines[self.point.line]):
            ch = self.lines[self.point.line][self.point.col]
            if ch.isalnum() or ch == "_":
                break
            self.point.col += 1
        else:
            # Reached end of line — cross to next if possible
            if self.point.line < len(self.lines) - 1:
                self.point.line += 1
                self.point.col = 0
                return True
            return self.point.to_tuple() != start
        # Skip word characters
        while self.point.col < len(self.lines[self.point.line]):
            ch = self.lines[self.point.line][self.point.col]
            if not (ch.isalnum() or ch == "_"):
                break
            self.point.col += 1
        return self.point.to_tuple() != start

    def _move_word_backward(self) -> bool:
        """Move point backward by one word.  Returns True if moved."""
        start = self.point.to_tuple()
        # Skip non-word characters backward
        while self.point.col > 0:
            ch = self.lines[self.point.line][self.point.col - 1]
            if ch.isalnum() or ch == "_":
                break
            self.point.col -= 1
        else:
            if self.point.col == 0 and self.point.line > 0:
                self.point.line -= 1
                self.point.col = len(self.lines[self.point.line])
                return True
            if self.point.col == 0:
                return False
        # Skip word characters backward
        while self.point.col > 0:
            ch = self.lines[self.point.line][self.point.col - 1]
            if not (ch.isalnum() or ch == "_"):
                break
            self.point.col -= 1
        return self.point.to_tuple() != start

    # ------------------------------------------------------------------
    # Sentence motion
    # ------------------------------------------------------------------

    _SENTENCE_ENDINGS = frozenset(".?!")

    def forward_sentence(self, n: int = 1) -> bool:
        """Move point forward by *n* sentences (M-e).

        A sentence ends at ``.``, ``?``, or ``!`` followed by whitespace,
        end-of-line, or end-of-buffer.  Point lands after the terminating
        punctuation.
        """
        self._goal_col = -1
        moved = False
        for _ in range(n):
            if self._move_sentence_forward():
                moved = True
        return moved

    def backward_sentence(self, n: int = 1) -> bool:
        """Move point backward by *n* sentences (M-a).

        Moves to the start of the current or previous sentence.
        """
        self._goal_col = -1
        moved = False
        for _ in range(n):
            if self._move_sentence_backward():
                moved = True
        return moved

    def _move_sentence_forward(self) -> bool:
        """Move forward to the end of the next sentence."""
        start = self.point.to_tuple()
        ln = self.point.line
        col = self.point.col

        while ln < len(self.lines):
            line = self.lines[ln]
            while col < len(line):
                ch = line[col]
                if ch in self._SENTENCE_ENDINGS:
                    # Found a sentence-ending character.
                    # The sentence ends after this char if followed by
                    # whitespace, end-of-line, or end-of-buffer.
                    after_col = col + 1
                    if after_col >= len(line):
                        # End of line or buffer — sentence ends here
                        self.point.move_to(ln, after_col)
                        return self.point.to_tuple() != start
                    if line[after_col].isspace():
                        self.point.move_to(ln, after_col)
                        return self.point.to_tuple() != start
                col += 1
            # Move to next line
            ln += 1
            col = 0

        # Reached end of buffer
        self.point.move_to(len(self.lines) - 1, len(self.lines[-1]))
        return self.point.to_tuple() != start

    def _move_sentence_backward(self) -> bool:
        """Move backward to the start of the current or previous sentence."""
        start = self.point.to_tuple()
        ln = self.point.line
        col = self.point.col

        # Skip whitespace at/before point to get past any sentence gap
        while True:
            if col > 0:
                if self.lines[ln][col - 1].isspace():
                    col -= 1
                    continue
                # If we're right after a sentence-ending char, skip it too
                if self.lines[ln][col - 1] in self._SENTENCE_ENDINGS:
                    col -= 1
                    continue
                break
            elif ln > 0:
                ln -= 1
                col = len(self.lines[ln])
            else:
                break

        # Now scan backward to find the end of the previous sentence
        # (a sentence-ending char followed by whitespace/EOL),
        # then land after the whitespace that follows it.
        while True:
            if col > 0:
                col -= 1
                ch = self.lines[ln][col]
                if ch in self._SENTENCE_ENDINGS:
                    # Found a sentence boundary — land after the subsequent
                    # whitespace (which is the start of the next sentence).
                    pos_ln, pos_col = ln, col + 1
                    # Skip whitespace/newlines forward from here
                    while pos_ln < len(self.lines):
                        line = self.lines[pos_ln]
                        while pos_col < len(line):
                            if not line[pos_col].isspace():
                                self.point.move_to(pos_ln, pos_col)
                                return self.point.to_tuple() != start
                            pos_col += 1
                        pos_ln += 1
                        pos_col = 0
                    # Reached end of buffer
                    self.point.move_to(len(self.lines) - 1, len(self.lines[-1]))
                    return self.point.to_tuple() != start
            elif ln > 0:
                ln -= 1
                col = len(self.lines[ln])
            else:
                break

        # No previous sentence boundary — go to beginning of buffer
        self.point.move_to(0, 0)
        return self.point.to_tuple() != start

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def find_forward(
        self,
        text: str,
        from_line: int = -1,
        from_col: int = -1,
        *,
        case_fold: bool = False,
    ) -> tuple[int, int] | None:
        """Find *text* forward from the given position (default: point).

        *text* may contain ``\\n`` to match across line boundaries.  When
        ``case_fold`` is true, matching is case-insensitive; returned
        positions refer to the original (un-lowercased) text.

        Returns ``(line, col)`` of the match's start, or ``None``.
        """
        if not text:
            return None
        if from_line < 0:
            from_line = self.point.line
        if from_col < 0:
            from_col = self.point.col

        needle = text.lower() if case_fold else text

        if "\n" not in needle:
            # Fast path: single-line scan
            for ln in range(from_line, len(self.lines)):
                line = self.lines[ln]
                haystack = line.lower() if case_fold else line
                start = from_col if ln == from_line else 0
                idx = haystack.find(needle, start)
                if idx >= 0:
                    return (ln, idx)
            return None

        # Multi-line path: split needle on newlines.  The first part
        # must match a suffix of the starting line (so the implicit
        # line-break aligns with the needle's first ``\n``); middle
        # parts must match whole intervening lines exactly; the last
        # part must match a prefix of the final line.
        parts = needle.split("\n")
        n = len(parts)
        first_part = parts[0]
        last_part = parts[-1]
        for ln in range(from_line, len(self.lines) - (n - 1)):
            line = self.lines[ln]
            haystack = line.lower() if case_fold else line
            start = from_col if ln == from_line else 0
            if not haystack.endswith(first_part):
                continue
            col = len(haystack) - len(first_part)
            if col < start:
                continue
            ok = True
            for i in range(1, n - 1):
                mid_line = self.lines[ln + i]
                mid_hay = mid_line.lower() if case_fold else mid_line
                if mid_hay != parts[i]:
                    ok = False
                    break
            if not ok:
                continue
            last_line = self.lines[ln + n - 1]
            last_hay = last_line.lower() if case_fold else last_line
            if not last_hay.startswith(last_part):
                continue
            return (ln, col)
        return None

    def find_backward(
        self,
        text: str,
        from_line: int = -1,
        from_col: int = -1,
        *,
        case_fold: bool = False,
    ) -> tuple[int, int] | None:
        """Find *text* backward from the given position (default: point).

        Finds the rightmost match that *starts* before ``from_col`` on
        ``from_line`` (or earlier).  *text* may contain ``\\n``; when
        ``case_fold`` is true, matching is case-insensitive.

        Returns ``(line, col)`` of the match's start, or ``None``.
        """
        if not text:
            return None
        if from_line < 0:
            from_line = self.point.line
        if from_col < 0:
            from_col = self.point.col

        needle = text.lower() if case_fold else text

        if "\n" not in needle:
            # Fast path: single-line scan
            for ln in range(from_line, -1, -1):
                line = self.lines[ln]
                haystack = line.lower() if case_fold else line
                limit = from_col if ln == from_line else len(line)
                # Find rightmost match whose start < limit.
                best = -1
                pos = 0
                while True:
                    idx = haystack.find(needle, pos)
                    if idx < 0 or idx >= limit:
                        break
                    best = idx
                    pos = idx + 1
                if best >= 0:
                    return (ln, best)
            return None

        # Multi-line path.  The match starts at (ln, col) where
        # first_part is a suffix of lines[ln]; col is determined
        # uniquely per line.
        parts = needle.split("\n")
        n = len(parts)
        first_part = parts[0]
        last_part = parts[-1]
        for ln in range(from_line, -1, -1):
            if ln + n - 1 >= len(self.lines):
                continue
            line = self.lines[ln]
            haystack = line.lower() if case_fold else line
            if not haystack.endswith(first_part):
                continue
            col = len(haystack) - len(first_part)
            if ln == from_line and col >= from_col:
                continue
            ok = True
            for i in range(1, n - 1):
                mid_line = self.lines[ln + i]
                mid_hay = mid_line.lower() if case_fold else mid_line
                if mid_hay != parts[i]:
                    ok = False
                    break
            if not ok:
                continue
            last_line = self.lines[ln + n - 1]
            last_hay = last_line.lower() if case_fold else last_line
            if not last_hay.startswith(last_part):
                continue
            return (ln, col)
        return None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def _clamp_point(self) -> None:
        """Ensure point is within valid buffer bounds."""
        self.point.line = max(0, min(self.point.line, len(self.lines) - 1))
        self.point.col = max(0, min(self.point.col, len(self.lines[self.point.line])))
