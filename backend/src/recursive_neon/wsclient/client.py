"""
WebSocket terminal client implementation.

Connects to the server's /ws/terminal endpoint and runs an interactive
REPL using prompt_toolkit for local line editing and tab completion.
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


async def _session_loop(ws) -> None:
    """Main client loop: read server messages, send user input."""
    completer = _WebSocketCompleter(ws)

    input_queue: asyncio.Queue[str | None] = asyncio.Queue()

    reader_task = asyncio.create_task(
        _server_reader(ws, input_queue, completer)
    )
    writer_task = asyncio.create_task(
        _user_input_sender(ws, input_queue, completer)
    )

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
            exc, (ConnectionClosed, asyncio.CancelledError)
        ):
            raise exc


async def _server_reader(
    ws,
    input_queue: asyncio.Queue[str | None],
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

            elif msg_type == "exit":
                break

            elif msg_type == "error":
                err = msg.get("message", "Unknown error")
                sys.stderr.write(f"Server error: {err}\n")

    except ConnectionClosed:
        pass


async def _user_input_sender(
    ws,
    input_queue: asyncio.Queue[str | None],
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

    with patch_stdout(raw=True):
        while True:
            # Wait for the server to send a prompt
            prompt_text = await input_queue.get()
            if prompt_text is None:
                break

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
