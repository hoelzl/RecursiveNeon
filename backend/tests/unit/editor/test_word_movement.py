"""Tests for word movement, additional keybindings, and read-only buffers."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.mark import Mark


# ═══════════════════════════════════════════════════════════════════════
# forward_word
# ═══════════════════════════════════════════════════════════════════════


class TestForwardWord:
    def test_skip_to_end_of_word(self):
        b = Buffer.from_text("hello world")
        b.forward_word()
        assert b.point.col == 5

    def test_skip_spaces_then_word(self):
        b = Buffer.from_text("hello world")
        b.point.col = 5
        b.forward_word()
        assert b.point.col == 11

    def test_at_end_of_buffer(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        assert not b.forward_word()

    def test_crosses_line_boundary(self):
        b = Buffer.from_text("hello\nworld")
        b.point.col = 5
        b.forward_word()
        # Should cross to next line
        assert b.point.line == 1

    def test_multiple_words(self):
        b = Buffer.from_text("one two three")
        b.forward_word(2)
        assert b.point.col == 7  # past "one two"

    def test_underscores_are_word_chars(self):
        b = Buffer.from_text("hello_world foo")
        b.forward_word()
        assert b.point.col == 11  # "hello_world"

    def test_punctuation_stops_word(self):
        b = Buffer.from_text("foo.bar")
        b.forward_word()
        assert b.point.col == 3  # stops at "."


# ═══════════════════════════════════════════════════════════════════════
# backward_word
# ═══════════════════════════════════════════════════════════════════════


class TestBackwardWord:
    def test_skip_to_start_of_word(self):
        b = Buffer.from_text("hello world")
        b.point.col = 11
        b.backward_word()
        assert b.point.col == 6

    def test_skip_spaces_then_word(self):
        b = Buffer.from_text("hello world")
        b.point.col = 6
        b.backward_word()
        assert b.point.col == 0

    def test_at_start_of_buffer(self):
        b = Buffer.from_text("hello")
        assert not b.backward_word()

    def test_crosses_line_boundary(self):
        b = Buffer.from_text("hello\nworld")
        b.point.line = 1
        b.point.col = 0
        b.backward_word()
        assert b.point.line == 0

    def test_multiple_words(self):
        b = Buffer.from_text("one two three")
        b.point.col = 13
        b.backward_word(2)
        assert b.point.col == 4  # start of "two"

    def test_mid_word(self):
        b = Buffer.from_text("hello world")
        b.point.col = 8
        b.backward_word()
        assert b.point.col == 6  # start of "world"


# ═══════════════════════════════════════════════════════════════════════
# kill_word_backward
# ═══════════════════════════════════════════════════════════════════════


class TestKillBackwardWord:
    def test_kill_word_backward(self):
        b = Buffer.from_text("hello world")
        b.point.col = 11
        killed = b.kill_word_backward()
        assert killed == "world"
        assert b.text == "hello "

    def test_kill_at_start_returns_empty(self):
        b = Buffer.from_text("hello")
        killed = b.kill_word_backward()
        assert killed == ""

    def test_consecutive_kills_prepend(self):
        b = Buffer.from_text("one two three")
        b.point.col = 13
        b.kill_word_backward()  # "three"
        b.kill_word_backward()  # "two " (prepends)
        assert b.kill_ring.top == "two three"


# ═══════════════════════════════════════════════════════════════════════
# Additional keybindings via Editor
# ═══════════════════════════════════════════════════════════════════════


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestAdditionalKeybindings:
    def test_m_f_forward_word(self):
        ed = make_editor("hello world")
        ed.process_key("M-f")
        assert ed.buffer.point.col == 5

    def test_m_b_backward_word(self):
        ed = make_editor("hello world")
        ed.buffer.point.col = 11
        ed.process_key("M-b")
        assert ed.buffer.point.col == 6

    def test_delete_key(self):
        ed = make_editor("hello")
        ed.process_key("Delete")
        assert ed.buffer.text == "ello"

    def test_home_key(self):
        ed = make_editor("hello")
        ed.buffer.point.col = 3
        ed.process_key("Home")
        assert ed.buffer.point.col == 0

    def test_end_key(self):
        ed = make_editor("hello")
        ed.process_key("End")
        assert ed.buffer.point.col == 5

    def test_m_backspace_kills_word_backward(self):
        ed = make_editor("hello world")
        ed.buffer.point.col = 11
        ed.process_key("M-Backspace")
        assert ed.buffer.text == "hello "

    def test_m_d_kills_word_forward(self):
        ed = make_editor("hello world")
        ed.process_key("M-d")
        assert ed.buffer.text == " world"


# ═══════════════════════════════════════════════════════════════════════
# Read-only buffers
# ═══════════════════════════════════════════════════════════════════════


class TestReadOnlyBuffer:
    def test_insert_char_rejected(self):
        b = Buffer.from_text("hello")
        b.read_only = True
        b.insert_char("x")
        assert b.text == "hello"

    def test_insert_string_rejected(self):
        b = Buffer.from_text("hello")
        b.read_only = True
        b.insert_string("world")
        assert b.text == "hello"

    def test_delete_forward_rejected(self):
        b = Buffer.from_text("hello")
        b.read_only = True
        result = b.delete_char_forward()
        assert result is None
        assert b.text == "hello"

    def test_delete_backward_rejected(self):
        b = Buffer.from_text("hello")
        b.read_only = True
        b.point.col = 5
        result = b.delete_char_backward()
        assert result is None
        assert b.text == "hello"

    def test_delete_region_rejected(self):
        b = Buffer.from_text("hello")
        b.read_only = True
        result = b.delete_region(Mark(0, 0), Mark(0, 5))
        assert result == ""
        assert b.text == "hello"

    def test_movement_still_works(self):
        b = Buffer.from_text("hello world")
        b.read_only = True
        b.forward_char(5)
        assert b.point.col == 5
        b.forward_word()
        assert b.point.col == 11

    def test_not_read_only_by_default(self):
        b = Buffer()
        assert not b.read_only
