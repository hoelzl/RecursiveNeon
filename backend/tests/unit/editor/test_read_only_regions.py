"""Tests for Buffer read-only regions (Phase 7a-1)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer, ReadOnlyRegion
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.mark import Mark

# ------------------------------------------------------------------
# ReadOnlyRegion helpers
# ------------------------------------------------------------------


class TestReadOnlyRegionContains:
    def test_inside(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 10))
        assert r.contains(0, 5)

    def test_at_start_boundary(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 10))
        assert r.contains(0, 0)  # start is inclusive

    def test_at_end_boundary(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 10))
        assert not r.contains(0, 10)  # end is exclusive

    def test_outside_before(self):
        r = ReadOnlyRegion(Mark(0, 5), Mark(0, 10))
        assert not r.contains(0, 3)

    def test_outside_after(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 10))
        assert not r.contains(0, 15)

    def test_multiline_inside(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(3, 0))
        assert r.contains(1, 5)

    def test_multiline_at_end_line(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(3, 5))
        assert r.contains(3, 4)
        assert not r.contains(3, 5)

    def test_reversed_marks(self):
        """Region with start > end still works (swapped internally)."""
        r = ReadOnlyRegion(Mark(0, 10), Mark(0, 0))
        assert r.contains(0, 5)
        assert not r.contains(0, 10)


class TestReadOnlyRegionOverlaps:
    def test_contained(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 10))
        assert r.overlaps(0, 2, 0, 5)

    def test_partial_left(self):
        r = ReadOnlyRegion(Mark(0, 5), Mark(0, 15))
        assert r.overlaps(0, 3, 0, 8)

    def test_partial_right(self):
        r = ReadOnlyRegion(Mark(0, 5), Mark(0, 15))
        assert r.overlaps(0, 10, 0, 20)

    def test_no_overlap_before(self):
        r = ReadOnlyRegion(Mark(0, 10), Mark(0, 20))
        assert not r.overlaps(0, 0, 0, 10)

    def test_no_overlap_after(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(0, 5))
        assert not r.overlaps(0, 5, 0, 10)

    def test_multiline_overlap(self):
        r = ReadOnlyRegion(Mark(0, 0), Mark(3, 0))
        assert r.overlaps(2, 0, 4, 0)


# ------------------------------------------------------------------
# Buffer read-only region API
# ------------------------------------------------------------------


class TestBufferReadOnlyAPI:
    def test_add_and_query(self):
        buf = Buffer.from_text("hello world")
        s = Mark(0, 0, kind="left")
        e = Mark(0, 5, kind="left")
        buf.add_read_only_region(s, e)
        assert buf.is_read_only_at(0, 3)
        assert not buf.is_read_only_at(0, 7)

    def test_remove_region(self):
        buf = Buffer.from_text("hello world")
        s = Mark(0, 0, kind="left")
        e = Mark(0, 5, kind="left")
        region = buf.add_read_only_region(s, e)
        buf.remove_read_only_region(region)
        assert not buf.is_read_only_at(0, 3)

    def test_clear_regions(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.add_read_only_region(Mark(0, 7, kind="left"), Mark(0, 11, kind="left"))
        buf.clear_read_only_regions()
        assert not buf.is_read_only_at(0, 3)
        assert not buf.is_read_only_at(0, 8)

    def test_marks_are_tracked(self):
        buf = Buffer.from_text("hello world")
        s = Mark(0, 0, kind="left")
        e = Mark(0, 5, kind="left")
        buf.add_read_only_region(s, e)
        # s and e should be in tracked marks
        assert any(m is s for m in buf._tracked_marks)
        assert any(m is e for m in buf._tracked_marks)

    def test_remove_untracks_marks(self):
        buf = Buffer.from_text("hello world")
        s = Mark(0, 0, kind="left")
        e = Mark(0, 5, kind="left")
        region = buf.add_read_only_region(s, e)
        buf.remove_read_only_region(region)
        assert not any(m is s for m in buf._tracked_marks)
        assert not any(m is e for m in buf._tracked_marks)

    def test_remove_nonexistent_is_noop(self):
        buf = Buffer.from_text("hello")
        region = ReadOnlyRegion(Mark(0, 0), Mark(0, 5))
        buf.remove_read_only_region(region)  # should not raise


# ------------------------------------------------------------------
# Mutation enforcement
# ------------------------------------------------------------------


class TestInsertBlocked:
    def test_insert_char_in_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 3)
        buf.insert_char("X")
        assert buf.lines[0] == "hello world"  # unchanged
        assert buf._read_only_error

    def test_insert_char_outside_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 7)
        buf.insert_char("X")
        assert buf.lines[0] == "hello wXorld"
        assert not buf._read_only_error

    def test_insert_string_in_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        buf.insert_string("XYZ")
        assert buf.lines[0] == "hello world"
        assert buf._read_only_error

    def test_insert_at_end_boundary_allowed(self):
        """Insertion exactly at the end boundary is outside the region."""
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 5)
        buf.insert_char("X")
        assert buf.lines[0] == "helloX world"
        assert not buf._read_only_error


class TestDeleteBlocked:
    def test_delete_forward_in_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        result = buf.delete_char_forward()
        assert result is None
        assert buf.lines[0] == "hello world"
        assert buf._read_only_error

    def test_delete_backward_in_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 3)
        result = buf.delete_char_backward()
        assert result is None
        assert buf.lines[0] == "hello world"
        assert buf._read_only_error

    def test_delete_backward_at_boundary(self):
        """Backspace at the end boundary deletes the last protected char."""
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 5)
        result = buf.delete_char_backward()
        assert result is None
        assert buf._read_only_error

    def test_delete_forward_outside_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 7)
        result = buf.delete_char_forward()
        assert result == "o"  # "hello world"[7] == 'o'
        assert not buf._read_only_error

    def test_delete_region_overlapping_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        result = buf.delete_region(Mark(0, 3), Mark(0, 8))
        assert result == ""
        assert buf.lines[0] == "hello world"
        assert buf._read_only_error

    def test_delete_region_outside_read_only(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        result = buf.delete_region(Mark(0, 6), Mark(0, 11))
        assert result == "world"
        assert not buf._read_only_error


class TestProgrammaticBypass:
    """Mutations with _undo_recording=False bypass read-only checks."""

    def test_insert_with_undo_off(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        buf._undo_recording = False
        buf.insert_char("X")
        buf._undo_recording = True
        assert buf.lines[0] == "heXllo world"
        assert not buf._read_only_error

    def test_delete_with_undo_off(self):
        buf = Buffer.from_text("hello world")
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        buf._undo_recording = False
        result = buf.delete_char_forward()
        buf._undo_recording = True
        assert result == "l"
        assert not buf._read_only_error


# ------------------------------------------------------------------
# Mark tracking — regions adjust as surrounding text changes
# ------------------------------------------------------------------


class TestRegionTracking:
    def test_region_adjusts_on_insert_before(self):
        """Inserting text before a region shifts it right."""
        buf = Buffer.from_text("hello world")
        s = Mark(0, 5, kind="left")
        e = Mark(0, 10, kind="left")
        buf.add_read_only_region(s, e)
        # Insert at position 0 (before the region)
        buf.point.move_to(0, 0)
        buf.insert_string("XX")
        # Region should have shifted right by 2
        # _insert_within_line: m.col > col → shift right by length
        # col=0, s.col=5 → 5 > 0 → s.col becomes 7
        assert s.col == 7
        assert e.col == 12
        # Position 6 is NOT read-only (before the shifted region)
        assert not buf.is_read_only_at(0, 6)
        # Position 8 (inside shifted region) IS read-only
        assert buf.is_read_only_at(0, 8)

    def test_region_adjusts_on_insert_after(self):
        """Inserting text after a region doesn't change it."""
        buf = Buffer.from_text("hello world")
        s = Mark(0, 0, kind="left")
        e = Mark(0, 5, kind="left")
        buf.add_read_only_region(s, e)
        buf.point.move_to(0, 8)
        buf.insert_string("XX")
        assert s.col == 0
        assert e.col == 5


# ------------------------------------------------------------------
# Editor-level message
# ------------------------------------------------------------------


class TestEditorReadOnlyMessage:
    def _make_editor(self) -> Editor:
        from recursive_neon.editor.default_commands import build_default_keymap

        ed = Editor()
        ed.global_keymap = build_default_keymap()
        return ed

    def test_self_insert_shows_message(self):
        ed = self._make_editor()
        buf = ed.buffer
        buf.insert_string("hello world")
        buf.point.move_to(0, 0)
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        # Simulate typing 'x'
        ed.process_key("x")
        assert ed.message == "Text is read-only"
        assert buf.lines[0] == "hello world"

    def test_delete_shows_message(self):
        ed = self._make_editor()
        buf = ed.buffer
        buf.insert_string("hello world")
        buf.point.move_to(0, 0)
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 2)
        ed.process_key("C-d")
        assert ed.message == "Text is read-only"

    def test_no_message_outside_region(self):
        ed = self._make_editor()
        buf = ed.buffer
        buf.insert_string("hello world")
        buf.point.move_to(0, 0)
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 7)
        ed.process_key("x")
        assert ed.message != "Text is read-only"


# ------------------------------------------------------------------
# Whole-buffer read_only still works independently
# ------------------------------------------------------------------


class TestWholeBufferReadOnlyIndependent:
    def test_whole_buffer_still_blocks(self):
        buf = Buffer.from_text("hello")
        buf.read_only = True
        buf.point.move_to(0, 2)
        buf.insert_char("X")
        assert buf.lines[0] == "hello"

    def test_region_plus_whole_buffer(self):
        buf = Buffer.from_text("hello world")
        buf.read_only = True
        buf.add_read_only_region(Mark(0, 0, kind="left"), Mark(0, 5, kind="left"))
        buf.point.move_to(0, 7)
        # Whole-buffer flag blocks even outside the region
        buf.insert_char("X")
        assert buf.lines[0] == "hello world"
