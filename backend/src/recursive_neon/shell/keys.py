"""
Platform-specific raw keystroke reading.

Shared between the local CLI (shell.py) and the WebSocket client
(wsclient/client.py) to avoid duplicating key lookup tables and
raw-mode logic.
"""

from __future__ import annotations

import asyncio
import sys

# ---------------------------------------------------------------------------
# Key lookup tables
# ---------------------------------------------------------------------------

WINDOWS_SPECIAL_KEYS: dict[str, str] = {
    "H": "ArrowUp",
    "P": "ArrowDown",
    "K": "ArrowLeft",
    "M": "ArrowRight",
    "G": "Home",
    "O": "End",
    "I": "PageUp",
    "Q": "PageDown",
    "S": "Delete",
    "R": "Insert",
    ";": "F1",
    "<": "F2",
    "=": "F3",
    ">": "F4",
}

ANSI_SEQUENCES: dict[str, str] = {
    "A": "ArrowUp",
    "B": "ArrowDown",
    "C": "ArrowRight",
    "D": "ArrowLeft",
    "H": "Home",
    "F": "End",
}

CTRL_KEYS: dict[str, str] = {
    "\r": "Enter",
    "\n": "Enter",
    "\t": "Tab",
    "\x08": "Backspace",
    "\x03": "C-c",
    "\x04": "C-d",
    "\x11": "C-q",
    "\x17": "C-w",
}


# ---------------------------------------------------------------------------
# Platform-specific raw key reading
# ---------------------------------------------------------------------------


def read_key_windows() -> str:
    """Read a single key on Windows using msvcrt."""
    import msvcrt

    ch = msvcrt.getwch()

    # Special keys start with \x00 or \xe0
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return WINDOWS_SPECIAL_KEYS.get(ch2, f"Unknown-{ord(ch2)}")

    # Ctrl combinations
    if ord(ch) < 32:
        return CTRL_KEYS.get(ch, f"C-{chr(ord(ch) + 64).lower()}")

    # Escape
    if ch == "\x1b":
        return "Escape"

    return ch


def read_key_unix() -> str:  # pragma: no cover (Unix only)
    """Read a single key on Unix using tty/termios."""
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)  # type: ignore[attr-defined]
    try:
        tty.setraw(fd)  # type: ignore[attr-defined]
        ch = sys.stdin.read(1)

        if ch == "\x1b":
            # Could be an escape sequence
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return ANSI_SEQUENCES.get(ch3, f"Unknown-[{ch3}")
                return f"Alt-{ch2}"
            return "Escape"

        # Ctrl combinations
        if ord(ch) < 32:
            return CTRL_KEYS.get(ch, f"C-{chr(ord(ch) + 64).lower()}")

        # Backspace (DEL)
        if ch == "\x7f":
            return "Backspace"

        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # type: ignore[attr-defined]


def read_key_blocking() -> str:
    """Read a single raw key, dispatching to the correct platform implementation."""
    if sys.platform == "win32":
        return read_key_windows()
    else:
        return read_key_unix()


async def read_key_async() -> str:
    """Read a single raw key asynchronously (runs blocking I/O in a thread)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, read_key_blocking)
