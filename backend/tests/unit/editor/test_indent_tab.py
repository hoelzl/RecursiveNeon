"""Tests for indent-for-tab-command (TAB) — text-mode indent-relative.

TAB indents the current line to the next "indent point" of the nearest
previous non-blank line, falling back to tab-to-tab-stop past the last
point (or on the first line). Verified against GNU Emacs via the parity
harness.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import (
    _indent_points,
    build_default_keymap,
)
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestIndentPoints:
    def test_leading_space_line(self) -> None:
        assert _indent_points("  word1   word2") == [2, 10]

    def test_line_starting_with_word(self) -> None:
        assert _indent_points("word1 word2") == [0, 6]

    def test_blank_and_empty(self) -> None:
        assert _indent_points("") == []
        assert _indent_points("    ") == []


class TestIndentForTabCommand:
    def test_tab_bound(self) -> None:
        ed = make_editor("x")
        assert ed.global_keymap.lookup("Tab") == "indent-for-tab-command"

    def test_indent_relative_cascade(self) -> None:
        ed = make_editor("  word1   word2\n\nrest\n")
        ed.buffer.point.move_to(1, 0)  # empty line 2
        ed.process_key("Tab")
        assert ed.buffer.point.col == 2  # first indent point
        assert ed.buffer.lines[1] == "  "
        ed.process_key("Tab")
        assert ed.buffer.point.col == 10  # second indent point
        ed.process_key("Tab")
        assert ed.buffer.point.col == 16  # tab-to-tab-stop past the last point

    def test_first_line_tab_to_tab_stop(self) -> None:
        ed = make_editor("  word1   word2\n")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("Tab")
        assert ed.buffer.point.col == 8
        # The leading whitespace pushes the original text right.
        assert ed.buffer.lines[0] == "        " + "  word1   word2"

    def test_skips_blank_lines_to_previous_non_blank(self) -> None:
        ed = make_editor("  abc\n\n\n")
        ed.buffer.point.move_to(2, 0)  # second empty line
        ed.process_key("Tab")
        assert ed.buffer.point.col == 2  # indent point of "  abc"

    def test_tab_stop_from_nonzero_column(self) -> None:
        # No previous line; a TAB from a non-zero column rounds up to the
        # next multiple of tab-width.
        ed = make_editor("abcdefghij\n")
        ed.buffer.point.move_to(0, 10)  # past the first tab stop
        ed.process_key("Tab")
        assert ed.buffer.point.col == 16

    def test_tab_is_one_undo_group(self) -> None:
        ed = make_editor("  word\n\n")
        ed.buffer.point.move_to(1, 0)
        ed.process_key("Tab")
        assert ed.buffer.point.col == 2
        ed.execute_command("undo")
        assert ed.buffer.lines[1] == ""
        assert ed.buffer.point.col == 0
