"""Tests for the Buffer class — creation, text access, insertion,
deletion, mark maintenance, and point movement."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.mark import Mark

# ═══════════════════════════════════════════════════════════════════════
# Creation and text access
# ═══════════════════════════════════════════════════════════════════════


class TestBufferCreation:
    def test_empty_buffer_has_one_empty_line(self):
        b = Buffer()
        assert b.lines == [""]
        assert b.line_count == 1

    def test_name_defaults_to_scratch(self):
        assert Buffer().name == "*scratch*"

    def test_custom_name(self):
        assert Buffer(name="foo").name == "foo"

    def test_from_text_single_line(self):
        b = Buffer.from_text("hello")
        assert b.lines == ["hello"]

    def test_from_text_multi_line(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        assert b.lines == ["aaa", "bbb", "ccc"]
        assert b.line_count == 3

    def test_from_text_trailing_newline(self):
        b = Buffer.from_text("hello\n")
        assert b.lines == ["hello", ""]

    def test_point_starts_at_origin(self):
        b = Buffer.from_text("hello")
        assert b.point.line == 0
        assert b.point.col == 0

    def test_point_is_right_inserting(self):
        assert Buffer().point.kind == "right"

    def test_not_modified_initially(self):
        assert not Buffer.from_text("hello").modified

    def test_filepath(self):
        b = Buffer(filepath="/tmp/foo.txt")
        assert b.filepath == "/tmp/foo.txt"


class TestBufferTextAccess:
    def test_text_round_trip(self):
        txt = "line one\nline two\nline three"
        b = Buffer.from_text(txt)
        assert b.text == txt

    def test_current_line(self):
        b = Buffer.from_text("aaa\nbbb")
        assert b.current_line == "aaa"
        b.point.line = 1
        assert b.current_line == "bbb"

    def test_get_text_same_line(self):
        b = Buffer.from_text("hello world")
        assert b.get_text(Mark(0, 0), Mark(0, 5)) == "hello"

    def test_get_text_multi_line(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        assert b.get_text(Mark(0, 1), Mark(2, 2)) == "aa\nbbb\ncc"

    def test_get_text_order_independent(self):
        b = Buffer.from_text("hello world")
        assert b.get_text(Mark(0, 5), Mark(0, 0)) == "hello"

    def test_char_after_point_normal(self):
        b = Buffer.from_text("ab")
        assert b.char_after_point() == "a"

    def test_char_after_point_at_eol_is_newline(self):
        b = Buffer.from_text("ab\ncd")
        b.point.col = 2
        assert b.char_after_point() == "\n"

    def test_char_after_point_at_end_of_buffer(self):
        b = Buffer.from_text("ab")
        b.point.col = 2
        assert b.char_after_point() is None

    def test_char_before_point_normal(self):
        b = Buffer.from_text("ab")
        b.point.col = 2
        assert b.char_before_point() == "b"

    def test_char_before_point_at_bol_is_newline(self):
        b = Buffer.from_text("ab\ncd")
        b.point.line = 1
        b.point.col = 0
        assert b.char_before_point() == "\n"

    def test_char_before_point_at_start_of_buffer(self):
        b = Buffer.from_text("ab")
        assert b.char_before_point() is None


# ═══════════════════════════════════════════════════════════════════════
# Insertion
# ═══════════════════════════════════════════════════════════════════════


class TestInsertChar:
    def test_insert_at_beginning(self):
        b = Buffer.from_text("hello")
        b.insert_char("X")
        assert b.lines == ["Xhello"]
        assert b.point.col == 1

    def test_insert_at_end(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.insert_char("!")
        assert b.lines == ["hello!"]
        assert b.point.col == 6

    def test_insert_in_middle(self):
        b = Buffer.from_text("hllo")
        b.point.col = 1
        b.insert_char("e")
        assert b.lines == ["hello"]
        assert b.point.col == 2

    def test_insert_sets_modified(self):
        b = Buffer.from_text("hello")
        b.insert_char("x")
        assert b.modified


class TestInsertNewline:
    def test_split_at_beginning(self):
        b = Buffer.from_text("hello")
        b.insert_char("\n")
        assert b.lines == ["", "hello"]
        assert b.point == Mark(1, 0)

    def test_split_at_end(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.insert_char("\n")
        assert b.lines == ["hello", ""]
        assert b.point == Mark(1, 0)

    def test_split_in_middle(self):
        b = Buffer.from_text("helloworld")
        b.point.col = 5
        b.insert_char("\n")
        assert b.lines == ["hello", "world"]
        assert b.point == Mark(1, 0)

    def test_split_pushes_later_lines_down(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        b.point.col = 1
        b.insert_char("\n")
        assert b.lines == ["a", "aa", "bbb", "ccc"]


class TestInsertString:
    def test_empty_string_is_noop(self):
        b = Buffer.from_text("hello")
        b.insert_string("")
        assert b.text == "hello"
        assert not b.modified

    def test_single_line_string(self):
        b = Buffer.from_text("hd")
        b.point.col = 1
        b.insert_string("ello worl")
        assert b.lines == ["hello world"]
        assert b.point.col == 10

    def test_multi_line_string(self):
        b = Buffer()
        b.insert_string("line1\nline2\nline3")
        assert b.lines == ["line1", "line2", "line3"]
        assert b.point == Mark(2, 5)

    def test_insert_string_in_middle_of_text(self):
        b = Buffer.from_text("ac")
        b.point.col = 1
        b.insert_string("X\nY\nZ")
        assert b.lines == ["aX", "Y", "Zc"]
        assert b.point == Mark(2, 1)


# ═══════════════════════════════════════════════════════════════════════
# Mark maintenance during insertion
# ═══════════════════════════════════════════════════════════════════════


class TestInsertMarkMaintenance:
    def test_left_mark_stays_left_of_insertion(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 3, "left")
        b.track_mark(m)
        b.point.col = 3
        b.insert_char("X")
        # Left-inserting mark stays at col 3 (before X)
        assert m.col == 3
        # Point (right-inserting) moves to col 4
        assert b.point.col == 4

    def test_right_mark_stays_right_of_insertion(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 3, "right")
        b.track_mark(m)
        b.point.col = 3
        b.insert_char("X")
        # Right-inserting mark moves past the insertion
        assert m.col == 4
        assert b.point.col == 4

    def test_mark_before_insertion_unaffected(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 1, "left")
        b.track_mark(m)
        b.point.col = 3
        b.insert_char("X")
        assert m.col == 1

    def test_mark_after_insertion_shifts_right(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 4, "left")
        b.track_mark(m)
        b.point.col = 2
        b.insert_char("X")
        assert m.col == 5

    def test_newline_marks_on_later_lines_shift_down(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        m = Mark(2, 1, "left")
        b.track_mark(m)
        b.point.col = 1
        b.insert_char("\n")
        # Line 2 was "ccc", now line 3 because of the split at line 0
        assert m.line == 3
        assert m.col == 1

    def test_newline_left_mark_at_split_stays_on_original_line(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 3, "left")
        b.track_mark(m)
        b.point.col = 3
        b.insert_char("\n")
        # Left mark stays on the original line
        assert m.line == 0
        assert m.col == 3

    def test_newline_right_mark_at_split_goes_to_new_line(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 3, "right")
        b.track_mark(m)
        b.point.col = 3
        b.insert_char("\n")
        # Right mark moves to the new line
        assert m.line == 1
        assert m.col == 0

    def test_newline_mark_after_split_moves_to_new_line(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 4, "left")
        b.track_mark(m)
        b.point.col = 2
        b.insert_char("\n")
        # Mark was at col 4, split at col 2 → new line 1, col 4-2=2
        assert m.line == 1
        assert m.col == 2

    def test_set_mark_creates_left_inserting(self):
        b = Buffer.from_text("hello")
        m = b.set_mark(0, 3)
        assert m.kind == "left"
        assert b.mark is m

    def test_region_text(self):
        b = Buffer.from_text("hello world")
        b.point.col = 0
        b.set_mark(0, 5)
        assert b.region_text == "hello"

    def test_clear_mark(self):
        b = Buffer.from_text("hello")
        b.set_mark()
        b.clear_mark()
        assert b.mark is None
        assert not b.region_active


# ═══════════════════════════════════════════════════════════════════════
# Deletion
# ═══════════════════════════════════════════════════════════════════════


class TestDeleteCharForward:
    def test_delete_within_line(self):
        b = Buffer.from_text("hello")
        ch = b.delete_char_forward()
        assert ch == "h"
        assert b.lines == ["ello"]
        assert b.point.col == 0

    def test_delete_at_end_of_line_joins(self):
        b = Buffer.from_text("ab\ncd")
        b.point.col = 2
        ch = b.delete_char_forward()
        assert ch == "\n"
        assert b.lines == ["abcd"]

    def test_delete_at_end_of_buffer_returns_none(self):
        b = Buffer.from_text("ab")
        b.point.col = 2
        assert b.delete_char_forward() is None
        assert b.lines == ["ab"]

    def test_delete_sets_modified(self):
        b = Buffer.from_text("hello")
        b.delete_char_forward()
        assert b.modified


class TestDeleteCharBackward:
    def test_delete_within_line(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        ch = b.delete_char_backward()
        assert ch == "o"
        assert b.lines == ["hell"]
        assert b.point.col == 4

    def test_delete_at_beginning_of_line_joins(self):
        b = Buffer.from_text("ab\ncd")
        b.point.line = 1
        b.point.col = 0
        ch = b.delete_char_backward()
        assert ch == "\n"
        assert b.lines == ["abcd"]
        assert b.point.col == 2

    def test_delete_at_start_of_buffer_returns_none(self):
        b = Buffer.from_text("ab")
        assert b.delete_char_backward() is None
        assert b.lines == ["ab"]


class TestDeleteRegion:
    def test_single_line_delete(self):
        b = Buffer.from_text("hello world")
        deleted = b.delete_region(Mark(0, 5), Mark(0, 11))
        assert deleted == " world"
        assert b.lines == ["hello"]

    def test_multi_line_delete(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        deleted = b.delete_region(Mark(0, 1), Mark(2, 2))
        assert deleted == "aa\nbbb\ncc"
        assert b.lines == ["ac"]

    def test_delete_region_order_independent(self):
        b = Buffer.from_text("hello world")
        deleted = b.delete_region(Mark(0, 11), Mark(0, 5))
        assert deleted == " world"
        assert b.lines == ["hello"]

    def test_empty_region_returns_empty(self):
        b = Buffer.from_text("hello")
        deleted = b.delete_region(Mark(0, 3), Mark(0, 3))
        assert deleted == ""
        assert b.lines == ["hello"]

    def test_delete_entire_line(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        deleted = b.delete_region(Mark(0, 3), Mark(1, 3))
        assert deleted == "\nbbb"
        assert b.lines == ["aaa", "ccc"]

    def test_delete_sets_modified(self):
        b = Buffer.from_text("hello")
        b.delete_region(Mark(0, 0), Mark(0, 3))
        assert b.modified


# ═══════════════════════════════════════════════════════════════════════
# Mark maintenance during deletion
# ═══════════════════════════════════════════════════════════════════════


class TestDeleteMarkMaintenance:
    def test_forward_delete_shifts_marks_left(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 4, "left")
        b.track_mark(m)
        b.delete_char_forward()  # deletes 'h'
        assert m.col == 3

    def test_forward_delete_mark_before_unaffected(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 0, "left")
        b.track_mark(m)
        b.point.col = 3
        b.delete_char_forward()  # deletes 'l'
        assert m.col == 0

    def test_backward_delete_shifts_marks(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 4, "left")
        b.track_mark(m)
        b.point.col = 2
        b.delete_char_backward()  # deletes 'e'
        assert m.col == 3

    def test_join_forward_adjusts_marks_on_next_line(self):
        b = Buffer.from_text("ab\ncd")
        m = Mark(1, 1, "left")
        b.track_mark(m)
        b.point.col = 2
        b.delete_char_forward()  # join lines
        assert m.line == 0
        assert m.col == 3  # 2 (len "ab") + 1

    def test_join_backward_adjusts_marks(self):
        b = Buffer.from_text("ab\ncd")
        m = Mark(1, 1, "left")
        b.track_mark(m)
        b.point.line = 1
        b.point.col = 0
        b.delete_char_backward()  # join lines
        assert m.line == 0
        assert m.col == 3  # 2 (len "ab") + 1

    def test_region_delete_collapses_marks_inside(self):
        b = Buffer.from_text("hello world")
        m = Mark(0, 7, "left")
        b.track_mark(m)
        b.delete_region(Mark(0, 5), Mark(0, 11))
        assert m.col == 5  # collapsed to start of deleted region

    def test_region_delete_shifts_marks_after(self):
        b = Buffer.from_text("hello world")
        b.lines[0] = "hello world!"
        m = Mark(0, 11, "left")
        b.track_mark(m)
        b.delete_region(Mark(0, 5), Mark(0, 10))
        assert m.col == 6  # 11 - (10-5) = 6

    def test_multi_line_region_delete_marks_below_shift_up(self):
        b = Buffer.from_text("aaa\nbbb\nccc\nddd")
        m = Mark(3, 1, "left")
        b.track_mark(m)
        b.delete_region(Mark(1, 0), Mark(2, 3))
        # del removes lines[2:3] (one line), so "ddd" shifts from 3 to 2
        assert m.line == 2
        assert m.col == 1

    def test_multi_line_region_delete_mark_on_last_deleted_line_after_end(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        m = Mark(2, 2, "left")
        b.track_mark(m)
        b.delete_region(Mark(0, 1), Mark(2, 1))
        # Mark was at (2,2), end of deletion at (2,1), so it survives
        # Adjusted to: line=start_ln(0), col=start_col(1) + (2 - 1) = 2
        assert m.line == 0
        assert m.col == 2


# ═══════════════════════════════════════════════════════════════════════
# Point movement
# ═══════════════════════════════════════════════════════════════════════


class TestForwardChar:
    def test_within_line(self):
        b = Buffer.from_text("hello")
        assert b.forward_char()
        assert b.point.col == 1

    def test_across_line_boundary(self):
        b = Buffer.from_text("ab\ncd")
        b.point.col = 2
        assert b.forward_char()
        assert b.point == Mark(1, 0)

    def test_at_end_of_buffer(self):
        b = Buffer.from_text("ab")
        b.point.col = 2
        assert not b.forward_char()

    def test_multiple(self):
        b = Buffer.from_text("hello")
        b.forward_char(3)
        assert b.point.col == 3


class TestBackwardChar:
    def test_within_line(self):
        b = Buffer.from_text("hello")
        b.point.col = 3
        assert b.backward_char()
        assert b.point.col == 2

    def test_across_line_boundary(self):
        b = Buffer.from_text("ab\ncd")
        b.point.line = 1
        b.point.col = 0
        assert b.backward_char()
        assert b.point == Mark(0, 2)

    def test_at_start_of_buffer(self):
        b = Buffer.from_text("ab")
        assert not b.backward_char()

    def test_multiple(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.backward_char(3)
        assert b.point.col == 2


class TestForwardLine:
    def test_simple_down(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        b.point.col = 1
        assert b.forward_line()
        assert b.point == Mark(1, 1)

    def test_clamp_to_shorter_line(self):
        b = Buffer.from_text("long line\nhi")
        b.point.col = 8
        b.forward_line()
        assert b.point == Mark(1, 2)

    def test_goal_column_preserved(self):
        b = Buffer.from_text("long line\nhi\nlong again")
        b.point.col = 8
        b.forward_line()
        assert b.point.col == 2  # clamped
        b.forward_line()
        assert b.point.col == 8  # restored

    def test_at_last_line(self):
        b = Buffer.from_text("aaa\nbbb")
        b.point.line = 1
        assert not b.forward_line()

    def test_multiple_lines(self):
        b = Buffer.from_text("a\nb\nc\nd")
        b.forward_line(3)
        assert b.point.line == 3


class TestBackwardLine:
    def test_simple_up(self):
        b = Buffer.from_text("aaa\nbbb")
        b.point.line = 1
        b.point.col = 2
        assert b.backward_line()
        assert b.point == Mark(0, 2)

    def test_at_first_line(self):
        b = Buffer.from_text("aaa\nbbb")
        assert not b.backward_line()

    def test_goal_column_preserved(self):
        b = Buffer.from_text("long again\nhi\nlong line")
        b.point.line = 2
        b.point.col = 8
        b.backward_line()
        assert b.point.col == 2  # clamped
        b.backward_line()
        assert b.point.col == 8  # restored


class TestLineStartEnd:
    def test_beginning_of_line(self):
        b = Buffer.from_text("hello")
        b.point.col = 3
        b.beginning_of_line()
        assert b.point.col == 0

    def test_end_of_line(self):
        b = Buffer.from_text("hello")
        b.end_of_line()
        assert b.point.col == 5

    def test_beginning_of_buffer(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        b.point.line = 2
        b.point.col = 3
        b.beginning_of_buffer()
        assert b.point == Mark(0, 0)

    def test_end_of_buffer(self):
        b = Buffer.from_text("aaa\nbbb\nccc")
        b.end_of_buffer()
        assert b.point == Mark(2, 3)


class TestGoalColumnReset:
    def test_horizontal_movement_resets_goal(self):
        b = Buffer.from_text("longline\nhi\nlongline")
        b.point.col = 7
        b.forward_line()
        assert b.point.col == 2  # clamped to len("hi")
        # Horizontal move resets goal column
        b.backward_char()  # col = 1
        b.forward_line()
        assert b.point.col == 1  # uses 1, not the old goal of 7

    def test_beginning_of_line_resets_goal(self):
        b = Buffer.from_text("long\nhi\nlong")
        b.point.col = 3
        b.forward_line()  # goal=3, clamped to 2
        b.beginning_of_line()  # resets goal
        b.forward_line()
        assert b.point.col == 0

    def test_end_of_line_resets_goal(self):
        b = Buffer.from_text("long\nhi\nlong")
        b.point.col = 3
        b.forward_line()
        b.end_of_line()  # resets goal
        b.forward_line()
        assert b.point.col == 2  # min(2, 4)


# ═══════════════════════════════════════════════════════════════════════
# Mark tracking lifecycle
# ═══════════════════════════════════════════════════════════════════════


class TestMarkTracking:
    def test_point_is_always_tracked(self):
        b = Buffer()
        assert b.point in b._tracked_marks

    def test_set_mark_adds_to_tracked(self):
        b = Buffer()
        m = b.set_mark()
        assert m in b._tracked_marks

    def test_clear_mark_removes_from_tracked(self):
        b = Buffer()
        m = b.set_mark()
        b.clear_mark()
        # Use identity check — __eq__ compares position only
        assert all(t is not m for t in b._tracked_marks)

    def test_replace_mark_untracks_old(self):
        b = Buffer()
        m1 = b.set_mark(0, 0)
        m2 = b.set_mark(0, 3)
        assert all(t is not m1 for t in b._tracked_marks)
        assert any(t is m2 for t in b._tracked_marks)

    def test_untrack_unknown_mark_is_safe(self):
        b = Buffer()
        b.untrack_mark(Mark(0, 0))  # no-op, no error

    def test_external_tracked_mark_maintained_during_insert(self):
        b = Buffer.from_text("hello")
        m = Mark(0, 5, "left")
        b.track_mark(m)
        b.point.col = 0
        b.insert_string("XX")
        assert m.col == 7  # shifted right by 2


# ═══════════════════════════════════════════════════════════════════════
# Edge cases and integration
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_insert_and_delete_round_trip(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        b.insert_string(" world")
        assert b.text == "hello world"
        # Delete it back
        for _ in range(6):
            b.delete_char_backward()
        assert b.text == "hello"

    def test_split_and_join_round_trip(self):
        b = Buffer.from_text("helloworld")
        b.point.col = 5
        b.insert_char("\n")
        assert b.lines == ["hello", "world"]
        b.point.line = 1
        b.point.col = 0
        b.delete_char_backward()
        assert b.lines == ["helloworld"]

    def test_delete_all_text(self):
        b = Buffer.from_text("ab\ncd")
        b.delete_region(Mark(0, 0), Mark(1, 2))
        assert b.lines == [""]
        assert b.point == Mark(0, 0)

    def test_many_insertions_at_same_point(self):
        b = Buffer()
        for ch in "hello":
            b.insert_char(ch)
        assert b.text == "hello"
        assert b.point.col == 5

    def test_multiline_insert_then_region_delete(self):
        b = Buffer()
        b.insert_string("aaa\nbbb\nccc")
        start = Mark(0, 0)
        end = b.point.copy()
        deleted = b.delete_region(start, end)
        assert deleted == "aaa\nbbb\nccc"
        assert b.text == ""

    def test_mark_and_point_bracket_typed_text(self):
        """Point (right-inserting) and mark (left-inserting) should
        naturally bracket text typed between them."""
        b = Buffer.from_text("hello")
        b.point.col = 3
        m = b.set_mark()  # left-inserting at (0, 3)
        b.insert_string("XY")
        # Mark stays at 3 (left), point at 5 (right)
        assert m.col == 3
        assert b.point.col == 5
        assert b.region_text == "XY"
