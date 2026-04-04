"""Tests for window rendering in EditorView."""

from __future__ import annotations

import re

from tests.unit.editor.harness import make_harness

_ANSI_RE = re.compile(r"\033\[[^m]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ═══════════════════════════════════════════════════════════════════════
# Single-window backward compatibility
# ═══════════════════════════════════════════════════════════════════════


class TestSingleWindowCompat:
    """Verify single-window rendering is identical to pre-window behaviour."""

    def test_text_rendered(self):
        h = make_harness("hello\nworld", width=40, height=10)
        assert h.screen_text(0) == "hello"
        assert h.screen_text(1) == "world"

    def test_tilde_for_empty_lines(self):
        h = make_harness("hello", width=40, height=10)
        assert h.screen_text(1) == "~"

    def test_modeline_present(self):
        h = make_harness("hello", width=40, height=10)
        ml = h.modeline()
        assert "*scratch*" in ml
        assert "--" in ml

    def test_message_line_at_bottom(self):
        h = make_harness("hello", width=40, height=10)
        h.editor.message = "Test message"
        h.send_keys("C-g")  # trigger re-render with message
        # Message line is last row
        assert "Quit" in h.message_line()

    def test_cursor_at_origin(self):
        h = make_harness("hello", width=40, height=10)
        assert h.cursor_position() == (0, 0)

    def test_cursor_tracks_movement(self):
        h = make_harness("hello\nworld", width=40, height=10)
        h.send_keys("C-n", "C-e")
        assert h.point() == (1, 5)
        row, col = h.cursor_position()
        assert row == 1
        assert col == 5


# ═══════════════════════════════════════════════════════════════════════
# Horizontal split rendering
# ═══════════════════════════════════════════════════════════════════════


class TestHorizontalSplitRendering:
    def test_split_produces_two_modelines(self):
        h = make_harness("hello\nworld\nfoo\nbar", width=40, height=12)
        h.send_keys("C-x", "2")
        lines = h.screen_lines()
        # Count modeline-style lines (contain *scratch*)
        modelines = [ln for ln in lines if "*scratch*" in ln]
        assert len(modelines) == 2

    def test_both_windows_show_same_text(self):
        h = make_harness("hello\nworld", width=40, height=12)
        h.send_keys("C-x", "2")
        lines = h.screen_lines()
        # Both windows should show "hello" as their first line
        text_lines = [ln for ln in lines if ln.strip() == "hello"]
        assert len(text_lines) == 2

    def test_active_window_has_cursor(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        row, col = h.cursor_position()
        # Cursor should be in the top (active) window
        assert row == 0
        assert col == 0


# ═══════════════════════════════════════════════════════════════════════
# Vertical split rendering
# ═══════════════════════════════════════════════════════════════════════


class TestVerticalSplitRendering:
    def test_vertical_split_has_divider(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "3")
        lines = h.screen_lines()
        # The divider character should appear in at least one line
        has_divider = any("\u2502" in ln for ln in lines)
        assert has_divider, f"No divider found in: {lines}"

    def test_both_sides_show_text(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "3")
        lines = h.screen_lines()
        # First row should contain "hello" on both sides of the divider
        first_line = lines[0]
        # Count occurrences of "hello"
        assert first_line.count("hello") == 2

    def test_cursor_in_left_window(self):
        h = make_harness("hello", width=40, height=10)
        h.send_keys("C-x", "3")
        row, col = h.cursor_position()
        # Cursor should be in the left (active) window
        assert col < 20  # roughly left half


# ═══════════════════════════════════════════════════════════════════════
# Active window visual distinction
# ═══════════════════════════════════════════════════════════════════════


class TestActiveWindowModeline:
    def test_active_modeline_is_bright(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        lines = h._screen.lines  # raw, with ANSI
        # Find modelines
        modelines = [ln for ln in lines if "*scratch*" in _strip_ansi(ln)]
        assert len(modelines) == 2
        # Active (first) should use \033[7m, inactive should use \033[2;7m
        assert "\033[7m" in modelines[0]
        assert "\033[2;7m" in modelines[1]

    def test_switching_window_changes_active_modeline(self):
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        h.send_keys("C-x", "o")  # switch to other window
        lines = h._screen.lines
        modelines = [ln for ln in lines if "*scratch*" in _strip_ansi(ln)]
        assert len(modelines) == 2
        # Now the second modeline should be active (bright)
        assert "\033[2;7m" in modelines[0]  # inactive (top)
        assert "\033[7m" in modelines[1]  # active (bottom)
        # Verify it's not dim+reverse
        # The active one should NOT contain \033[2;7m
        assert "\033[2;7m" not in modelines[1]


# ═══════════════════════════════════════════════════════════════════════
# Resize
# ═══════════════════════════════════════════════════════════════════════


class TestWindowResize:
    def test_resize_recalculates_layout(self):
        h = make_harness("hello\nworld", width=40, height=12)
        h.send_keys("C-x", "2")
        screen = h.view.on_resize(60, 20)
        assert screen.width == 60
        assert screen.height == 20
        # Both windows should still render
        lines = [_strip_ansi(ln) for ln in screen.lines]
        modelines = [ln for ln in lines if "*scratch*" in ln]
        assert len(modelines) == 2
