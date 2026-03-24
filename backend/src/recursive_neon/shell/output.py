"""
Output abstraction for shell commands and programs.

Programs write to an Output object instead of directly to stdout.
This allows the same program code to work with:
- CLI terminal (ANSI escape codes)
- Captured output (for testing)
- WebSocket transport (future browser terminal)
"""

from __future__ import annotations

import asyncio
import io
import sys
from typing import TextIO

# ANSI color codes — cyberpunk palette
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


class Output:
    """Output stream with ANSI styling helpers.

    Wraps a text stream (stdout by default) with convenience methods
    for colored/styled output.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        err_stream: TextIO | None = None,
        color: bool = True,
    ) -> None:
        self._stream: TextIO = stream or sys.stdout
        self._err_stream: TextIO = err_stream or sys.stderr
        self._color = color

    def write(self, text: str) -> None:
        """Write text to output."""
        self._stream.write(text)
        self._stream.flush()

    def writeln(self, text: str = "") -> None:
        """Write text followed by a newline."""
        self._stream.write(text + "\n")
        self._stream.flush()

    def error(self, text: str) -> None:
        """Write error message to stderr in red."""
        if self._color:
            self._err_stream.write(f"{RED}{text}{RESET}\n")
        else:
            self._err_stream.write(text + "\n")
        self._err_stream.flush()

    def styled(self, text: str, *codes: str) -> str:
        """Wrap text in ANSI codes if color is enabled."""
        if not self._color or not codes:
            return text
        prefix = "".join(codes)
        return f"{prefix}{text}{RESET}"


class CapturedOutput(Output):
    """Output that captures to in-memory buffers for testing."""

    def __init__(self) -> None:
        self._out_buf = io.StringIO()
        self._err_buf = io.StringIO()
        super().__init__(stream=self._out_buf, err_stream=self._err_buf, color=False)

    @property
    def text(self) -> str:
        """Get all captured stdout text."""
        return self._out_buf.getvalue()

    @property
    def error_text(self) -> str:
        """Get all captured stderr text."""
        return self._err_buf.getvalue()

    @property
    def lines(self) -> list[str]:
        """Get captured stdout as a list of non-empty lines."""
        return [line for line in self.text.splitlines() if line]

    def reset(self) -> None:
        """Clear captured output."""
        self._out_buf.truncate(0)
        self._out_buf.seek(0)
        self._err_buf.truncate(0)
        self._err_buf.seek(0)


class QueueOutput(Output):
    """Output that pushes text fragments to an asyncio.Queue.

    Used by the WebSocket terminal session: the shell writes output here,
    and the WebSocket handler drains the queue to send JSON messages to
    the client.  ANSI codes are preserved (the client renders them).
    """

    def __init__(self, queue: asyncio.Queue[dict]) -> None:
        # We override every write method, so the parent streams are unused.
        super().__init__(color=True)
        self._queue = queue

    def write(self, text: str) -> None:
        self._queue.put_nowait({"type": "output", "text": text})

    def writeln(self, text: str = "") -> None:
        self._queue.put_nowait({"type": "output", "text": text + "\n"})

    def error(self, text: str) -> None:
        self._queue.put_nowait({"type": "output", "text": f"{RED}{text}{RESET}\n"})
