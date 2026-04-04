"""Tests for fill-paragraph, set-fill-column, and auto-fill-mode (Phase 6h)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.default_commands import _fill_lines, _find_paragraph_bounds
from recursive_neon.editor.variables import VARIABLES
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# _find_paragraph_bounds (helper)
# ═══════════════════════════════════════════════════════════════════════


class TestFindParagraphBounds:
    def test_single_paragraph(self) -> None:
        buf = Buffer.from_text("hello world\nfoo bar\nbaz")
        assert _find_paragraph_bounds(buf, 0) == (0, 2)

    def test_multiple_paragraphs(self) -> None:
        buf = Buffer.from_text("para one\nstill one\n\npara two\nstill two")
        assert _find_paragraph_bounds(buf, 0) == (0, 1)
        assert _find_paragraph_bounds(buf, 3) == (3, 4)

    def test_middle_of_paragraph(self) -> None:
        buf = Buffer.from_text("a\nb\nc\n\nd\ne")
        assert _find_paragraph_bounds(buf, 1) == (0, 2)

    def test_single_line_paragraph(self) -> None:
        buf = Buffer.from_text("only line")
        assert _find_paragraph_bounds(buf, 0) == (0, 0)

    def test_blank_lines_around(self) -> None:
        buf = Buffer.from_text("\ntext here\n")
        assert _find_paragraph_bounds(buf, 1) == (1, 1)


# ═══════════════════════════════════════════════════════════════════════
# _fill_lines (helper)
# ═══════════════════════════════════════════════════════════════════════


class TestFillLines:
    def test_wrap_long_line(self) -> None:
        lines = ["the quick brown fox jumps over the lazy dog"]
        result = _fill_lines(lines, 20)
        assert result == ["the quick brown fox", "jumps over the lazy", "dog"]

    def test_already_wrapped(self) -> None:
        lines = ["short"]
        result = _fill_lines(lines, 70)
        assert result == ["short"]

    def test_join_short_lines(self) -> None:
        lines = ["a", "b", "c"]
        result = _fill_lines(lines, 70)
        assert result == ["a b c"]

    def test_empty_input(self) -> None:
        result = _fill_lines([""], 70)
        assert result == [""]

    def test_exact_fill_column(self) -> None:
        lines = ["aaaa bbbb"]
        result = _fill_lines(lines, 9)
        assert result == ["aaaa bbbb"]

    def test_word_longer_than_fill_column(self) -> None:
        lines = ["superlongword short"]
        result = _fill_lines(lines, 10)
        # Long word gets its own line
        assert result == ["superlongword", "short"]


# ═══════════════════════════════════════════════════════════════════════
# fill-paragraph command (M-q)
# ═══════════════════════════════════════════════════════════════════════


class TestFillParagraph:
    def test_basic_fill(self) -> None:
        text = "the quick brown fox jumps over the lazy dog"
        h = make_harness(text, width=80)
        h.editor.buffer.set_variable_local("fill-column", 20)
        h.send_keys("M-q")
        assert h.buffer_text() == "the quick brown fox\njumps over the lazy\ndog"

    def test_fill_joins_short_lines(self) -> None:
        h = make_harness("hello\nworld\nfoo", width=80)
        h.editor.buffer.set_variable_local("fill-column", 70)
        h.send_keys("M-q")
        assert h.buffer_text() == "hello world foo"

    def test_fill_respects_paragraph_boundary(self) -> None:
        h = make_harness("para one line one\npara one line two\n\npara two", width=80)
        h.editor.buffer.set_variable_local("fill-column", 70)
        h.send_keys("M-q")
        # Only first paragraph should be affected
        assert h.buffer_text() == "para one line one para one line two\n\npara two"

    def test_fill_second_paragraph(self) -> None:
        h = make_harness("first\n\na b c d e f g h", width=80)
        h.editor.buffer.set_variable_local("fill-column", 10)
        # Move to second paragraph
        h.send_keys("C-n", "C-n")
        h.send_keys("M-q")
        assert h.buffer_text() == "first\n\na b c d e\nf g h"

    def test_fill_on_blank_line(self) -> None:
        h = make_harness("text\n\nmore text", width=80)
        h.send_keys("C-n")  # move to blank line
        h.send_keys("M-q")
        assert "No paragraph" in h.message_line()

    def test_fill_read_only(self) -> None:
        h = make_harness("some text here", width=80)
        h.editor.buffer.read_only = True
        h.send_keys("M-q")
        assert "read-only" in h.message_line()

    def test_fill_unchanged_paragraph(self) -> None:
        h = make_harness("short", width=80)
        h.editor.buffer.set_variable_local("fill-column", 70)
        h.send_keys("M-q")
        assert "unchanged" in h.message_line().lower()

    def test_fill_undoable(self) -> None:
        text = "the quick brown fox jumps over the lazy dog"
        h = make_harness(text, width=80)
        h.editor.buffer.set_variable_local("fill-column", 20)
        h.send_keys("M-q")
        assert h.buffer_text() != text
        h.send_keys("C-/")
        assert h.buffer_text() == text

    def test_fill_message(self) -> None:
        h = make_harness("a b c d e f g h i j k l", width=80)
        h.editor.buffer.set_variable_local("fill-column", 10)
        h.send_keys("M-q")
        assert "Filled" in h.message_line()


# ═══════════════════════════════════════════════════════════════════════
# set-fill-column (C-x f)
# ═══════════════════════════════════════════════════════════════════════


class TestSetFillColumn:
    def _save_fill_column(self) -> int:
        return VARIABLES["fill-column"].default

    def _restore_fill_column(self, val: int) -> None:
        VARIABLES["fill-column"].default = val

    def test_set_with_prefix_arg(self) -> None:
        old = self._save_fill_column()
        try:
            h = make_harness("hello")
            # C-u 40 C-x f
            h.send_keys("C-u")
            h.type_string("40")
            h.send_keys("C-x", "f")
            assert h.editor.get_variable("fill-column") == 40
            assert "40" in h.message_line()
        finally:
            self._restore_fill_column(old)

    def test_set_to_current_column(self) -> None:
        old = self._save_fill_column()
        try:
            h = make_harness("hello world")
            # Move to col 5
            h.send_keys("C-f", "C-f", "C-f", "C-f", "C-f")
            h.send_keys("C-x", "f")
            assert h.editor.get_variable("fill-column") == 5
            assert "5" in h.message_line()
        finally:
            self._restore_fill_column(old)

    def test_set_to_zero_column(self) -> None:
        old = self._save_fill_column()
        try:
            h = make_harness("hello")
            h.send_keys("C-x", "f")
            assert h.editor.get_variable("fill-column") == 0
        finally:
            self._restore_fill_column(old)


# ═══════════════════════════════════════════════════════════════════════
# auto-fill-mode
# ═══════════════════════════════════════════════════════════════════════


class TestAutoFillMode:
    def test_toggle_on(self) -> None:
        h = make_harness("")
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        assert "enabled" in h.message_line()
        # Check minor mode is active
        assert any(m.name == "auto-fill-mode" for m in h.editor.buffer.minor_modes)

    def test_toggle_off(self) -> None:
        h = make_harness("")
        # Toggle on
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        # Toggle off
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        assert "disabled" in h.message_line()
        assert not any(m.name == "auto-fill-mode" for m in h.editor.buffer.minor_modes)

    def test_modeline_shows_fill(self) -> None:
        h = make_harness("", width=80, height=10)
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        modeline = h.modeline()
        assert "Fill" in modeline

    def test_auto_break_on_space(self) -> None:
        h = make_harness("", width=80)
        h.editor.buffer.set_variable_local("fill-column", 15)
        # Enable auto-fill
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        # Type text that exceeds fill-column
        h.type_string("hello world this is long")
        # Should have been broken across lines
        lines = h.buffer_text().split("\n")
        assert len(lines) >= 2
        # No line should exceed fill-column (except possibly words longer than fill-col)
        for line in lines:
            # Allow slight overshoot for words that don't fit
            assert len(line) <= 20  # generous margin

    def test_no_break_without_auto_fill(self) -> None:
        h = make_harness("", width=80)
        h.editor.buffer.set_variable_local("fill-column", 10)
        h.type_string("hello world this is long text")
        # Should remain on one line
        assert h.buffer_text().count("\n") == 0

    def test_auto_fill_respects_fill_column(self) -> None:
        h = make_harness("", width=80)
        h.editor.buffer.set_variable_local("fill-column", 10)
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        # "aaaa bbbb " is 10 chars — the space after "cccc" triggers break
        h.type_string("aaaa bbbb cccc dddd")
        lines = h.buffer_text().split("\n")
        assert len(lines) >= 2

    def test_auto_fill_variable_via_mode(self) -> None:
        """auto-fill-mode sets auto-fill variable to True."""
        h = make_harness("")
        assert h.editor.get_variable("auto-fill") is False
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        assert h.editor.get_variable("auto-fill") is True
