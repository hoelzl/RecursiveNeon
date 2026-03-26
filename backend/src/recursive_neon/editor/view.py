"""
EditorView — TUI rendering for the editor.

Implements the ``TuiApp`` protocol from the shell's TUI framework.
This is the thin shell that wraps the pure editor model: it renders
buffer text into a ``ScreenBuffer``, draws the Emacs-style modeline,
manages viewport scrolling, and translates TUI keystrokes into
editor key notation.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.shell.tui import ScreenBuffer

# ANSI styling for the modeline
_MODELINE_STYLE = "\033[7m"  # reverse video
_RESET = "\033[0m"


class EditorView:
    """TuiApp that renders an Editor into a ScreenBuffer.

    The view occupies the full screen: text area fills all rows except
    the last two (modeline + message line).
    """

    def __init__(self, editor: Editor | None = None) -> None:
        self.editor = editor or Editor(global_keymap=build_default_keymap())
        self._width: int = 80
        self._height: int = 24
        self._scroll_top: int = 0  # first visible line

    # ------------------------------------------------------------------
    # TuiApp protocol
    # ------------------------------------------------------------------

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self._width = width
        self._height = height
        if not self.editor.buffers:
            self.editor.create_buffer()
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        self.editor.process_key(key)
        if not self.editor.running:
            return None
        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self._width = width
        self._height = height
        return self._render()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    @property
    def _text_height(self) -> int:
        """Number of rows available for buffer text (excluding modeline + message)."""
        return max(1, self._height - 2)

    def _render(self) -> ScreenBuffer:
        """Render the current editor state into a ScreenBuffer."""
        buf = self.editor.buffer
        screen = ScreenBuffer(width=self._width, height=self._height)

        # Ensure cursor is visible by adjusting scroll
        self._ensure_cursor_visible(buf.point.line)

        # Render text lines
        for row in range(self._text_height):
            line_idx = self._scroll_top + row
            if line_idx < buf.line_count:
                line_text = buf.lines[line_idx]
                # Truncate to width (simple truncation, no horizontal scroll yet)
                screen.set_line(row, line_text[: self._width])
            else:
                # Beyond end of buffer — show tilde like vi
                screen.set_line(row, "~")

        # Modeline
        modeline_row = self._text_height
        screen.set_line(modeline_row, self._render_modeline())

        # Message line / minibuffer
        message_row = self._text_height + 1
        if message_row < self._height:
            if self.editor.minibuffer is not None:
                mb = self.editor.minibuffer
                screen.set_line(message_row, mb.display[: self._width])
                # Cursor goes in the minibuffer
                screen.cursor_row = message_row
                screen.cursor_col = min(
                    len(mb.prompt) + mb.cursor, self._width - 1
                )
                screen.cursor_visible = True
            else:
                screen.set_line(message_row, self.editor.message[: self._width])
                # Cursor position (relative to viewport)
                screen.cursor_row = buf.point.line - self._scroll_top
                screen.cursor_col = min(buf.point.col, self._width - 1)
                screen.cursor_visible = True

        return screen

    def _ensure_cursor_visible(self, cursor_line: int) -> None:
        """Scroll the viewport so that cursor_line is visible."""
        if cursor_line < self._scroll_top:
            self._scroll_top = cursor_line
        elif cursor_line >= self._scroll_top + self._text_height:
            self._scroll_top = cursor_line - self._text_height + 1

    def _render_modeline(self) -> str:
        """Render the Emacs-style modeline."""
        buf = self.editor.buffer
        modified = "**" if buf.modified else "--"
        name = buf.name
        if buf.filepath:
            name = buf.filepath
        line_col = f"L{buf.point.line + 1}:C{buf.point.col}"
        # Pad to width
        left = f" {modified} {name}  "
        right = f"  ({line_col}) "
        padding = max(0, self._width - len(left) - len(right))
        modeline_text = left + "-" * padding + right
        return f"{_MODELINE_STYLE}{modeline_text[:self._width]}{_RESET}"


def create_editor_for_file(
    content: str = "",
    *,
    name: str = "*scratch*",
    filepath: str | None = None,
) -> EditorView:
    """Create an EditorView pre-loaded with file content.

    This is the convenience factory used by the shell command.
    """
    editor = Editor(global_keymap=build_default_keymap())
    editor.create_buffer(name=name, text=content, filepath=filepath)
    return EditorView(editor=editor)
