"""
TUI framework for full-screen terminal applications.

Provides the core abstractions for building interactive TUI apps
that run inside the shell. Apps implement the TuiApp protocol and
render to a ScreenBuffer; the framework handles mode switching,
keystroke routing, and screen delivery across CLI and WebSocket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class StyleSpan:
    """A styled region to overlay on a ``ScreenBuffer`` after compositing.

    Used by the editor's post-compose styling pass for inline highlights
    (isearch, query-replace, future syntax highlighting).  Spans are
    applied *after* plain-text rendering is complete, so they never
    interfere with ``set_region`` width math.

    Overlapping spans on the same cell resolve by priority: higher
    ``priority`` wins.  Reserved priority ranges (higher wins per cell):

    - 10 — syntax highlighting (future)
    - 20 — isearch / query-replace, non-current match
    - 25 — isearch / query-replace, current match (emphasised)
    - 30 — region / active mark (future)
    - 40 — cursor line highlight (future)
    """

    row: int
    col: int
    width: int
    style: str
    priority: int = 0


@dataclass
class ScreenBuffer:
    """A 2D text grid representing the terminal screen.

    Each row is a string that may contain ANSI escape codes for styling.
    The framework delivers complete screen snapshots to the client after
    each keystroke — no incremental updates to track.
    """

    width: int
    height: int
    lines: list[str] = field(default_factory=list)
    cursor_row: int = 0
    cursor_col: int = 0
    cursor_visible: bool = True

    def __post_init__(self) -> None:
        if not self.lines:
            self.lines = [""] * self.height

    @classmethod
    def create(cls, width: int = 80, height: int = 24) -> ScreenBuffer:
        return cls(width=width, height=height)

    def set_line(self, row: int, text: str) -> None:
        """Set the content of a specific row."""
        if 0 <= row < self.height:
            self.lines[row] = text

    def set_region(self, row: int, col: int, width: int, text: str) -> None:
        """Write *text* into columns [col, col+width) of *row*.

        Text is padded/truncated to exactly *width* characters.
        Existing content outside the region is preserved.
        """
        if not (0 <= row < self.height) or width <= 0:
            return
        line = self.lines[row]
        # Pad line to reach the target region
        if len(line) < col + width:
            line = line.ljust(col + width)
        segment = text[:width].ljust(width)
        self.lines[row] = line[:col] + segment + line[col + width :]

    def clear(self) -> None:
        """Clear all rows."""
        self.lines = [""] * self.height

    def center_text(self, row: int, text: str, style: str = "") -> None:
        """Write text centered horizontally on a row.

        *text* should be the raw (unstyled) string so padding is
        calculated correctly.  *style* is an optional ANSI prefix
        applied to the text (the reset code is appended automatically).
        """
        if not (0 <= row < self.height):
            return
        # Strip ANSI for width calculation — the visible length is len(text)
        pad = max(0, (self.width - len(text)) // 2)
        if style:
            self.lines[row] = " " * pad + f"{style}{text}\033[0m"
        else:
            self.lines[row] = " " * pad + text

    def to_message(self) -> dict:
        """Serialize to a WebSocket ``screen`` message."""
        return {
            "type": "screen",
            "lines": list(self.lines),
            "cursor": [self.cursor_row, self.cursor_col],
            "cursor_visible": self.cursor_visible,
        }

    def render_ansi(self) -> str:
        """Render as an ANSI string for direct terminal display.

        Clears the screen and writes each row at its absolute position.
        """
        parts: list[str] = ["\033[2J\033[H"]  # clear + home
        for i, line in enumerate(self.lines):
            parts.append(f"\033[{i + 1};1H{line}")
        if self.cursor_visible:
            parts.append(f"\033[{self.cursor_row + 1};{self.cursor_col + 1}H")
        return "".join(parts)


class TuiApp(Protocol):
    """Interface for full-screen TUI applications.

    Apps are pure state machines: they receive keystrokes and return
    screen buffers.  No I/O, no async — this makes them trivially
    testable by calling ``on_start`` / ``on_key`` directly.
    """

    tick_interval_ms: int
    """Tick interval in milliseconds.  ``0`` disables ticks."""

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        """Called when the app launches. Return the initial screen."""
        ...

    def on_key(self, key: str) -> ScreenBuffer | None:
        """Handle a keystroke.

        Return a new screen buffer to display, or ``None`` to exit.

        Key encoding:
        - Printable characters: ``"a"``, ``"Z"``, ``" "``
        - Named keys: ``"Enter"``, ``"Escape"``, ``"Backspace"``, ``"Tab"``
        - Arrow keys: ``"ArrowUp"``, ``"ArrowDown"``, ``"ArrowLeft"``, ``"ArrowRight"``
        - Ctrl combos: ``"C-c"``, ``"C-d"``
        """
        ...

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        """Handle terminal resize. Return a re-rendered screen."""
        ...

    def on_tick(self, dt_ms: int) -> ScreenBuffer | None:
        """Called periodically when ``tick_interval_ms > 0``.

        *dt_ms* is the approximate elapsed time since the last tick (or
        since ``on_start`` for the first tick).  Return a new screen to
        display, or ``None`` to keep the current screen.
        """
        ...


class RawInputSource(Protocol):
    """Provides individual keystrokes to a TUI application."""

    async def get_key(self, *, timeout: float | None = None) -> str | None:
        """Read one keystroke.

        Returns a canonical key string (see ``TuiApp.on_key`` for encoding),
        or ``None`` if *timeout* seconds elapsed with no input.

        When *timeout* is ``None``, blocks indefinitely.

        Raises:
            EOFError: Connection lost or input exhausted.
        """
        ...
