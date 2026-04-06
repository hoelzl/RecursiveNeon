"""Tests for buffer text attributes (Phase 7a-2)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.text_attr import TextAttr

RED = TextAttr(fg=1)
GREEN = TextAttr(fg=2)
BLUE = TextAttr(fg=4)


class TestEnableAttrs:
    def test_default_none(self):
        buf = Buffer.from_text("hello")
        assert buf._line_attrs is None

    def test_enable(self):
        buf = Buffer.from_text("hello")
        buf.enable_attrs()
        assert buf._line_attrs is not None
        assert len(buf._line_attrs) == 1
        assert len(buf._line_attrs[0]) == 5  # len("hello")
        assert all(a is None for a in buf._line_attrs[0])

    def test_enable_multiline(self):
        buf = Buffer.from_text("ab\ncd\nef")
        buf.enable_attrs()
        assert len(buf._line_attrs) == 3
        assert len(buf._line_attrs[0]) == 2
        assert len(buf._line_attrs[1]) == 2
        assert len(buf._line_attrs[2]) == 2

    def test_enable_idempotent(self):
        buf = Buffer.from_text("hello")
        buf.enable_attrs()
        buf._line_attrs[0][0] = RED
        buf.enable_attrs()  # should not reset
        assert buf._line_attrs[0][0] == RED


class TestInsertStringAttributed:
    def test_basic(self):
        buf = Buffer.from_text("")
        buf.insert_string_attributed([("hello", RED)])
        assert buf.text == "hello"
        assert buf._line_attrs is not None
        assert buf._line_attrs[0] == [RED, RED, RED, RED, RED]

    def test_mixed_runs(self):
        buf = Buffer.from_text("")
        buf.insert_string_attributed([("ab", RED), ("cd", GREEN)])
        assert buf.text == "abcd"
        assert buf._line_attrs[0] == [RED, RED, GREEN, GREEN]

    def test_with_default(self):
        buf = Buffer.from_text("")
        buf.insert_string_attributed([("ab", RED), ("cd", None)])
        assert buf._line_attrs[0] == [RED, RED, None, None]

    def test_multiline(self):
        buf = Buffer.from_text("")
        buf.insert_string_attributed([("ab\ncd", RED)])
        assert buf.text == "ab\ncd"
        assert buf._line_attrs[0] == [RED, RED]
        assert buf._line_attrs[1] == [RED, RED]

    def test_into_existing(self):
        buf = Buffer.from_text("hello")
        buf.enable_attrs()
        buf.point.move_to(0, 2)
        buf.insert_string_attributed([("XX", BLUE)])
        assert buf.text == "heXXllo"
        assert buf._line_attrs[0] == [None, None, BLUE, BLUE, None, None, None]


class TestPlainInsertWithAttrs:
    """Plain insert_string fills with None when attrs layer is active."""

    def test_plain_insert_fills_none(self):
        buf = Buffer.from_text("ab")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED]
        buf.point.move_to(0, 1)
        buf.insert_char("X")
        assert buf.text == "aXb"
        assert buf._line_attrs[0] == [RED, None, RED]

    def test_plain_insert_string(self):
        buf = Buffer.from_text("ab")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED]
        buf.point.move_to(0, 1)
        buf.insert_string("XY")
        assert buf.text == "aXYb"
        assert buf._line_attrs[0] == [RED, None, None, RED]


class TestDeleteWithAttrs:
    def test_delete_forward(self):
        buf = Buffer.from_text("abc")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, GREEN, BLUE]
        buf.point.move_to(0, 1)
        buf.delete_char_forward()
        assert buf.text == "ac"
        assert buf._line_attrs[0] == [RED, BLUE]

    def test_delete_backward(self):
        buf = Buffer.from_text("abc")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, GREEN, BLUE]
        buf.point.move_to(0, 2)
        buf.delete_char_backward()
        assert buf.text == "ac"
        assert buf._line_attrs[0] == [RED, BLUE]

    def test_delete_region_single_line(self):
        buf = Buffer.from_text("abcde")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED, GREEN, GREEN, BLUE]
        buf.delete_region(Mark(0, 1), Mark(0, 4))
        assert buf.text == "ae"
        assert buf._line_attrs[0] == [RED, BLUE]

    def test_delete_region_multiline(self):
        buf = Buffer.from_text("abc\ndef\nghi")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED, RED]
        buf._line_attrs[1] = [GREEN, GREEN, GREEN]
        buf._line_attrs[2] = [BLUE, BLUE, BLUE]
        buf.delete_region(Mark(0, 1), Mark(2, 1))
        assert buf.text == "ahi"
        assert buf._line_attrs[0] == [RED, BLUE, BLUE]


class TestJoinWithAttrs:
    def test_join_line_forward(self):
        buf = Buffer.from_text("ab\ncd")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED]
        buf._line_attrs[1] = [GREEN, GREEN]
        buf.point.move_to(0, 2)
        buf.delete_char_forward()  # delete the \n
        assert buf.text == "abcd"
        assert buf._line_attrs[0] == [RED, RED, GREEN, GREEN]

    def test_join_line_backward(self):
        buf = Buffer.from_text("ab\ncd")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED]
        buf._line_attrs[1] = [GREEN, GREEN]
        buf.point.move_to(1, 0)
        buf.delete_char_backward()  # delete the \n
        assert buf.text == "abcd"
        assert buf._line_attrs[0] == [RED, RED, GREEN, GREEN]


class TestNewlineWithAttrs:
    def test_split_line(self):
        buf = Buffer.from_text("abcd")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, RED, GREEN, GREEN]
        buf.point.move_to(0, 2)
        buf.insert_char("\n")
        assert buf.text == "ab\ncd"
        assert buf._line_attrs[0] == [RED, RED]
        assert buf._line_attrs[1] == [GREEN, GREEN]


class TestUndoWithAttrs:
    def test_undo_insert_attributed(self):
        buf = Buffer.from_text("")
        buf.add_undo_boundary()
        buf.insert_string_attributed([("hello", RED)])
        assert buf.text == "hello"
        assert buf._line_attrs[0] == [RED] * 5

        buf.undo()
        assert buf.text == ""
        assert buf._line_attrs[0] == []

    def test_undo_delete_restores_attrs(self):
        buf = Buffer.from_text("hello")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, GREEN, BLUE, RED, GREEN]
        buf.point.move_to(0, 1)
        buf.add_undo_boundary()
        buf.delete_char_forward()
        assert buf.text == "hllo"
        assert buf._line_attrs[0] == [RED, BLUE, RED, GREEN]

        buf.undo()
        assert buf.text == "hello"
        assert buf._line_attrs[0] == [RED, GREEN, BLUE, RED, GREEN]

    def test_undo_redo_roundtrip(self):
        buf = Buffer.from_text("")
        buf.add_undo_boundary()
        buf.insert_string_attributed([("ab", RED), ("cd", BLUE)])
        assert buf._line_attrs[0] == [RED, RED, BLUE, BLUE]

        # Undo
        buf.undo()
        assert buf.text == ""

        # Redo (undo the undo)
        buf.add_undo_boundary()
        buf.undo()
        assert buf.text == "abcd"
        assert buf._line_attrs[0] == [RED, RED, BLUE, BLUE]

    def test_undo_delete_region_restores_attrs(self):
        buf = Buffer.from_text("abcde")
        buf.enable_attrs()
        buf._line_attrs[0] = [RED, GREEN, BLUE, RED, GREEN]
        buf.add_undo_boundary()
        buf.delete_region(Mark(0, 1), Mark(0, 4))
        assert buf.text == "ae"

        buf.undo()
        assert buf.text == "abcde"
        assert buf._line_attrs[0] == [RED, GREEN, BLUE, RED, GREEN]
