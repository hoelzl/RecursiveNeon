"""Tests for the undo system."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.undo import UndoBoundary, UndoInsert


# ═══════════════════════════════════════════════════════════════════════
# Basic undo of insertions
# ═══════════════════════════════════════════════════════════════════════


class TestUndoInsert:
    def test_undo_single_char(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.insert_char("!")
        assert b.text == "hello!"
        b.undo()
        assert b.text == "hello"

    def test_undo_restores_point(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.insert_char("!")
        assert b.point.col == 6
        b.undo()
        assert b.point.col == 5

    def test_undo_string(self):
        b = Buffer.from_text("hd")
        b.point.col = 1
        b.insert_string("ello worl")
        assert b.text == "hello world"
        b.undo()
        assert b.text == "hd"
        assert b.point.col == 1

    def test_undo_multiline_insert(self):
        b = Buffer()
        b.insert_string("aaa\nbbb\nccc")
        assert b.line_count == 3
        b.undo()
        assert b.text == ""
        assert b.point == Mark(0, 0)

    def test_undo_newline(self):
        b = Buffer.from_text("helloworld")
        b.point.col = 5
        b.insert_char("\n")
        assert b.lines == ["hello", "world"]
        b.undo()
        assert b.lines == ["helloworld"]
        assert b.point.col == 5


# ═══════════════════════════════════════════════════════════════════════
# Basic undo of deletions
# ═══════════════════════════════════════════════════════════════════════


class TestUndoDelete:
    def test_undo_delete_forward(self):
        b = Buffer.from_text("hello")
        b.delete_char_forward()
        assert b.text == "ello"
        b.undo()
        assert b.text == "hello"
        assert b.point.col == 0

    def test_undo_delete_backward(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.delete_char_backward()
        assert b.text == "hell"
        b.undo()
        assert b.text == "hello"
        assert b.point.col == 5

    def test_undo_delete_region(self):
        b = Buffer.from_text("hello world")
        b.delete_region(Mark(0, 5), Mark(0, 11))
        assert b.text == "hello"
        b.undo()
        assert b.text == "hello world"

    def test_undo_delete_multiline(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        b.delete_region(Mark(0, 1), Mark(2, 2))
        b.undo()
        assert b.text == "aaa\nbbb\nccc"

    def test_undo_join_line_forward(self):
        b = Buffer.from_text("ab\ncd")
        b.point.col = 2
        b.delete_char_forward()
        assert b.text == "abcd"
        b.undo()
        assert b.text == "ab\ncd"

    def test_undo_join_line_backward(self):
        b = Buffer.from_text("ab\ncd")
        b.point.line = 1
        b.point.col = 0
        b.delete_char_backward()
        assert b.text == "abcd"
        b.undo()
        assert b.text == "ab\ncd"
        assert b.point.line == 1
        assert b.point.col == 0


# ═══════════════════════════════════════════════════════════════════════
# Undo boundaries and multi-step undo
# ═══════════════════════════════════════════════════════════════════════


class TestUndoBoundary:
    def test_boundary_separates_groups(self):
        b = Buffer()
        b.insert_char("a")
        b.add_undo_boundary()
        b.insert_char("b")
        assert b.text == "ab"
        # First undo reverses second group only
        b.undo()
        assert b.text == "a"
        # Second undo reverses first group
        b.undo()
        assert b.text == ""

    def test_consecutive_boundaries_collapsed(self):
        b = Buffer()
        b.add_undo_boundary()
        b.add_undo_boundary()
        b.add_undo_boundary()
        # Should only have one boundary
        assert sum(1 for e in b.undo_list if isinstance(e, UndoBoundary)) == 1

    def test_undo_multiple_chars_in_one_group(self):
        b = Buffer()
        b.insert_char("h")
        b.insert_char("i")
        assert b.text == "hi"
        # No boundary between them — one undo reverses both
        b.undo()
        assert b.text == ""

    def test_undo_with_interleaved_ops(self):
        b = Buffer()
        b.insert_string("hello")
        b.add_undo_boundary()
        b.point.col = 5
        b.insert_string(" world")
        b.add_undo_boundary()
        # Delete " world"
        b.delete_region(Mark(0, 5), Mark(0, 11))

        assert b.text == "hello"
        b.undo()  # undo delete
        assert b.text == "hello world"
        b.undo()  # undo " world" insert
        assert b.text == "hello"
        b.undo()  # undo "hello" insert
        assert b.text == ""

    def test_undo_on_empty_list_returns_false(self):
        b = Buffer()
        assert not b.undo()

    def test_undo_returns_true_when_undone(self):
        b = Buffer()
        b.insert_char("x")
        assert b.undo()


# ═══════════════════════════════════════════════════════════════════════
# Undo of undo (redo)
# ═══════════════════════════════════════════════════════════════════════


class TestUndoOfUndo:
    def test_undo_undo_reapplies_insert(self):
        b = Buffer()
        b.insert_string("hello")
        b.add_undo_boundary()
        b.undo()
        assert b.text == ""
        # The undo itself added reverse entries; undo again to "redo"
        b.add_undo_boundary()
        b.undo()
        assert b.text == "hello"

    def test_undo_undo_reapplies_delete(self):
        b = Buffer.from_text("hello")
        b.delete_region(Mark(0, 0), Mark(0, 5))
        assert b.text == ""
        b.add_undo_boundary()
        b.undo()
        assert b.text == "hello"
        # Undo the undo — re-delete
        b.add_undo_boundary()
        b.undo()
        assert b.text == ""

    def test_undo_redo_cycle(self):
        b = Buffer()
        b.insert_char("a")
        b.add_undo_boundary()
        b.insert_char("b")
        b.add_undo_boundary()
        assert b.text == "ab"

        b.undo()
        assert b.text == "a"
        b.add_undo_boundary()
        b.undo()  # redo "b"
        assert b.text == "ab"


# ═══════════════════════════════════════════════════════════════════════
# Undo does not record during playback
# ═══════════════════════════════════════════════════════════════════════


class TestUndoRecordingFlag:
    def test_no_undo_entries_when_recording_off(self):
        b = Buffer()
        b._undo_recording = False
        b.insert_char("x")
        assert len(b.undo_list) == 0
        b._undo_recording = True

    def test_undo_entries_accumulate_normally(self):
        b = Buffer()
        b.insert_char("a")
        b.insert_char("b")
        # Each char generates 2 entries (cursor + insert)
        assert len(b.undo_list) == 4
