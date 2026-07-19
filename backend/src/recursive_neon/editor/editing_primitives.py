"""Capability-free editing primitives shared by editor command profiles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer


def auto_fill_break(buffer: Buffer, fill_column: int) -> None:
    """Break the current line at the last space before ``fill_column``."""
    line = buffer.lines[buffer.point.line]
    break_column = line.rfind(" ", 0, fill_column)
    if break_column <= 0:
        return

    saved_line = buffer.point.line
    saved_column = buffer.point.col
    buffer.point.move_to(saved_line, break_column)
    buffer.delete_char_forward()
    buffer.insert_char("\n")
    if saved_column > break_column:
        buffer.point.move_to(
            saved_line + 1,
            saved_column - break_column - 1,
        )
    else:
        buffer.point.move_to(saved_line, saved_column)
