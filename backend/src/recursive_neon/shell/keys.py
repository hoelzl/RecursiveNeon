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


def _win_alt_pressed() -> bool:
    """Check whether Alt is physically held using the Win32 API.

    ``msvcrt.getwch()`` on Windows Terminal silently drops the Alt
    modifier for regular letter keys, so we probe the hardware state
    via ``GetAsyncKeyState(VK_MENU)`` immediately after each read.
    """
    import ctypes

    VK_MENU = 0x12  # Alt key (either left or right)
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_MENU) & 0x8000)


def read_key_windows() -> str:
    """Read a single key on Windows using msvcrt + Win32 Alt detection."""
    import msvcrt

    ch = msvcrt.getwch()
    alt = _win_alt_pressed()

    # Special keys start with \x00 or \xe0
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        key = WINDOWS_SPECIAL_KEYS.get(ch2, f"Unknown-{ord(ch2)}")
        return f"M-{key}" if alt else key

    # Ctrl combinations (except ESC which is also < 32)
    if ord(ch) < 32 and ch != "\x1b":
        key = CTRL_KEYS.get(ch, f"C-{chr(ord(ch) + 64).lower()}")
        return f"M-{key}" if alt else key

    # Escape — could be a real Escape key, or ESC+key from a Unix-style
    # terminal (e.g. SSH session).  Also handle Alt+Escape.
    if ch == "\x1b":
        if msvcrt.kbhit():
            ch2 = msvcrt.getwch()
            if ch2 in ("\x00", "\xe0"):
                ch3 = msvcrt.getwch()
                special = WINDOWS_SPECIAL_KEYS.get(ch3, f"Unknown-{ord(ch3)}")
                return f"M-{special}"
            if ord(ch2) < 32:
                ctrl = CTRL_KEYS.get(ch2, f"C-{chr(ord(ch2) + 64).lower()}")
                return f"M-{ctrl}"
            return f"M-{ch2}"
        return "Escape"

    # Regular printable character — Alt detected via Win32 API
    if alt:
        return f"M-{ch}"

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
                return f"M-{ch2}"
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
