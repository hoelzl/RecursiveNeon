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
from recursive_neon.shell.tui import ScreenBuffer, StyleSpan

# ANSI styling
_MODELINE_ACTIVE = "\033[7m"  # reverse video
_MODELINE_INACTIVE = "\033[2;7m"  # dim + reverse
_RESET = "\033[0m"
_DIVIDER_CHAR = "\u2502"  # │

# Highlight styles for isearch / query-replace matches
_HIGHLIGHT_MATCH = "\033[43;30m"  # yellow background, black foreground
_HIGHLIGHT_CURRENT = "\033[1;41;97m"  # bold + red background + bright white
_HIGHLIGHT_PRIORITY = 20  # non-current match
_HIGHLIGHT_PRIORITY_CURRENT = 25  # the match the point is on


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

        # Replace killed buffers in inactive windows (e.g. after kill-buffer)
        live_buffers = {id(b) for b in self.editor.buffers}
        for w in self._tree.windows():
            if w is not new_active and id(w.buffer) not in live_buffers:
                self._update_window_buffer(w, self.editor.buffer)

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
        text_spans: list[StyleSpan] = []
        for win in self._tree.windows():
            is_active = win is self._tree.active
            self._render_window(win, screen, is_active, text_spans)
            modeline_row = win._top + win.text_height
            if modeline_row < self._height:
                style = _MODELINE_ACTIVE if is_active else _MODELINE_INACTIVE
                modeline_regions.append((modeline_row, win._left, win._width, style))

        # Draw vertical split dividers
        self._render_dividers(self._tree.root, screen)

        # Apply text-row styling (isearch / query-replace highlights) before
        # modeline styling so the two passes work on disjoint rows.
        self._style_text_rows(screen, text_spans)

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
        self,
        win: Window,
        screen: ScreenBuffer,
        is_active: bool,
        text_spans: list[StyleSpan],
    ) -> None:
        """Render a single window's text and modeline into the screen.

        Highlight spans (isearch / query-replace matches) are appended to
        *text_spans* for the post-compose styling pass.
        """
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

        # Compute highlight spans for this window (isearch term etc.)
        self._compute_highlight_spans(win, text_spans)

        # Modeline (plain text — ANSI styling applied by _style_modeline_rows)
        modeline_row = win._top + text_h
        if modeline_row < self._height:
            ml = self._render_modeline(win)
            if full_width:
                screen.set_line(modeline_row, ml)
            else:
                screen.set_region(modeline_row, win._left, win._width, ml)

    def _compute_highlight_spans(
        self, win: Window, text_spans: list[StyleSpan]
    ) -> None:
        """Append isearch / query-replace highlight spans for *win*.

        Scans the visible portion of ``win.buffer`` for occurrences of
        ``editor.highlight_term`` (using ``editor.highlight_case_fold``)
        and appends a ``StyleSpan`` for each match.  The current match
        (the one at ``buf.point``) is emitted at a higher priority so
        it renders with the emphasised style.

        Only single-line match segments are emitted per visible row —
        multi-line needles are walked via ``Buffer.find_forward`` but
        their rendered highlights are broken into per-line sub-spans.
        """
        term = self.editor.highlight_term
        if not term:
            return
        buf = win.buffer
        case_fold = self.editor.highlight_case_fold
        text_h = win.text_height
        first_visible = win.scroll_top
        last_visible = first_visible + text_h - 1

        # Find all matches by iterating Buffer.find_forward from the
        # buffer start.  Stop once we pass the last visible line.
        cursor_line = 0
        cursor_col = 0
        point_line = buf.point.line
        point_col = buf.point.col

        while True:
            if cursor_line >= buf.line_count:
                break
            match = buf.find_forward(term, cursor_line, cursor_col, case_fold=case_fold)
            if match is None:
                break
            m_line, m_col = match
            # Compute match end (may cross lines for multi-line needles)
            end_line, end_col = self._match_end(term, m_line, m_col, buf)

            # Advance search cursor past this match for the next iteration.
            # Use +1 to avoid infinite loop on empty-match edge cases.
            if end_line == m_line and end_col == m_col:
                cursor_line, cursor_col = m_line, m_col + 1
            else:
                cursor_line, cursor_col = end_line, end_col

            # Bail out once we're past the visible region.
            if m_line > last_visible:
                break

            # Is this the current match (the one point is on)?
            is_current = m_line == point_line and m_col == point_col

            # Emit per-line sub-spans for the match.
            if m_line == end_line:
                line_ranges = [(m_line, m_col, end_col)]
            else:
                line_ranges = []
                # First line: from m_col to end of line
                if 0 <= m_line < buf.line_count:
                    line_ranges.append((m_line, m_col, len(buf.lines[m_line])))
                # Middle lines: whole line
                for ln in range(m_line + 1, end_line):
                    if 0 <= ln < buf.line_count:
                        line_ranges.append((ln, 0, len(buf.lines[ln])))
                # Last line: from 0 to end_col
                line_ranges.append((end_line, 0, end_col))

            for ln, c_start, c_end in line_ranges:
                if ln < first_visible or ln > last_visible:
                    continue
                screen_row = win._top + (ln - first_visible)
                screen_col = win._left + c_start
                width = c_end - c_start
                if width <= 0:
                    continue
                # Clip to window width
                win_right = win._left + win._width
                if screen_col >= win_right:
                    continue
                if screen_col + width > win_right:
                    width = win_right - screen_col
                style = _HIGHLIGHT_CURRENT if is_current else _HIGHLIGHT_MATCH
                priority = (
                    _HIGHLIGHT_PRIORITY_CURRENT if is_current else _HIGHLIGHT_PRIORITY
                )
                text_spans.append(
                    StyleSpan(
                        row=screen_row,
                        col=screen_col,
                        width=width,
                        style=style,
                        priority=priority,
                    )
                )

    @staticmethod
    def _match_end(term: str, m_line: int, m_col: int, buf: Buffer) -> tuple[int, int]:
        """Compute the (line, col) *just past* the end of a match.

        Handles multi-line needles (needle contains ``\\n``) by walking
        part-by-part from the starting position.
        """
        if "\n" not in term:
            return (m_line, m_col + len(term))
        parts = term.split("\n")
        # First part occupies from m_col to end of m_line
        # Middle parts occupy whole lines
        # Last part occupies 0..len(parts[-1]) on the final line
        end_line = m_line + len(parts) - 1
        end_col = len(parts[-1])
        return (end_line, end_col)

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

    def _style_text_rows(
        self,
        screen: ScreenBuffer,
        spans: list[StyleSpan],
    ) -> None:
        """Apply ``StyleSpan`` entries to the composed screen.

        Overlapping spans on the same cell resolve by priority (higher
        wins; ties break by emission order, which is stable because we
        iterate the list in order).  Each affected row is rewritten by
        walking runs of constant effective style and wrapping them in
        ``style + text + reset``.

        Spans that reference rows outside the screen are ignored, as
        are zero-width spans.
        """
        if not spans:
            return

        by_row: dict[int, list[StyleSpan]] = {}
        for span in spans:
            if span.width <= 0:
                continue
            if 0 <= span.row < screen.height:
                by_row.setdefault(span.row, []).append(span)

        for row, row_spans in by_row.items():
            line = screen.lines[row]
            if not line:
                continue
            n = len(line)
            # Per-cell winning (priority, style) or None for unstyled.
            cell_styles: list[tuple[int, str] | None] = [None] * n
            for span in row_spans:
                lo = max(0, span.col)
                hi = min(n, span.col + span.width)
                for c in range(lo, hi):
                    cur = cell_styles[c]
                    if cur is None or span.priority > cur[0]:
                        cell_styles[c] = (span.priority, span.style)

            # Walk the line, emitting runs of constant effective style.
            parts: list[str] = []
            i = 0
            while i < n:
                cur = cell_styles[i]
                j = i
                while j < n and cell_styles[j] == cur:
                    j += 1
                if cur is None:
                    parts.append(line[i:j])
                else:
                    parts.append(f"{cur[1]}{line[i:j]}{_RESET}")
                i = j
            screen.lines[row] = "".join(parts)

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
