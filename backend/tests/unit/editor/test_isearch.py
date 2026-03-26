"""Tests for incremental search (C-s / C-r)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


# ═══════════════════════════════════════════════════════════════════════
# Buffer.find_forward / find_backward
# ═══════════════════════════════════════════════════════════════════════


class TestFindForward:
    def test_find_on_same_line(self):
        b = Buffer.from_text("hello world")
        assert b.find_forward("world") == (0, 6)

    def test_find_from_middle(self):
        b = Buffer.from_text("abcabc")
        assert b.find_forward("abc", 0, 1) == (0, 3)

    def test_find_on_later_line(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        assert b.find_forward("ccc", 0, 0) == (2, 0)

    def test_not_found(self):
        b = Buffer.from_text("hello")
        assert b.find_forward("xyz") is None

    def test_empty_pattern(self):
        b = Buffer.from_text("hello")
        assert b.find_forward("") is None


class TestFindBackward:
    def test_find_on_same_line(self):
        b = Buffer.from_text("hello world")
        assert b.find_backward("hello", 0, 11) == (0, 0)

    def test_find_before_cursor(self):
        b = Buffer.from_text("abcabc")
        assert b.find_backward("abc", 0, 5) == (0, 3)

    def test_find_on_earlier_line(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        assert b.find_backward("aaa", 2, 3) == (0, 0)

    def test_not_found(self):
        b = Buffer.from_text("hello")
        assert b.find_backward("xyz", 0, 5) is None


# ═══════════════════════════════════════════════════════════════════════
# Isearch via Editor
# ═══════════════════════════════════════════════════════════════════════


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestIsearchForward:
    def test_c_s_opens_minibuffer(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        assert ed.minibuffer is not None
        assert "I-search" in ed.minibuffer.prompt

    def test_typing_moves_point_to_match(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        assert ed.buffer.point.col == 6  # "world" starts at 6

    def test_enter_exits_at_match(self):
        ed = make_editor("hello world")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        ed.process_key("Enter")
        assert ed.minibuffer is None
        assert ed.buffer.point.col == 6

    def test_c_g_restores_original_position(self):
        ed = make_editor("hello world")
        ed.buffer.point.col = 2
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        assert ed.buffer.point.col == 6  # found match
        ed.process_key("C-g")
        assert ed.minibuffer is None
        assert ed.buffer.point.col == 2  # restored

    def test_c_s_repeats_search(self):
        ed = make_editor("aaa bbb aaa ccc")
        ed.process_key("C-s")
        ed.process_key("a")
        ed.process_key("a")
        ed.process_key("a")
        assert ed.buffer.point.col == 0  # first "aaa"
        ed.process_key("C-s")  # repeat
        assert ed.buffer.point.col == 8  # second "aaa"

    def test_no_match_shows_failing(self):
        ed = make_editor("hello")
        ed.process_key("C-s")
        ed.process_key("z")
        assert ed.minibuffer is not None
        assert "Failing" in ed.minibuffer.prompt

    def test_exit_and_replay(self):
        ed = make_editor("hello world\nsecond line")
        ed.process_key("C-s")
        ed.process_key("w")
        ed.process_key("o")
        assert ed.buffer.point.col == 6  # at "world"
        # C-n is not a minibuffer key — should exit isearch and move down
        ed.process_key("C-n")
        assert ed.minibuffer is None
        assert ed.buffer.point.line == 1  # moved to second line


class TestIsearchBackward:
    def test_c_r_opens_minibuffer(self):
        ed = make_editor("hello world")
        ed.process_key("C-r")
        assert ed.minibuffer is not None
        assert "backward" in ed.minibuffer.prompt.lower()

    def test_backward_search_finds_before_point(self):
        ed = make_editor("hello world hello")
        ed.buffer.end_of_buffer()
        ed.process_key("C-r")
        ed.process_key("h")
        ed.process_key("e")
        assert ed.buffer.point.col == 12  # second "hello"

    def test_c_r_repeats_backward(self):
        ed = make_editor("aaa bbb aaa")
        ed.buffer.end_of_buffer()
        ed.process_key("C-r")
        ed.process_key("a")
        ed.process_key("a")
        ed.process_key("a")
        # First backward match at col 8
        assert ed.buffer.point.col == 8
        ed.process_key("C-r")
        # Second backward match at col 0
        assert ed.buffer.point.col == 0


class TestIsearchMultiLine:
    def test_search_across_lines(self):
        ed = make_editor("aaa\nbbb\nccc\nbbb")
        ed.process_key("C-s")
        ed.process_key("b")
        ed.process_key("b")
        ed.process_key("b")
        assert ed.buffer.point.line == 1
        ed.process_key("C-s")  # repeat
        assert ed.buffer.point.line == 3

    def test_backward_search_across_lines(self):
        ed = make_editor("aaa\nbbb\nccc")
        ed.buffer.end_of_buffer()
        ed.process_key("C-r")
        ed.process_key("a")
        ed.process_key("a")
        assert ed.buffer.point.line == 0
