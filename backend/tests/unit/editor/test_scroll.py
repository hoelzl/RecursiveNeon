"""Tests for viewport scrolling commands (scroll-up, scroll-down, recenter)."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from tests.unit.editor.harness import make_harness


def _long_text(n: int = 30) -> str:
    """Return *n* lines of text."""
    return "\n".join(f"line {i}" for i in range(n))


# ═══════════════════════════════════════════════════════════════════════
# scroll-up (C-v / PageDown)
# ═══════════════════════════════════════════════════════════════════════


class TestScrollUp:
    def test_scrolls_forward_one_screenful(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height  # 8
        h.send_keys("C-v")
        assert h.view.scroll_top == text_h
        assert h.point() == (text_h, 0)

    def test_point_moves_to_top_of_new_viewport(self):
        h = make_harness(_long_text(30), height=10)
        h.send_keys("C-v")
        assert h.point()[0] == h.view.scroll_top

    def test_does_not_scroll_past_last_line(self):
        h = make_harness(_long_text(10), height=10)
        # text_height = 8, 10 lines total
        h.send_keys("C-v")
        h.send_keys("C-v")
        assert h.view.scroll_top <= 9
        assert h.point()[0] <= 9

    def test_prefix_arg_scrolls_n_lines(self):
        h = make_harness(_long_text(30), height=10)
        # C-u 3 C-v should scroll 3 lines
        h.send_keys("C-u")
        h.type_string("3")
        h.send_keys("C-v")
        assert h.view.scroll_top == 3
        assert h.point() == (3, 0)

    def test_pagedown_key_binding(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        h.send_keys("PageDown")
        assert h.view.scroll_top == text_h

    def test_noop_without_viewport(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text=_long_text(30))
        assert ed.viewport is None
        ed.process_key("C-v")
        # Should not crash; point unchanged
        assert ed.buffer.point.line == 0


# ════════════════════════════════════════════════���══════════════════════
# scroll-down (M-v / PageUp)
# ═════════════════════════════════════════════════════��═════════════════


class TestScrollDown:
    def test_scrolls_backward_one_screenful(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height  # 8
        # Scroll forward first
        h.send_keys("C-v")
        assert h.view.scroll_top == text_h
        # Now scroll back
        h.send_keys("M-v")
        assert h.view.scroll_top == 0

    def test_point_moves_to_bottom_of_new_viewport(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        h.send_keys("C-v")
        h.send_keys("M-v")
        # Point should be at last visible line of viewport
        assert h.point()[0] == text_h - 1

    def test_does_not_scroll_above_zero(self):
        h = make_harness(_long_text(30), height=10)
        h.send_keys("M-v")
        assert h.view.scroll_top == 0

    def test_prefix_arg_scrolls_n_lines(self):
        h = make_harness(_long_text(30), height=10)
        # Scroll forward first
        h.send_keys("C-v")
        old_top = h.view.scroll_top
        # C-u 3 M-v should scroll back 3 lines
        h.send_keys("C-u")
        h.type_string("3")
        h.send_keys("M-v")
        assert h.view.scroll_top == old_top - 3

    def test_pageup_key_binding(self):
        h = make_harness(_long_text(30), height=10)
        h.send_keys("C-v")
        h.send_keys("PageUp")
        assert h.view.scroll_top == 0

    def test_noop_without_viewport(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text=_long_text(30))
        ed.process_key("M-v")
        assert ed.buffer.point.line == 0


# ═════════════════════════════════════════════════════════════��═════════
# recenter (C-l)
# ═══════════════════════════════════════════════════════════════════════


class TestRecenter:
    def test_centers_viewport_around_point(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height  # 8
        # Move point to line 15
        for _ in range(15):
            h.send_keys("C-n")
        h.send_keys("C-l")
        expected_top = 15 - text_h // 2
        assert h.view.scroll_top == expected_top

    def test_consecutive_cycles_to_top(self):
        h = make_harness(_long_text(30), height=10)
        for _ in range(15):
            h.send_keys("C-n")
        h.send_keys("C-l")  # center
        h.send_keys("C-l")  # top
        assert h.view.scroll_top == 15  # cursor at top of viewport

    def test_consecutive_cycles_to_bottom(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        for _ in range(15):
            h.send_keys("C-n")
        h.send_keys("C-l")  # center
        h.send_keys("C-l")  # top
        h.send_keys("C-l")  # bottom
        expected_top = 15 - text_h + 1
        assert h.view.scroll_top == expected_top

    def test_cycle_wraps_back_to_center(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        for _ in range(15):
            h.send_keys("C-n")
        h.send_keys("C-l")  # center
        h.send_keys("C-l")  # top
        h.send_keys("C-l")  # bottom
        h.send_keys("C-l")  # center again
        expected_top = 15 - text_h // 2
        assert h.view.scroll_top == expected_top

    def test_non_consecutive_resets_to_center(self):
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        for _ in range(15):
            h.send_keys("C-n")
        h.send_keys("C-l")  # center
        h.send_keys("C-l")  # top
        h.send_keys("C-f")  # break the chain
        h.send_keys("C-l")  # should be center again, not bottom
        expected_top = 15 - text_h // 2
        assert h.view.scroll_top == expected_top

    def test_noop_without_viewport(self):
        ed = Editor(global_keymap=build_default_keymap())
        ed.create_buffer(text=_long_text(30))
        ed.process_key("C-l")
        # No crash


# ═══════════════════════════════════════════��═══════════════════════════
# Viewport protocol
# ═══════════════════════════════════════════════════════════════════════


class TestViewportProtocol:
    def test_editor_viewport_is_none_without_view(self):
        ed = Editor(global_keymap=build_default_keymap())
        assert ed.viewport is None

    def test_editor_view_sets_viewport(self):
        h = make_harness("hello")
        assert h.editor.viewport is h.view

    def test_scroll_to_clamps_negative(self):
        h = make_harness("hello")
        h.view.scroll_to(-5)
        assert h.view.scroll_top == 0

    def test_scroll_top_reflects_state(self):
        h = make_harness(_long_text(30), height=10)
        h.send_keys("C-v")
        assert h.view.scroll_top == h.view.text_height
