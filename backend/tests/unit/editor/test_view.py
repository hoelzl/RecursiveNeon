"""Tests for EditorView (TuiApp) and shell integration."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView, create_editor_for_file


def make_view(text: str = "", *, width: int = 40, height: int = 10) -> EditorView:
    """Helper: create an EditorView with given text and dimensions."""
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    view = EditorView(editor=ed)
    view.on_start(width, height)
    return view


# ═══════════════════════════════════════════════════════════════════════
# Rendering basics
# ═══════════════════════════════════════════════════════════════════════


class TestViewRendering:
    def test_on_start_returns_screen(self):
        view = EditorView()
        screen = view.on_start(80, 24)
        assert screen is not None
        assert screen.width == 80
        assert screen.height == 24

    def test_text_lines_rendered(self):
        view = make_view("hello\nworld")
        screen = view.on_start(40, 10)
        assert screen.lines[0] == "hello"
        assert screen.lines[1] == "world"

    def test_empty_lines_show_tilde(self):
        view = make_view("hello")
        screen = view.on_start(40, 10)
        # text_height = 10 - 2 = 8, so lines 1-7 should be "~"
        assert screen.lines[1] == "~"
        assert screen.lines[7] == "~"

    def test_cursor_at_origin(self):
        view = make_view("hello")
        screen = view.on_start(40, 10)
        assert screen.cursor_row == 0
        assert screen.cursor_col == 0
        assert screen.cursor_visible

    def test_cursor_tracks_point(self):
        view = make_view("hello")
        view.editor.buffer.point.col = 3
        screen = view._render()
        assert screen.cursor_col == 3

    def test_modeline_present(self):
        view = make_view("hello", height=10)
        screen = view.on_start(40, 10)
        # Modeline is on row 8 (text_height = 8)
        modeline = screen.lines[8]
        assert "\033[7m" in modeline  # reverse video
        assert "*scratch*" in modeline

    def test_modeline_shows_modified(self):
        view = make_view("hello")
        view.editor.buffer.modified = True
        screen = view._render()
        modeline = screen.lines[view.text_height]
        assert "**" in modeline

    def test_modeline_shows_unmodified(self):
        view = make_view("hello")
        view.editor.buffer.modified = False
        screen = view._render()
        modeline = screen.lines[view.text_height]
        assert "--" in modeline

    def test_modeline_shows_filepath(self):
        view = make_view("hello", width=80)
        view.editor.buffer.filepath = "Documents/notes.txt"
        screen = view._render()
        modeline = screen.lines[view.text_height]
        assert "Documents/notes.txt" in modeline

    def test_modeline_shows_line_col(self):
        view = make_view("hello\nworld")
        view.editor.buffer.point.line = 1
        view.editor.buffer.point.col = 3
        screen = view._render()
        modeline = screen.lines[view.text_height]
        assert "L2:C3" in modeline

    def test_message_line(self):
        view = make_view("hello")
        view.editor.message = "Mark set"
        screen = view._render()
        message_row = view.text_height + 1
        assert screen.lines[message_row] == "Mark set"


# ═══════════════════════════════════════════════════════════════════════
# Key handling and TuiApp protocol
# ═══════════════════════════════════════════════════════════════════════


class TestViewKeyHandling:
    def test_on_key_returns_screen(self):
        view = make_view("hello")
        screen = view.on_key("C-f")
        assert screen is not None

    def test_on_key_typing(self):
        view = make_view()
        view.on_key("h")
        view.on_key("i")
        assert view.editor.buffer.text == "hi"

    def test_on_key_movement(self):
        view = make_view("hello")
        view.on_key("C-e")
        assert view.editor.buffer.point.col == 5

    def test_on_key_quit_returns_none(self):
        view = make_view()
        view.on_key("C-x")
        result = view.on_key("C-c")
        assert result is None
        assert not view.editor.running

    def test_on_resize(self):
        view = make_view("hello")
        screen = view.on_resize(60, 20)
        assert screen.width == 60
        assert screen.height == 20


# ═══════════════════════════════════════════════════════════════════════
# Viewport scrolling
# ═══════════════════════════════════════════════════════════════════════


class TestViewScrolling:
    def test_scroll_down_when_cursor_below_viewport(self):
        # 10 lines of text, viewport = height - 2 = 3 rows
        text = "\n".join(f"line {i}" for i in range(10))
        view = make_view(text, height=5)  # text_height = 3
        # Move cursor to line 5
        view.editor.buffer.point.line = 5
        screen = view._render()
        # Scroll should have adjusted so line 5 is visible
        assert view._scroll_top <= 5
        assert view._scroll_top + view.text_height > 5
        # Cursor row should be relative to viewport
        assert screen.cursor_row == 5 - view._scroll_top

    def test_scroll_up_when_cursor_above_viewport(self):
        text = "\n".join(f"line {i}" for i in range(10))
        view = make_view(text, height=5)
        # Scroll down first
        view.editor.buffer.point.line = 8
        view._render()
        # Now move cursor back up
        view.editor.buffer.point.line = 1
        screen = view._render()
        assert view._scroll_top <= 1
        assert screen.cursor_row == 1 - view._scroll_top

    def test_no_scroll_when_cursor_visible(self):
        text = "\n".join(f"line {i}" for i in range(10))
        view = make_view(text, height=5)
        view.editor.buffer.point.line = 2
        view._render()
        assert view._scroll_top == 0

    def test_scroll_follows_typing_at_bottom(self):
        view = make_view("", height=5)  # text_height = 3
        # Type 5 lines
        for i in range(5):
            if i > 0:
                view.on_key("Enter")
            for ch in f"line{i}":
                view.on_key(ch)
        # Should have scrolled to keep cursor visible
        assert view._scroll_top > 0
        assert view.editor.buffer.point.line - view._scroll_top < view.text_height


# ═══════════════════════════════════════════════════════════════════════
# Factory function
# ═══════════════════════════════════════════════════════════════════════


class TestCreateEditorForFile:
    def test_from_content(self):
        view = create_editor_for_file(content="hello\nworld", name="test.txt")
        assert view.editor.buffer.text == "hello\nworld"
        assert view.editor.buffer.name == "test.txt"

    def test_with_filepath(self):
        view = create_editor_for_file(
            content="data", name="foo.txt", filepath="Documents/foo.txt"
        )
        assert view.editor.buffer.filepath == "Documents/foo.txt"

    def test_empty_scratch(self):
        view = create_editor_for_file()
        assert view.editor.buffer.text == ""
        assert view.editor.buffer.name == "*scratch*"


# ═══════════════════════════════════════════════════════════════════════
# Save callback integration
# ═══════════════════════════════════════════════════════════════════════


class TestSaveCallback:
    def test_save_calls_callback(self):
        saved = {}

        def mock_save(buf):
            saved["text"] = buf.text
            return True

        view = make_view("hello world")
        view.editor.save_callback = mock_save
        view.on_key("C-x")
        view.on_key("C-s")
        assert saved["text"] == "hello world"
        assert not view.editor.buffer.modified

    def test_save_without_callback_shows_message(self):
        view = make_view("hello")
        view.editor.save_callback = None
        view.on_key("C-x")
        view.on_key("C-s")
        assert "No save handler" in view.editor.message

    def test_save_failure_shows_message(self):
        view = make_view("hello")
        view.editor.save_callback = lambda buf: False
        view.on_key("C-x")
        view.on_key("C-s")
        assert "failed" in view.editor.message.lower()


# ═══════════════════════════════════════════════════════════════════════
# Post-compose styling (StyleSpan + _style_text_rows)
# ═══════════════════════════════════════════════════════════════════════


class TestStyleTextRows:
    """Unit tests for the post-compose styling pass.

    Exercises ``EditorView._style_text_rows`` directly with synthetic
    ``StyleSpan`` inputs, so the algorithm is verified independently of
    isearch / query-replace wiring.
    """

    def _view(self) -> EditorView:
        return make_view("", width=20, height=5)

    def _screen_with_line(self, text: str, width: int = 20):
        from recursive_neon.shell.tui import ScreenBuffer

        screen = ScreenBuffer(width=width, height=1)
        screen.set_line(0, text.ljust(width))
        return screen

    def test_empty_span_list_is_noop(self):
        view = self._view()
        screen = self._screen_with_line("hello world")
        original = screen.lines[0]
        view._style_text_rows(screen, [])
        assert screen.lines[0] == original

    def test_single_span_wraps_range(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("hello world")
        spans = [StyleSpan(row=0, col=6, width=5, style="\033[7m", priority=20)]
        view._style_text_rows(screen, spans)
        # Line should still start with "hello " unstyled, then styled "world"
        line = screen.lines[0]
        assert line.startswith("hello ")
        assert "\033[7mworld\033[0m" in line

    def test_multiple_non_overlapping_spans_on_same_row(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("foo bar baz")
        spans = [
            StyleSpan(row=0, col=0, width=3, style="\033[31m", priority=20),
            StyleSpan(row=0, col=8, width=3, style="\033[32m", priority=20),
        ]
        view._style_text_rows(screen, spans)
        line = screen.lines[0]
        assert "\033[31mfoo\033[0m" in line
        assert "\033[32mbaz\033[0m" in line
        # Middle "bar" stays unstyled
        assert " bar " in line

    def test_overlapping_spans_resolved_by_priority(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("abcdefghij")
        # Lower priority covers cells 0..7; higher priority covers 3..5.
        spans = [
            StyleSpan(row=0, col=0, width=8, style="\033[31m", priority=10),
            StyleSpan(row=0, col=3, width=3, style="\033[1;33m", priority=25),
        ]
        view._style_text_rows(screen, spans)
        line = screen.lines[0]
        # Expect: "abc" styled red, "def" styled bold yellow, "gh" styled red,
        # the rest unstyled.
        assert "\033[31mabc\033[0m" in line
        assert "\033[1;33mdef\033[0m" in line
        assert "\033[31mgh\033[0m" in line

    def test_span_exceeding_line_length_is_clipped(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("abc", width=5)
        # Span extends past the 5-char line; should clip without error.
        spans = [StyleSpan(row=0, col=2, width=100, style="\033[7m", priority=20)]
        view._style_text_rows(screen, spans)
        line = screen.lines[0]
        assert line.startswith("ab")  # unstyled prefix
        assert "\033[7m" in line  # styling started
        assert line.endswith("\033[0m")  # properly closed

    def test_zero_width_span_ignored(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("hello")
        original = screen.lines[0]
        view._style_text_rows(
            screen, [StyleSpan(row=0, col=2, width=0, style="\033[7m", priority=20)]
        )
        assert screen.lines[0] == original

    def test_span_outside_screen_ignored(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("hello")
        original = screen.lines[0]
        view._style_text_rows(
            screen,
            [
                StyleSpan(row=99, col=0, width=5, style="\033[7m", priority=20),
                StyleSpan(row=-1, col=0, width=5, style="\033[7m", priority=20),
            ],
        )
        assert screen.lines[0] == original

    def test_spans_on_different_rows_applied_independently(self):
        from recursive_neon.shell.tui import ScreenBuffer, StyleSpan

        view = self._view()
        screen = ScreenBuffer(width=10, height=3)
        screen.set_line(0, "aaaaaaaaaa")
        screen.set_line(1, "bbbbbbbbbb")
        screen.set_line(2, "cccccccccc")
        spans = [
            StyleSpan(row=0, col=0, width=3, style="\033[31m", priority=20),
            StyleSpan(row=2, col=5, width=4, style="\033[32m", priority=20),
        ]
        view._style_text_rows(screen, spans)
        assert screen.lines[0].startswith("\033[31maaa\033[0m")
        assert screen.lines[1] == "bbbbbbbbbb"  # unchanged
        assert "\033[32mcccc\033[0m" in screen.lines[2]

    def test_tie_breaks_by_emission_order(self):
        from recursive_neon.shell.tui import StyleSpan

        view = self._view()
        screen = self._screen_with_line("xxxxx")
        # Both priority 20, overlapping; later-emitted wins because the
        # comparison is strict > priority (not >=).
        spans = [
            StyleSpan(row=0, col=0, width=5, style="\033[31m", priority=20),
            StyleSpan(row=0, col=0, width=5, style="\033[32m", priority=20),
        ]
        view._style_text_rows(screen, spans)
        # Strict > means the FIRST span wins for equal priority.
        line = screen.lines[0]
        assert "\033[31mxxxxx\033[0m" in line
        assert "\033[32m" not in line
