"""Tests for the EditorHarness test helper."""

from __future__ import annotations

from tests.unit.editor.harness import make_harness


class TestHarnessBasics:
    def test_make_harness_returns_harness(self):
        h = make_harness("hello")
        assert h.editor is not None
        assert h.view is not None

    def test_screen_text_first_line(self):
        h = make_harness("hello\nworld")
        assert h.screen_text(0) == "hello"
        assert h.screen_text(1) == "world"

    def test_screen_lines_returns_all(self):
        h = make_harness("abc", height=5)
        lines = h.screen_lines()
        assert len(lines) == 5
        assert lines[0] == "abc"

    def test_cursor_position_at_origin(self):
        h = make_harness("hello")
        assert h.cursor_position() == (0, 0)

    def test_buffer_text(self):
        h = make_harness("hello\nworld")
        assert h.buffer_text() == "hello\nworld"

    def test_point_at_origin(self):
        h = make_harness("hello")
        assert h.point() == (0, 0)


class TestHarnessInput:
    def test_send_keys_movement(self):
        h = make_harness("hello")
        h.send_keys("C-e")
        assert h.point() == (0, 5)

    def test_send_keys_multiple(self):
        h = make_harness("hello\nworld")
        h.send_keys("C-n", "C-e")
        assert h.point() == (1, 5)

    def test_type_string(self):
        h = make_harness()
        h.type_string("hi")
        assert h.buffer_text() == "hi"

    def test_type_string_with_newline(self):
        h = make_harness()
        h.type_string("a\nb")
        assert h.buffer_text() == "a\nb"


class TestHarnessScreenDetails:
    def test_modeline_contains_buffer_name(self):
        h = make_harness("hello")
        assert "*scratch*" in h.modeline()

    def test_modeline_strips_ansi(self):
        h = make_harness("hello")
        ml = h.modeline()
        assert "\033[" not in ml

    def test_message_line_shows_message(self):
        h = make_harness("hello")
        h.send_keys("C-space")
        assert "Mark set" in h.message_line()

    def test_cursor_tracks_movement(self):
        h = make_harness("hello\nworld")
        h.send_keys("C-n")
        row, col = h.cursor_position()
        assert row == 1
        assert col == 0
