"""Tests for python-mode TAB indentation (python-indent-line).

TAB indents to the syntactic level and cycles through the candidate
levels on repeated TAB; python-mode also shows the ElDoc lighter. TAB in
text/fundamental buffers keeps the indent-relative behaviour.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import register_language_modes
from recursive_neon.editor.modes.python_mode import _python_indent_levels

register_language_modes()  # ensure python-mode is in the registry


def make_py_editor(text: str) -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    ed.set_major_mode("python-mode")
    return ed


class TestPythonIndentLevels:
    def test_levels_under_colon_header(self) -> None:
        ed = make_py_editor("def foo():\n    if y:\nz\n")
        ed.buffer.point.move_to(2, 0)  # line 3 ("z")
        assert _python_indent_levels(ed.buffer) == [8, 4, 0]

    def test_levels_after_plain_statement(self) -> None:
        ed = make_py_editor("    a = 1\nb\n")
        ed.buffer.point.move_to(1, 0)  # line 2 ("b"), prev "    a = 1"
        assert _python_indent_levels(ed.buffer) == [4, 0]


class TestPythonIndentCycle:
    def test_tab_cycles_through_levels(self) -> None:
        ed = make_py_editor("def foo():\n    if y:\nz\n")
        ed.buffer.point.move_to(2, 0)
        ed.process_key("Tab")
        assert ed.buffer.point.col == 8
        assert ed.buffer.lines[2] == "        z"
        ed.process_key("Tab")
        assert ed.buffer.point.col == 4
        assert ed.buffer.lines[2] == "    z"
        ed.process_key("Tab")
        assert ed.buffer.point.col == 0
        assert ed.buffer.lines[2] == "z"
        ed.process_key("Tab")  # wraps
        assert ed.buffer.point.col == 8

    def test_non_repeated_tab_resets_to_calculated(self) -> None:
        ed = make_py_editor("def foo():\n    if y:\nz\n")
        ed.buffer.point.move_to(2, 0)
        ed.process_key("Tab")  # → 8
        ed.process_key("Tab")  # → 4
        # An intervening command breaks the cycle; the next TAB recomputes.
        ed.process_key("C-a")
        ed.process_key("Tab")
        assert ed.buffer.point.col == 8  # back to the calculated level


class TestPythonModeEldocLighter:
    def test_python_mode_shows_eldoc_lighter(self) -> None:
        ed = make_py_editor("x = 1\n")
        assert any(m.name == "eldoc-mode" for m in ed.buffer.minor_modes)
        eldoc = next(m for m in ed.buffer.minor_modes if m.name == "eldoc-mode")
        assert eldoc.indicator == "ElDoc"

    def test_eldoc_lighter_removed_when_leaving_python_mode(self) -> None:
        """Switching away from python-mode must not leak the ElDoc lighter."""
        ed = make_py_editor("x = 1\n")
        assert any(m.name == "eldoc-mode" for m in ed.buffer.minor_modes)
        ed.set_major_mode("text-mode")
        assert not any(m.name == "eldoc-mode" for m in ed.buffer.minor_modes)


class TestTextModeIndentUnaffected:
    def test_text_mode_still_indent_relative(self) -> None:
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text="  word1   word2\n\n")
        ed.set_major_mode("text-mode")
        ed.buffer.point.move_to(1, 0)  # empty line 2
        ed.process_key("Tab")
        assert ed.buffer.point.col == 2  # indent-relative to the word above
