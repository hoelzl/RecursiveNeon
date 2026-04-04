"""Tests for Window, WindowSplit, and WindowTree (editor/window.py)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.window import (
    SplitDirection,
    Window,
    WindowTree,
)

# ═══════════════════════════════════════════════════════════════════════
# Window basics
# ═══════════════════════════════════════════════════════════════════════


class TestWindow:
    def test_for_buffer_creates_tracked_point(self):
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        assert win.buffer is buf
        assert win._point.line == 0
        assert win._point.col == 0
        assert win._point in buf._tracked_marks

    def test_for_buffer_copies_current_point(self):
        buf = Buffer(text="hello\nworld")
        buf.point.move_to(1, 3)
        win = Window.for_buffer(buf)
        assert win._point.line == 1
        assert win._point.col == 3

    def test_text_height(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        win._height = 10
        assert win.text_height == 9  # height minus modeline

    def test_text_height_minimum(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        win._height = 1
        assert win.text_height == 1  # never below 1

    def test_scroll_to_clamps(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        win.scroll_to(-5)
        assert win.scroll_top == 0

    def test_sync_from_buffer(self):
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        buf.point.move_to(1, 3)
        win.sync_from_buffer()
        assert win._point.line == 1
        assert win._point.col == 3

    def test_sync_to_buffer(self):
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        win._point.move_to(1, 4)
        win.sync_to_buffer()
        assert buf.point.line == 1
        assert buf.point.col == 4

    def test_ensure_cursor_visible_scrolls_down(self):
        buf = Buffer(text="\n".join(f"line {i}" for i in range(20)))
        win = Window.for_buffer(buf)
        win._height = 5  # text_height = 4
        win._point.move_to(8, 0)
        win.ensure_cursor_visible()
        assert win.scroll_top <= 8
        assert win.scroll_top + win.text_height > 8

    def test_ensure_cursor_visible_scrolls_up(self):
        buf = Buffer(text="\n".join(f"line {i}" for i in range(20)))
        win = Window.for_buffer(buf)
        win._height = 5
        win.scroll_top = 10
        win._point.move_to(3, 0)
        win.ensure_cursor_visible()
        assert win.scroll_top == 3

    def test_detach_untracks_mark(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        assert any(m is win._point for m in buf._tracked_marks)
        win.detach()
        assert not any(m is win._point for m in buf._tracked_marks)

    def test_tracked_mark_adjusts_on_insert(self):
        """Window point should adjust when text is inserted before it."""
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        win._point.move_to(1, 0)
        # Insert a line at the beginning
        buf.point.move_to(0, 0)
        buf.insert_char("\n")
        # Window point should have shifted down by one line
        assert win._point.line == 2
        assert win._point.col == 0


# ═══════════════════════════════════════════════════════════════════════
# WindowTree basics
# ═══════════════════════════════════════════════════════════════════════


class TestWindowTree:
    def test_single_window(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        assert tree.is_single()
        assert tree.active is win
        assert tree.windows() == [win]

    def test_other_window_single(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        assert tree.other_window() is None


# ═══════════════════════════════════════════════════════════════════════
# Splitting
# ═══════════════════════════════════════════════════════════════════════


class TestWindowTreeSplit:
    def test_horizontal_split(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        new = tree.split(SplitDirection.HORIZONTAL)
        assert not tree.is_single()
        assert tree.active is win  # active stays on original
        assert new.buffer is buf
        assert tree.windows() == [win, new]

    def test_vertical_split(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        new = tree.split(SplitDirection.VERTICAL)
        assert not tree.is_single()
        assert tree.windows() == [win, new]

    def test_split_copies_point(self):
        buf = Buffer(text="hello\nworld")
        buf.point.move_to(1, 3)
        win = Window.for_buffer(buf)
        win.sync_from_buffer()
        tree = WindowTree(win)
        new = tree.split(SplitDirection.HORIZONTAL)
        assert new._point.line == 1
        assert new._point.col == 3

    def test_split_copies_scroll(self):
        buf = Buffer(text="\n".join(f"line {i}" for i in range(30)))
        win = Window.for_buffer(buf)
        win.scroll_top = 5
        tree = WindowTree(win)
        new = tree.split(SplitDirection.HORIZONTAL)
        assert new.scroll_top == 5

    def test_double_split_produces_three_windows(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        tree.split(SplitDirection.HORIZONTAL)
        tree.split(SplitDirection.HORIZONTAL)
        assert len(tree.windows()) == 3

    def test_new_window_point_is_tracked(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        new = tree.split(SplitDirection.HORIZONTAL)
        assert new._point in buf._tracked_marks


# ═══════════════════════════════════════════════════════════════════════
# Navigation
# ═══════════════════════════════════════════════════════════════════════


class TestWindowTreeNavigation:
    def test_next_window_cycles(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        assert tree.active is win
        result = tree.next_window()
        assert result is w2
        assert tree.active is w2
        result = tree.next_window()
        assert result is win  # wraps around

    def test_prev_window_cycles(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        result = tree.prev_window()
        assert result is w2  # wraps backward
        result = tree.prev_window()
        assert result is win

    def test_other_window_returns_next(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        assert tree.other_window() is w2


# ═══════════════════════════════════════════════════════════════════════
# Deletion
# ═══════════════════════════════════════════════════════════════════════


class TestWindowTreeDeletion:
    def test_delete_sole_window_returns_none(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        assert tree.delete_window() is None

    def test_delete_window_collapses_tree(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        # Delete the active (first) window
        new_active = tree.delete_window()
        assert new_active is w2
        assert tree.is_single()
        assert tree.active is w2

    def test_delete_second_window(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        # Switch to second, then delete it
        tree.next_window()
        assert tree.active is w2
        new_active = tree.delete_window()
        assert new_active is win
        assert tree.is_single()

    def test_delete_detaches_mark(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        w2_point = w2._point
        # Delete the active window (win)
        tree.delete_window()
        # The deleted window's mark should be untracked
        assert not any(m is win._point for m in buf._tracked_marks)
        # The surviving window's mark should still be tracked
        assert any(m is w2_point for m in buf._tracked_marks)

    def test_delete_other_windows(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        w3 = tree.split(SplitDirection.HORIZONTAL)
        tree.delete_other_windows()
        assert tree.is_single()
        assert tree.active is win
        assert tree.windows() == [win]
        # Other windows should be detached
        assert not any(m is w2._point for m in buf._tracked_marks)
        assert not any(m is w3._point for m in buf._tracked_marks)

    def test_delete_in_three_window_tree(self):
        buf = Buffer(text="hello")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        tree.active = w2
        tree.split(SplitDirection.VERTICAL)
        # Tree: [win, [w2, w3]]
        assert len(tree.windows()) == 3
        # Delete w2 — should collapse inner split, leaving [win, w3]
        tree.active = w2
        tree.delete_window()
        assert len(tree.windows()) == 2
        assert w2 not in tree.windows()


# ═══════════════════════════════════════════════════════════════════════
# Same-buffer multi-window point tracking
# ═══════════════════════════════════════════════════════════════════════


class TestSameBufferPointTracking:
    def test_two_windows_same_buffer_independent_points(self):
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        # Move points independently
        win._point.move_to(0, 3)
        w2._point.move_to(1, 2)
        assert win._point.line == 0
        assert w2._point.line == 1

    def test_insert_adjusts_other_window_point(self):
        buf = Buffer(text="hello\nworld")
        win = Window.for_buffer(buf)
        tree = WindowTree(win)
        w2 = tree.split(SplitDirection.HORIZONTAL)
        w2._point.move_to(1, 0)
        # Insert a newline at beginning via buffer.point
        buf.point.move_to(0, 0)
        buf.insert_char("\n")
        # w2's point should have shifted down
        assert w2._point.line == 2
