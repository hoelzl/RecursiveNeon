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


class TestFindForwardMultiLine:
    def test_two_line_needle(self):
        b = Buffer.from_text("xa\nby")
        # "a\nb" matches starting at (0, 1): 'a' at end of line 0, 'b' at start of line 1
        assert b.find_forward("a\nb", 0, 0) == (0, 1)

    def test_three_line_needle(self):
        b = Buffer.from_text("prefix\nmiddle\nsuffix")
        # "x\nmiddle\ns" — 'x' suffix of line 0, 'middle' == line 1, 's' prefix of line 2
        assert b.find_forward("x\nmiddle\ns", 0, 0) == (0, 5)

    def test_first_part_must_be_suffix(self):
        b = Buffer.from_text("ab\ncd")
        # "a\nc" — 'a' is NOT a suffix of "ab" (would need 'b'), so no match
        assert b.find_forward("a\nc", 0, 0) is None
        # "b\nc" — 'b' IS a suffix of "ab", 'c' is prefix of "cd"
        assert b.find_forward("b\nc", 0, 0) == (0, 1)

    def test_last_part_must_be_prefix(self):
        b = Buffer.from_text("ab\ncd")
        # "b\nd" — 'd' is NOT a prefix of "cd" (would need 'c'), so no match
        assert b.find_forward("b\nd", 0, 0) is None

    def test_middle_part_must_match_whole_line(self):
        b = Buffer.from_text("a\nmid\nz")
        # "a\nmid\nz" — middle line must match exactly
        assert b.find_forward("a\nmid\nz", 0, 0) == (0, 0)
        # "a\nmi\nz" — "mi" != "mid" (whole-line requirement), no match
        assert b.find_forward("a\nmi\nz", 0, 0) is None

    def test_empty_first_part(self):
        b = Buffer.from_text("xx\nab")
        # "\na" — first part is empty, matches at end of any line
        assert b.find_forward("\na", 0, 0) == (0, 2)

    def test_empty_last_part(self):
        b = Buffer.from_text("ab\ncd")
        # "ab\n" — first part 'ab' is suffix of line 0, last part '' matches any prefix
        assert b.find_forward("ab\n", 0, 0) == (0, 0)

    def test_bare_newline(self):
        b = Buffer.from_text("abc\ndef")
        # "\n" — matches at end of any line with a following line
        assert b.find_forward("\n", 0, 0) == (0, 3)

    def test_from_col_respected(self):
        b = Buffer.from_text("ab\nab\ncd")
        # First match is at (0, 1), second at (1, 1)
        assert b.find_forward("b\n", 0, 0) == (0, 1)
        assert b.find_forward("b\n", 0, 2) == (1, 1)

    def test_no_match_returns_none(self):
        b = Buffer.from_text("abc\ndef")
        assert b.find_forward("x\ny", 0, 0) is None


class TestFindBackwardMultiLine:
    def test_two_line_needle(self):
        b = Buffer.from_text("xa\nby")
        # Search backward from end
        assert b.find_backward("a\nb", 1, 2) == (0, 1)

    def test_rightmost_match(self):
        b = Buffer.from_text("ab\ncd\nab\ncd")
        # Two candidate matches at (0, 0) and (2, 0); backward from (3, 2) picks (2, 0)
        assert b.find_backward("ab\ncd", 3, 2) == (2, 0)

    def test_start_before_from_col(self):
        b = Buffer.from_text("ab\ncd")
        # Match starts at col 1, so from_col must exceed 1 on the start line
        assert b.find_backward("b\nc", 0, 1) is None
        # On a later line, any from_col counts
        assert b.find_backward("b\nc", 1, 0) == (0, 1)

    def test_no_match(self):
        b = Buffer.from_text("abc\ndef")
        assert b.find_backward("x\ny", 1, 3) is None


class TestFindForwardCaseFold:
    def test_case_fold_matches_uppercase_needle(self):
        b = Buffer.from_text("hello world")
        assert b.find_forward("HELLO", 0, 0, case_fold=True) == (0, 0)

    def test_case_fold_matches_mixed_haystack(self):
        b = Buffer.from_text("Hello World")
        assert b.find_forward("hello", 0, 0, case_fold=True) == (0, 0)
        assert b.find_forward("world", 0, 0, case_fold=True) == (0, 6)

    def test_case_sensitive_by_default(self):
        b = Buffer.from_text("hello world")
        assert b.find_forward("HELLO", 0, 0) is None

    def test_case_fold_multi_line(self):
        b = Buffer.from_text("Foo\nBAR")
        assert b.find_forward("foo\nbar", 0, 0, case_fold=True) == (0, 0)

    def test_returned_position_refers_to_original(self):
        # Even though case_fold lowercases internally, the returned
        # (line, col) refers to the un-lowercased buffer.
        b = Buffer.from_text("XYZHelloXYZ")
        pos = b.find_forward("HELLO", 0, 0, case_fold=True)
        assert pos == (0, 3)
        assert b.lines[0][3:8] == "Hello"  # original case preserved


class TestFindBackwardCaseFold:
    def test_case_fold_backward(self):
        b = Buffer.from_text("hello World hello")
        assert b.find_backward("WORLD", 0, 17, case_fold=True) == (0, 6)

    def test_case_fold_backward_multi_line(self):
        b = Buffer.from_text("FOO\nbaz\nfoo\nbaz")
        # Two candidates: (0, 0) and (2, 0); backward picks the later one
        assert b.find_backward("foo\nbaz", 3, 3, case_fold=True) == (2, 0)


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
