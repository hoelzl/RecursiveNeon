"""
EditorHarness — drive the editor at the TUI level for tests.

Wraps an ``EditorView`` and provides convenience accessors for screen
content, cursor position, buffer state, and keystroke dispatch.  ANSI
escape codes are stripped from screen output automatically.

Usage::

    h = make_harness("hello\\nworld", width=40, height=10)
    h.send_keys("C-n", "C-e")
    assert h.point() == (1, 5)
    assert h.screen_text(1) == "world"
"""

from __future__ import annotations

import re

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.tui import ScreenBuffer

_ANSI_RE = re.compile(r"\033\[[^m]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI SGR escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


class EditorHarness:
    """High-level test driver for the editor TUI."""

    def __init__(self, view: EditorView, width: int, height: int) -> None:
        self.view = view
        self.editor = view.editor
        self.width = width
        self.height = height
        self._screen: ScreenBuffer = view.on_start(width, height)

    # -- Input ---------------------------------------------------------------

    def send_keys(self, *keys: str) -> None:
        """Dispatch each *key* through the TUI, updating the stored screen."""
        for key in keys:
            result = self.view.on_key(key)
            if result is not None:
                self._screen = result

    def type_string(self, s: str) -> None:
        """Type each character of *s* (newlines become Enter)."""
        for ch in s:
            if ch == "\n":
                self.send_keys("Enter")
            else:
                self.send_keys(ch)

    # -- Screen inspection ---------------------------------------------------

    def screen_text(self, row: int) -> str:
        """Return the ANSI-stripped text of screen *row*."""
        return _strip_ansi(self._screen.lines[row])

    def screen_lines(self) -> list[str]:
        """Return all screen rows with ANSI codes stripped."""
        return [_strip_ansi(line) for line in self._screen.lines]

    def cursor_position(self) -> tuple[int, int]:
        """Return ``(row, col)`` of the screen cursor."""
        return (self._screen.cursor_row, self._screen.cursor_col)

    def message_line(self) -> str:
        """Return the ANSI-stripped message line text."""
        row = self.view.text_height + 1
        return _strip_ansi(self._screen.lines[row])

    def modeline(self) -> str:
        """Return the ANSI-stripped modeline text."""
        row = self.view.text_height
        return _strip_ansi(self._screen.lines[row])

    # -- Buffer inspection ---------------------------------------------------

    def buffer_text(self) -> str:
        """Return the full buffer text."""
        return self.editor.buffer.text

    def point(self) -> tuple[int, int]:
        """Return ``(line, col)`` of the buffer point."""
        p = self.editor.buffer.point
        return (p.line, p.col)


def make_harness(
    text: str = "",
    *,
    width: int = 40,
    height: int = 10,
) -> EditorHarness:
    """Create an ``EditorHarness`` with an editor pre-loaded with *text*."""
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    view = EditorView(editor=ed)
    return EditorHarness(view, width, height)
