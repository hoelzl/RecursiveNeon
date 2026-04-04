"""Tests for window commands (split, navigate, delete, scroll-other, find-file-other)."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# split-window-below  (C-x 2)
# ═══════════════════════════════════════════════════════════════════════


class TestSplitWindowBelow:
    def test_splits_into_two_windows(self):
        h = make_harness("hello\nworld", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        assert tree is not None
        assert len(tree.windows()) == 2

    def test_both_show_same_buffer(self):
        h = make_harness("hello\nworld", width=40, height=12)
        h.send_keys("C-x", "2")
        wins = h.editor._window_tree.windows()
        assert wins[0].buffer is wins[1].buffer

    def test_active_stays_on_first(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        assert tree.active is tree.windows()[0]


# ═══════════════════════════════════════════════════════════════════════
# split-window-right  (C-x 3)
# ═══════════════════════════════════════════════════════════════════════


class TestSplitWindowRight:
    def test_splits_into_two_windows(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "3")
        tree = h.editor._window_tree
        assert len(tree.windows()) == 2

    def test_both_show_same_buffer(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "3")
        wins = h.editor._window_tree.windows()
        assert wins[0].buffer is wins[1].buffer


# ═══════════════════════════════════════════════════════════════════════
# other-window  (C-x o)
# ═══════════════════════════════════════════════════════════════════════


class TestOtherWindow:
    def test_switches_active_window(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        w1, w2 = tree.windows()
        assert tree.active is w1
        h.send_keys("C-x", "o")
        assert tree.active is w2

    def test_cycles_back(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        w1, w2 = tree.windows()
        h.send_keys("C-x", "o")
        h.send_keys("C-x", "o")
        assert tree.active is w1

    def test_single_window_shows_message(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "o")
        assert "Only one window" in h.message_line()

    def test_typing_in_different_windows(self):
        h = make_harness("", width=40, height=12)
        # Create second buffer
        h.editor.create_buffer(name="b2", text="")
        h.send_keys("C-x", "2")
        # Switch to other window and switch to buffer b2
        h.send_keys("C-x", "o")
        h.editor.switch_to_buffer("b2")
        h.editor._window_tree.active.buffer = h.editor.buffer
        h.editor._window_tree.active._point = h.editor.buffer.point.copy(kind="right")
        h.editor.buffer.track_mark(h.editor._window_tree.active._point)
        h.editor._window_tree.active.sync_from_buffer()
        # Type in window 2
        h.type_string("BBB")
        assert h.editor.buffer.text == "BBB"
        # Switch back
        h.send_keys("C-x", "o")
        # Original buffer should be empty
        assert h.editor.buffer.text == ""

    def test_independent_points(self):
        h = make_harness("hello\nworld\nfoo", width=40, height=12)
        # Move to line 2 in first window
        h.send_keys("C-n", "C-n")
        assert h.point() == (2, 0)
        h.send_keys("C-x", "2")
        # Switch to second window — it starts at same position
        h.send_keys("C-x", "o")
        # Move back to line 0 in second window
        h.send_keys("C-p", "C-p")
        assert h.point() == (0, 0)
        # Switch back to first window — should still be at line 2
        h.send_keys("C-x", "o")
        assert h.point() == (2, 0)


# ═══════════════════════════════════════════════════════════════════════
# delete-window  (C-x 0)
# ═══════════════════════════════════════════════════════════════════════


class TestDeleteWindow:
    def test_deletes_active_window(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        assert len(tree.windows()) == 2
        h.send_keys("C-x", "0")
        assert len(tree.windows()) == 1

    def test_sole_window_shows_error(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "0")
        assert "sole" in h.message_line().lower()

    def test_switches_to_remaining(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        w2 = tree.windows()[1]
        h.send_keys("C-x", "0")
        assert tree.active is w2


# ═══════════════════════════════════════════════════════════════════════
# delete-other-windows  (C-x 1)
# ═══════════════════════════════════════════════════════════════════════


class TestDeleteOtherWindows:
    def test_collapses_to_one(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        h.send_keys("C-x", "3")
        tree = h.editor._window_tree
        assert len(tree.windows()) >= 2
        h.send_keys("C-x", "1")
        assert tree.is_single()

    def test_already_single_shows_message(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "1")
        assert (
            "already" in h.message_line().lower() or "only" in h.message_line().lower()
        )


# ═══════════════════════════════════════════════════════════════════════
# scroll-other-window  (C-M-v)
# ═══════════════════════════════════════════════════════════════════════


class TestScrollOtherWindow:
    def test_scrolls_other_window(self):
        text = "\n".join(f"line {i}" for i in range(30))
        h = make_harness(text, width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        other = tree.other_window()
        assert other is not None
        old_scroll = other.scroll_top
        h.send_keys("C-M-v")
        assert other.scroll_top > old_scroll

    def test_single_window_shows_message(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-M-v")
        assert "Only one window" in h.message_line()


# ═══════════════════════════════════════════════════════════════════════
# find-file-other-window  (C-x 4 C-f)
# ═══════════════════════════════════════════════════════════════════════


class TestFindFileOtherWindow:
    def test_splits_and_opens_file(self):
        h = make_harness("hello", width=40, height=12)
        h.editor.open_callback = lambda path: f"content of {path}"
        h.send_keys("C-x", "4", "C-f")
        h.type_string("test.txt")
        h.send_keys("Enter")
        tree = h.editor._window_tree
        # Should have split
        assert len(tree.windows()) == 2
        # Active window should show the new file
        assert h.editor.buffer.name == "test.txt"

    def test_uses_existing_split(self):
        h = make_harness("hello", width=40, height=12)
        h.editor.open_callback = lambda path: f"content of {path}"
        h.send_keys("C-x", "2")  # split first
        h.send_keys("C-x", "4", "C-f")
        h.type_string("test.txt")
        h.send_keys("Enter")
        tree = h.editor._window_tree
        # Should still have 2 windows (no additional split)
        assert len(tree.windows()) == 2


# ═══════════════════════════════════════════════════════════════════════
# Headless mode (no EditorView)
# ═══════════════════════════════════════════════════════════════════════


class TestWindowCommandsHeadless:
    def test_split_noops_without_window_tree(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text="hello")
        assert ed._window_tree is None
        ed.process_key("C-x")
        ed.process_key("2")
        assert "No window system" in ed.message

    def test_other_window_noops_without_tree(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text="hello")
        ed.process_key("C-x")
        ed.process_key("o")
        assert "Only one window" in ed.message

    def test_delete_window_noops_without_tree(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text="hello")
        ed.process_key("C-x")
        ed.process_key("0")
        assert "sole" in ed.message.lower() or "delete" in ed.message.lower()
