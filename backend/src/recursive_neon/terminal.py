"""
WebSocket terminal session manager.

Manages Shell instances that are driven over WebSocket connections.
Each connection gets its own session; sessions are owned by the manager
(not the WebSocket) so that persistent sessions can be added later
without architectural changes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from recursive_neon.dependencies import ServiceContainer
from recursive_neon.shell.output import QueueOutput
from recursive_neon.shell.shell import Shell
from recursive_neon.shell.tui import TuiApp
from recursive_neon.shell.tui.runner import run_tui_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WebSocketInput — feeds command lines from the WS handler into the Shell
# ---------------------------------------------------------------------------


class WebSocketInput:
    """InputSource that receives lines from an asyncio.Queue.

    The WebSocket handler puts lines into the queue; the Shell's REPL
    loop reads them out via ``get_line()``.

    When ``get_line`` is called, it first pushes a ``prompt`` message
    onto the output queue so the WS handler knows the shell is ready
    for the next command.  This avoids race conditions where the writer
    might send a premature prompt between partial output writes.
    """

    def __init__(
        self,
        input_queue: asyncio.Queue[str | None],
        output_queue: asyncio.Queue[dict],
    ) -> None:
        self._input = input_queue
        self._output = output_queue

    async def get_line(
        self,
        prompt: str,
        *,
        complete: bool = True,
        history_id: str | None = None,
    ) -> str:
        """Signal readiness via the output queue, then wait for input."""
        self._output.put_nowait({"type": "prompt", "text": prompt})
        line = await self._input.get()
        if line is None:
            raise EOFError
        return line


# ---------------------------------------------------------------------------
# WebSocketRawInput — feeds individual keystrokes for TUI apps
# ---------------------------------------------------------------------------


class WebSocketRawInput:
    """RawInputSource backed by the WebSocket key queue."""

    def __init__(self, key_queue: asyncio.Queue[str | None]) -> None:
        self._key_queue = key_queue

    async def get_key(self) -> str:
        key = await self._key_queue.get()
        if key is None:
            raise EOFError
        return key


# ---------------------------------------------------------------------------
# TerminalSession — one per WebSocket connection
# ---------------------------------------------------------------------------


@dataclass
class TerminalSession:
    """A single terminal session driven over WebSocket.

    Owns a Shell, an input queue (WS handler → Shell), and an output
    queue (Shell → WS handler).  Supports both cooked mode (line input)
    and raw mode (keystroke input for TUI apps).
    """

    session_id: str
    shell: Shell
    input_queue: asyncio.Queue[str | None] = field(default_factory=asyncio.Queue)
    output_queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    key_queue: asyncio.Queue[str | None] = field(default_factory=asyncio.Queue)
    mode: str = "cooked"
    _shell_task: asyncio.Task | None = field(default=None, repr=False)

    async def start(self) -> None:
        """Start the shell REPL as a background task."""
        ws_input = WebSocketInput(self.input_queue, self.output_queue)
        # Replace the shell's output with one that writes to our queue
        self.shell.output = QueueOutput(self.output_queue)

        # Wire up TUI support: the shell can launch TUI apps over WebSocket
        session = self  # capture for closure

        def _run_tui_factory():
            raw_input = WebSocketRawInput(session.key_queue)

            async def _run_tui(app: TuiApp) -> int:
                return await run_tui_app(
                    app,
                    raw_input,
                    session.shell.output,
                    enter_raw=lambda: session._enter_raw_mode(),
                    exit_raw=lambda: session._exit_raw_mode(),
                    send_screen=lambda msg: session.output_queue.put_nowait(msg),
                )

            return _run_tui

        self.shell._run_tui_factory = _run_tui_factory

        self._shell_task = asyncio.create_task(
            self._run_shell(ws_input),
            name=f"terminal-{self.session_id}",
        )

    async def _run_shell(self, ws_input: WebSocketInput) -> None:
        """Run the shell and signal completion via the output queue."""
        try:
            await self.shell.run(input_source=ws_input)
        except Exception:
            logger.exception("Shell task crashed for session %s", self.session_id)
        finally:
            # Tell the WS handler that the shell exited
            self.output_queue.put_nowait({"type": "exit"})

    async def stop(self) -> None:
        """Stop the shell (e.g. on WebSocket disconnect)."""
        # Send EOF to both queues so the shell and any TUI app exit cleanly
        self.input_queue.put_nowait(None)
        self.key_queue.put_nowait(None)
        if self._shell_task is not None:
            # Give the shell a moment to shut down gracefully
            try:
                await asyncio.wait_for(self._shell_task, timeout=2.0)
            except TimeoutError:
                self._shell_task.cancel()
                logger.warning(
                    "Shell task for %s cancelled after timeout", self.session_id
                )

    def feed_line(self, line: str) -> None:
        """Send a command line into the shell (called by the WS handler)."""
        self.input_queue.put_nowait(line)

    def feed_key(self, key: str) -> None:
        """Send a keystroke to the active TUI app (called by the WS handler)."""
        self.key_queue.put_nowait(key)

    def _enter_raw_mode(self) -> None:
        """Switch to raw mode and notify the client."""
        self.mode = "raw"
        self.output_queue.put_nowait({"type": "mode", "mode": "raw"})

    def _exit_raw_mode(self) -> None:
        """Switch back to cooked mode and notify the client."""
        self.mode = "cooked"
        self.output_queue.put_nowait({"type": "mode", "mode": "cooked"})


# ---------------------------------------------------------------------------
# TerminalSessionManager — owns all active sessions
# ---------------------------------------------------------------------------


class TerminalSessionManager:
    """Manages the lifecycle of all terminal sessions.

    Sessions are identified by a UUID.  Currently each WebSocket
    connection creates a new session; persistent named sessions can be
    added later by changing the lookup/creation logic here.

    Runs a periodic auto-save task while sessions are active so that
    unexpected disconnects don't lose progress.
    """

    AUTO_SAVE_INTERVAL_SECONDS = 60

    def __init__(
        self, container: ServiceContainer, data_dir: str | None = None
    ) -> None:
        self._container = container
        self._data_dir = data_dir
        self._sessions: dict[str, TerminalSession] = {}
        self._auto_save_task: asyncio.Task | None = None

    def create_session(self) -> TerminalSession:
        """Create a new terminal session.

        All sessions share the same ``ServiceContainer`` (and thus the same
        ``GameState``).  Concurrent mutations are safe for individual method
        calls (synchronous, no await points), but compound operations should
        acquire ``container.app_service.lock`` to prevent interleaving.
        """
        session_id = uuid.uuid4().hex[:12]
        shell = Shell(
            container=self._container,
            data_dir=self._data_dir,
        )
        ts = TerminalSession(session_id=session_id, shell=shell)
        self._sessions[session_id] = ts
        logger.info("Terminal session created: %s", session_id)
        self._ensure_auto_save_running()
        return ts

    def get_session(self, session_id: str) -> TerminalSession | None:
        return self._sessions.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        """Stop and remove a session.  Saves game state immediately."""
        ts = self._sessions.pop(session_id, None)
        if ts is not None:
            await ts.stop()
            self._save_game_state()
            logger.info("Terminal session removed: %s", session_id)

        # Stop auto-save if no sessions remain
        if not self._sessions and self._auto_save_task is not None:
            self._auto_save_task.cancel()
            self._auto_save_task = None

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    # -- auto-save ----------------------------------------------------------

    def _ensure_auto_save_running(self) -> None:
        if self._auto_save_task is None or self._auto_save_task.done():
            self._auto_save_task = asyncio.create_task(
                self._auto_save_loop(), name="terminal-auto-save"
            )

    async def _auto_save_loop(self) -> None:
        """Periodically save game state while sessions are active."""
        try:
            while self._sessions:
                await asyncio.sleep(self.AUTO_SAVE_INTERVAL_SECONDS)
                if self._sessions:
                    self._save_game_state()
        except asyncio.CancelledError:
            pass

    def _save_game_state(self) -> None:
        if not self._data_dir:
            return
        try:
            self._container.app_service.save_all_to_disk(self._data_dir)
            self._container.npc_manager.save_npcs_to_disk(self._data_dir)
            logger.info("Auto-save: game state saved to %s", self._data_dir)
        except Exception:
            logger.exception("Auto-save failed")
