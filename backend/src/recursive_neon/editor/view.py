"""
EditorView — TUI rendering for the editor.

Implements the ``TuiApp`` protocol from the shell's TUI framework.
This is the thin shell that wraps the pure editor model: it renders
buffer text into a ``ScreenBuffer``, draws Emacs-style modelines,
manages viewport scrolling, and translates TUI keystrokes into
editor key notation.

Window support: EditorView manages a ``WindowTree``.  Each window is
rendered into its allocated screen region with its own text area and
modeline.  The active window receives keystrokes and has a bright
modeline; inactive windows are dimmed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.mark import Mark

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.window import (
    SplitDirection,
    Window,
    WindowNode,
    WindowSplit,
    WindowTree,
)
from recursive_neon.shell.tui import ScreenBuffer

# ANSI styling
_MODELINE_ACTIVE = "\033[7m"  # reverse video
_MODELINE_INACTIVE = "\033[2;7m"  # dim + reverse
_RESET = "\033[0m"
_DIVIDER_CHAR = "\u2502"  # │


class EditorView:
    """TuiApp that renders an Editor into a ScreenBuffer.

    The view occupies the full screen.  The last row is reserved for
    the message line / minibuffer.  All remaining rows are divided
    among the window tree.
    """

    def __init__(self, editor: Editor | None = None) -> None:
        self.editor = editor or Editor(global_keymap=build_default_keymap())
        self._width: int = 80
        self._height: int = 24

        # Create the initial window tree with a single root window
        if not self.editor.buffers:
            self.editor.create_buffer()
        root_win = Window.for_buffer(self.editor.buffer)
        self._tree = WindowTree(root_win)
        self.editor._window_tree = self._tree
        self.editor.viewport = root_win

    # ------------------------------------------------------------------
    # TuiApp protocol
    # ------------------------------------------------------------------

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self._width = width
        self._height = height
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        win = self._tree.active

        # Sync: ensure buffer.point matches active window's point
        win.sync_to_buffer()
        self._ensure_editor_on_buffer(win.buffer)

        self.editor.process_key(key)

        if not self.editor.running:
            return None

        # Post-key sync: detect buffer change (find-file, switch-to-buffer, etc.)
        new_active = self._tree.active  # command may have changed active
        if self.editor.buffer is not new_active.buffer:
            self._update_window_buffer(new_active, self.editor.buffer)
        else:
            new_active.sync_from_buffer()

        # Update viewport reference in case active window changed
        self.editor.viewport = self._tree.active

        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self._width = width
        self._height = height
        return self._render()

    async def on_after_key(self) -> ScreenBuffer | None:
        """Process pending async work (e.g., shell command execution).

        Called by the TUI runner after each keystroke.  Returns a fresh
        ``ScreenBuffer`` if the display needs updating, or ``None``.
        """
        handler = self.editor._pending_async
        if handler is None:
            return None
        self.editor._pending_async = None
        await handler()
        # Re-sync active window after async work modified the buffer
        self._tree.active.sync_from_buffer()
        return self._render()

    # ------------------------------------------------------------------
    # Viewport compatibility (single-window convenience)
    # ------------------------------------------------------------------

    @property
    def scroll_top(self) -> int:
        """First visible line (delegates to active window)."""
        return self._tree.active.scroll_top

    # Backward-compat alias used by existing tests
    @property
    def _scroll_top(self) -> int:
        return self._tree.active.scroll_top

    @_scroll_top.setter
    def _scroll_top(self, value: int) -> None:
        self._tree.active.scroll_top = value

    @property
    def text_height(self) -> int:
        """Text rows in the active window."""
        return self._tree.active.text_height

    def scroll_to(self, line: int) -> None:
        """Scroll the active window."""
        self._tree.active.scroll_to(line)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self) -> ScreenBuffer:
        """Render the full editor state into a ScreenBuffer."""
        # Sync active window from buffer (handles direct buffer.point moves)
        win = self._tree.active
        win.sync_from_buffer()

        screen = ScreenBuffer(width=self._width, height=self._height)

        # Layout: all rows except the last (message line) go to windows
        avail_height = max(2, self._height - 1)
        self._compute_layout(self._tree.root, 0, 0, self._width, avail_height)

        # Render each window (modelines as plain text)
        modeline_regions: list[tuple[int, int, int, str]] = []
        for win in self._tree.windows():
            is_active = win is self._tree.active
            self._render_window(win, screen, is_active)
            modeline_row = win._top + win.text_height
            if modeline_row < self._height:
                style = _MODELINE_ACTIVE if is_active else _MODELINE_INACTIVE
                modeline_regions.append((modeline_row, win._left, win._width, style))

        # Draw vertical split dividers
        self._render_dividers(self._tree.root, screen)

        # Apply ANSI styling to modeline rows after all plain-text compositing
        self._style_modeline_rows(screen, modeline_regions)

        # Message line / minibuffer (last row)
        self._render_message_line(screen)

        return screen

    def _compute_layout(
        self, node: WindowNode, top: int, left: int, width: int, height: int
    ) -> None:
        """Recursively assign screen regions to windows."""
        if isinstance(node, Window):
            node._top = top
            node._left = left
            node._width = width
            node._height = height
        else:
            if node.direction == SplitDirection.HORIZONTAL:
                first_h = height // 2
                second_h = height - first_h
                self._compute_layout(node.first, top, left, width, first_h)
                self._compute_layout(node.second, top + first_h, left, width, second_h)
            else:
                # Vertical: leave 1 column for divider
                first_w = (width - 1) // 2
                second_w = width - first_w - 1
                self._compute_layout(node.first, top, left, first_w, height)
                self._compute_layout(
                    node.second, top, left + first_w + 1, second_w, height
                )

    def _render_window(
        self, win: Window, screen: ScreenBuffer, is_active: bool
    ) -> None:
        """Render a single window's text and modeline into the screen."""
        buf = win.buffer
        text_h = win.text_height

        # Ensure cursor is visible (only for active window)
        if is_active:
            win.ensure_cursor_visible()

        # Use set_region for sub-regions (vertical splits), set_line otherwise
        full_width = win._left == 0 and win._width == self._width

        # Render text lines
        for row in range(text_h):
            line_idx = win.scroll_top + row
            screen_row = win._top + row
            if line_idx < buf.line_count:
                text = buf.lines[line_idx][: win._width]
            else:
                text = "~"
            if full_width:
                screen.set_line(screen_row, text)
            else:
                screen.set_region(screen_row, win._left, win._width, text)

        # Modeline (plain text — ANSI styling applied by _style_modeline_rows)
        modeline_row = win._top + text_h
        if modeline_row < self._height:
            ml = self._render_modeline(win)
            if full_width:
                screen.set_line(modeline_row, ml)
            else:
                screen.set_region(modeline_row, win._left, win._width, ml)

    def _render_modeline(self, win: Window) -> str:
        """Render the Emacs-style modeline for a window (plain text, no ANSI).

        ANSI styling is applied later by ``_style_modeline_rows`` so that
        ``set_region`` width calculations are not thrown off by escape codes.
        """
        buf = win.buffer
        modified = "**" if buf.modified else "--"
        name = buf.filepath if buf.filepath else buf.name
        pt = win._point
        line_col = f"L{pt.line + 1}:C{pt.col}"
        # Mode indicator
        if buf.major_mode:
            display = buf.major_mode.name.removesuffix("-mode").capitalize()
        else:
            display = "Fundamental"
        minor_indicators = "".join(
            f" {m.indicator or m.name.removesuffix('-mode').capitalize()}"
            for m in buf.minor_modes
        )
        mode_str = f"({display}{minor_indicators})"
        # Assemble
        left = f" {modified} {name}  "
        right = f"  {mode_str} ({line_col}) "
        total = len(left) + len(right)
        w = win._width
        if total <= w:
            padding = w - total
            ml_text = left + "-" * padding + right
        else:
            avail = max(4, w - len(right))
            ml_text = left[:avail] + right
        return ml_text[:w]

    def _render_dividers(self, node: WindowNode, screen: ScreenBuffer) -> None:
        """Draw vertical divider columns for vertical splits."""
        if isinstance(node, WindowSplit):
            if node.direction == SplitDirection.VERTICAL:
                # Divider column is between the two children
                # Find the rightmost column of the first child
                div_col = self._rightmost_col(node.first)
                top, height = self._node_region(node)
                for row in range(top, top + height):
                    if 0 <= row < screen.height:
                        screen.set_region(row, div_col, 1, _DIVIDER_CHAR)
            self._render_dividers(node.first, screen)
            self._render_dividers(node.second, screen)

    def _style_modeline_rows(
        self,
        screen: ScreenBuffer,
        regions: list[tuple[int, int, int, str]],
    ) -> None:
        """Apply ANSI styling to modeline rows after plain-text compositing.

        Each entry in *regions* is ``(row, col, width, style)``.  Regions
        sharing a row are styled in a single left-to-right pass so that
        ANSI escape codes never interfere with character-position math.
        """
        by_row: dict[int, list[tuple[int, int, str]]] = {}
        for row, col, width, style in regions:
            by_row.setdefault(row, []).append((col, width, style))

        for row, row_regions in by_row.items():
            if row >= screen.height:
                continue
            line = screen.lines[row]
            row_regions.sort()  # by col
            parts: list[str] = []
            pos = 0
            for col, width, style in row_regions:
                if pos < col:
                    parts.append(line[pos:col])  # unstyled gap (divider)
                end = col + width
                parts.append(f"{style}{line[col:end]}{_RESET}")
                pos = end
            if pos < len(line):
                parts.append(line[pos:])
            screen.lines[row] = "".join(parts)

    def _rightmost_col(self, node: WindowNode) -> int:
        """Return the column just past the right edge of *node*."""
        if isinstance(node, Window):
            return node._left + node._width
        # For a split, it's the rightmost of the second child
        return self._rightmost_col(node.second)

    def _node_region(self, node: WindowNode) -> tuple[int, int]:
        """Return (top, height) of a node's screen region."""
        if isinstance(node, Window):
            return node._top, node._height
        # For a split, span from first.top to end of second
        t1, _ = self._node_region(node.first)
        t2, h2 = self._node_region(node.second)
        return t1, (t2 + h2) - t1

    def _render_message_line(self, screen: ScreenBuffer) -> None:
        """Render the message line / minibuffer and set cursor position."""
        message_row = self._height - 1
        win = self._tree.active

        if self.editor.minibuffer is not None:
            mb = self.editor.minibuffer
            screen.set_line(message_row, mb.display[: self._width])
            screen.cursor_row = message_row
            screen.cursor_col = min(len(mb.prompt) + mb.cursor, self._width - 1)
            screen.cursor_visible = True
        else:
            screen.set_line(message_row, self.editor.message[: self._width])
            # Cursor in active window
            pt = win._point
            screen.cursor_row = win._top + (pt.line - win.scroll_top)
            screen.cursor_col = win._left + min(pt.col, win._width - 1)
            screen.cursor_visible = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_editor_on_buffer(self, buf: Buffer) -> None:
        """Make the editor's current buffer match *buf*."""
        if self.editor.buffer is buf:
            return
        for i, b in enumerate(self.editor._buffers):
            if b is buf:
                self.editor._current_index = i
                return

    def _update_window_buffer(self, win: Window, new_buf: Buffer) -> None:
        """Switch a window to show a different buffer."""
        if win.buffer is not new_buf:
            win.detach()
            win.buffer = new_buf
            win._point = Mark(new_buf.point.line, new_buf.point.col, kind="right")
            new_buf.track_mark(win._point)
            win.scroll_top = 0
        else:
            win.sync_from_buffer()


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
