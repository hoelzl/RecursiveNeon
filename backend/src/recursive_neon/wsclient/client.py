"""
WebSocket terminal client implementation.

Connects to the server's /ws/terminal endpoint and runs an interactive
REPL using prompt_toolkit for local line editing and tab completion.
Supports both cooked mode (line editing) and raw mode (TUI apps).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from prompt_toolkit.completion import Completer, Completion
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

# Sentinel used to signal mode changes through the input queue
_MODE_CHANGE = "__mode_change__"


# ---------------------------------------------------------------------------
# WebSocketCompleter — tab completion via the server
# ---------------------------------------------------------------------------


class _WebSocketCompleter(Completer):
    """prompt_toolkit Completer that requests completions from the server.

    Overrides ``get_completions_async`` so completions run natively on
    the asyncio event loop (no thread pool needed).  This is safe because
    the client uses ``prompt_async()``, which calls the async variant.
    """

    def __init__(self, ws) -> None:
        self._ws = ws
        self._pending: asyncio.Future[tuple[list[str], int]] | None = None

    # -- async path (used by prompt_async) ------------------------------------

    async def get_completions_async(self, document, complete_event):
        text = document.text_before_cursor
        if not text:
            return

        # Cancel any previous in-flight request
        if self._pending is not None and not self._pending.done():
            self._pending.cancel()

        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()
        await self._ws.send(json.dumps({"type": "complete", "line": text}))

        try:
            items, replace = await asyncio.wait_for(self._pending, timeout=3.0)
        except (TimeoutError, asyncio.CancelledError):
            return

        for item in items:
            yield Completion(item, start_position=-replace)

    # -- sync fallback (required by Completer ABC) ----------------------------

    def get_completions(self, document, complete_event):
        return []

    # -- called by _server_reader when a completions message arrives ----------

    def feed_completions(self, items: list[str], replace: int) -> None:
        """Resolve the pending future with the server's response."""
        if self._pending is not None and not self._pending.done():
            self._pending.set_result((items, replace))


# ---------------------------------------------------------------------------
# Raw key reading — delegates to shared keys module
# ---------------------------------------------------------------------------


async def _read_raw_key() -> str:
    """Read a single keystroke from the terminal in raw mode.

    Returns a canonical key string matching the TuiApp key encoding.
    Delegates to the shared keys module (recursive_neon.shell.keys).
    """
    from recursive_neon.shell.keys import read_key_async

    return await read_key_async()


# ---------------------------------------------------------------------------
# Screen rendering
# ---------------------------------------------------------------------------


def _render_screen(lines: list[str], cursor: list[int]) -> None:
    """Render a screen buffer to the terminal using ANSI escape codes."""
    # Clear screen + move to home
    sys.stdout.write("\033[2J\033[H")
    for i, line in enumerate(lines):
        sys.stdout.write(f"\033[{i + 1};1H{line}")
    # Position cursor
    if len(cursor) >= 2:
        sys.stdout.write(f"\033[{cursor[0] + 1};{cursor[1] + 1}H")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Client session
# ---------------------------------------------------------------------------


async def run_client(url: str) -> None:
    """Connect to the terminal WebSocket and run an interactive session."""
    try:
        async with connect(url) as ws:
            await _session_loop(ws)
    except OSError as e:
        print(f"\nConnection failed: {e}", file=sys.stderr)
        print(f"Is the server running at {url}?", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Headless client — JSON stdin/stdout, no prompt_toolkit
# ---------------------------------------------------------------------------


async def run_batch_client(url: str, command: str) -> int:
    """Connect, run a single command, print its output, and disconnect.

    Args:
        url: WebSocket URL to connect to.
        command: Shell command to execute.

    Returns:
        Exit code from the command (0 = success, non-zero = error).
    """
    import re

    is_tty = sys.stdout.isatty()
    _ansi_re = re.compile(r"\033\[[0-9;]*[A-Za-z]")

    exit_code = 0

    try:
        async with connect(url) as ws:
            # Wait for the initial prompt
            prompt_received = False
            while not prompt_received:
                raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                msg = json.loads(raw)
                if msg.get("type") == "prompt":
                    prompt_received = True
                elif msg.get("type") == "output" and is_tty:
                    sys.stdout.write(msg.get("text", ""))

            # Send the command
            await ws.send(json.dumps({"type": "input", "line": command}))

            # Send exit immediately after so the session terminates
            # after the command finishes.
            exit_sent = False

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                except TimeoutError:
                    break
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "output":
                    text = msg.get("text", "")
                    if not is_tty:
                        text = _ansi_re.sub("", text)
                    sys.stdout.write(text)
                    sys.stdout.flush()

                elif msg_type == "prompt":
                    if not exit_sent:
                        # Command finished — send exit
                        await ws.send(json.dumps({"type": "input", "line": "exit"}))
                        exit_sent = True
                    else:
                        # Second prompt after exit — we're done
                        break

                elif msg_type == "exit":
                    break

                elif msg_type == "error":
                    err = msg.get("message", "Unknown error")
                    sys.stderr.write(f"Server error: {err}\n")
                    exit_code = 1

    except OSError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        print(f"Is the server running at {url}?", file=sys.stderr)
        return 1
    except TimeoutError:
        print("Timeout waiting for server response", file=sys.stderr)
        return 1

    return exit_code


async def run_headless_client(url: str) -> None:
    """Connect and run a headless session reading JSON from stdin.

    Each line on stdin is a JSON message sent to the server::

        {"type": "input", "line": "ls"}
        {"type": "key", "key": "ArrowUp"}

    Server responses are written to stdout as one JSON object per line.
    This mode requires no terminal and works with piped input, making
    it suitable for automation, scripting, and Claude Code interaction.
    """
    try:
        async with connect(url) as ws:
            await _headless_loop(ws)
    except OSError as e:
        print(json.dumps({"type": "error", "message": f"Connection failed: {e}"}))
        sys.exit(1)


async def _headless_loop(ws) -> None:
    """Headless client loop: JSON on stdin → WS, WS → JSON on stdout."""
    reader_task = asyncio.create_task(_headless_server_reader(ws))
    writer_task = asyncio.create_task(_headless_stdin_sender(ws))

    done, pending = await asyncio.wait(
        [reader_task, writer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    for task in done:
        exc = task.exception()
        if exc is not None and not isinstance(
            exc, ConnectionClosed | asyncio.CancelledError
        ):
            raise exc


async def _headless_server_reader(ws) -> None:
    """Read server messages and write them as JSON lines to stdout."""
    try:
        async for raw in ws:
            msg = json.loads(raw)
            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()

            if msg.get("type") == "exit":
                break
    except ConnectionClosed:
        pass


async def _headless_stdin_sender(ws) -> None:
    """Read JSON lines from stdin and send them to the server."""
    loop = asyncio.get_running_loop()

    while True:
        # Read a line from stdin in a thread to avoid blocking the event loop
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            # EOF — send exit
            await ws.send(json.dumps({"type": "input", "line": "exit"}))
            break

        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # Treat plain text as a shell command for convenience
            msg = {"type": "input", "line": line}

        await ws.send(json.dumps(msg))


async def _session_loop(ws) -> None:
    """Main client loop: read server messages, send user input."""
    completer = _WebSocketCompleter(ws)

    input_queue: asyncio.Queue[str | tuple[str, str] | None] = asyncio.Queue()

    reader_task = asyncio.create_task(_server_reader(ws, input_queue, completer))
    writer_task = asyncio.create_task(_user_input_sender(ws, input_queue, completer))

    done, pending = await asyncio.wait(
        [reader_task, writer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    # Re-raise exceptions from completed tasks
    for task in done:
        exc = task.exception()
        if exc is not None and not isinstance(
            exc, ConnectionClosed | asyncio.CancelledError
        ):
            raise exc


async def _server_reader(
    ws,
    input_queue: asyncio.Queue[str | tuple[str, str] | None],
    completer: _WebSocketCompleter,
) -> None:
    """Read messages from the server and display them."""
    try:
        async for raw in ws:
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "output":
                text = msg.get("text", "")
                sys.stdout.write(text)
                sys.stdout.flush()

            elif msg_type == "prompt":
                prompt_text = msg.get("text", "$ ")
                # Signal the input task with the new prompt
                input_queue.put_nowait(prompt_text)

            elif msg_type == "completions":
                items = msg.get("items", [])
                replace = msg.get("replace", 0)
                completer.feed_completions(items, replace)

            elif msg_type == "mode":
                mode = msg.get("mode", "cooked")
                input_queue.put_nowait((_MODE_CHANGE, mode))

            elif msg_type == "screen":
                lines = msg.get("lines", [])
                cursor = msg.get("cursor", [0, 0])
                _render_screen(lines, cursor)

            elif msg_type == "exit":
                break

            elif msg_type == "error":
                err = msg.get("message", "Unknown error")
                sys.stderr.write(f"Server error: {err}\n")

    except ConnectionClosed:
        pass


async def _user_input_sender(
    ws,
    input_queue: asyncio.Queue[str | tuple[str, str] | None],
    completer: _WebSocketCompleter,
) -> None:
    """Read lines from the user (via prompt_toolkit) and send them to the server."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.patch_stdout import patch_stdout

    session: PromptSession[str] = PromptSession(
        completer=completer,
        complete_while_typing=False,
    )

    mode = "cooked"

    with patch_stdout(raw=True):
        while True:
            if mode == "cooked":
                # Wait for the server to send a prompt or mode change
                item = await input_queue.get()
                if item is None:
                    break

                # Check for mode change
                if isinstance(item, tuple):
                    if item[0] == _MODE_CHANGE:
                        mode = item[1]
                    continue

                prompt_text: str = item

                try:
                    line = await session.prompt_async(ANSI(prompt_text))
                except KeyboardInterrupt:
                    sys.stdout.write("\n")
                    continue
                except EOFError:
                    # User pressed Ctrl-D — send exit command
                    await ws.send(json.dumps({"type": "input", "line": "exit"}))
                    break

                await ws.send(json.dumps({"type": "input", "line": line}))

            else:
                # Raw mode: read keystrokes and send them directly
                # Use asyncio.wait to handle both key input and queue signals
                key_task = asyncio.ensure_future(_read_raw_key())
                queue_task = asyncio.ensure_future(input_queue.get())

                done, pending = await asyncio.wait(
                    [key_task, queue_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                for task in done:
                    result = task.result()

                    if task is key_task:
                        await ws.send(json.dumps({"type": "key", "key": result}))
                    elif task is queue_task:
                        if result is None:
                            return
                        if isinstance(result, tuple) and result[0] == _MODE_CHANGE:
                            mode = result[1]
                            if mode == "cooked":
                                # Clear screen to prepare for cooked mode
                                sys.stdout.write("\033[2J\033[H")
                                sys.stdout.flush()
