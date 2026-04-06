"""Entry point: python -m recursive_neon.wsclient"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from recursive_neon.wsclient.client import (
    run_batch_client,
    run_client,
    run_headless_client,
)


def _enable_ansi_on_windows() -> None:
    """Enable virtual terminal processing so ANSI codes render on Windows."""
    if sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = ctypes.c_ulong()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect to Recursive://Neon terminal via WebSocket",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Headless mode: read JSON commands from stdin, write JSON to stdout. "
        "No terminal required. Suitable for automation and scripting.",
    )
    parser.add_argument(
        "--command",
        "-c",
        type=str,
        default=None,
        help="Run a single command, print output, and exit. "
        "ANSI codes are stripped when stdout is not a TTY.",
    )
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}/ws/terminal"

    if args.command is not None:
        if sys.stdout.isatty():
            _enable_ansi_on_windows()
        with contextlib.suppress(KeyboardInterrupt):
            exit_code = asyncio.run(run_batch_client(url, args.command))
        sys.exit(exit_code)
    elif args.headless:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(run_headless_client(url))
    else:
        _enable_ansi_on_windows()
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(run_client(url))

    sys.exit(0)


if __name__ == "__main__":
    main()
