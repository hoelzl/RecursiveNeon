"""
Tests for the WebSocket terminal session manager, QueueOutput, and
the /ws/terminal endpoint.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from recursive_neon.config import settings
from recursive_neon.dependencies import (
    ServiceFactory,
    initialize_container,
    reset_container,
)
from recursive_neon.main import app
from recursive_neon.models.game_state import SystemStatus
from recursive_neon.shell.output import QueueOutput
from recursive_neon.terminal import TerminalSessionManager, WebSocketInput

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_global_container():
    yield
    reset_container()


@pytest.fixture
def container(mock_llm):
    """A test ServiceContainer with initialized filesystem."""
    npc_manager = ServiceFactory.create_npc_manager(llm=mock_llm)
    c = ServiceFactory.create_test_container(mock_npc_manager=npc_manager)
    c.app_service.load_initial_filesystem(initial_fs_dir=str(settings.initial_fs_path))
    npc_manager.create_default_npcs()
    c.system_state.status = SystemStatus.READY
    return c


@pytest.fixture
def client(container):
    """A FastAPI TestClient with initialized container + terminal manager."""
    initialize_container(container)
    app.state.terminal_manager = TerminalSessionManager(container=container)
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# QueueOutput tests
# ============================================================================


class TestQueueOutput:
    def test_write_puts_output_message(self):
        q: asyncio.Queue[dict] = asyncio.Queue()
        out = QueueOutput(q)
        out.write("hello")
        msg = q.get_nowait()
        assert msg == {"type": "output", "text": "hello"}

    def test_writeln_appends_newline(self):
        q: asyncio.Queue[dict] = asyncio.Queue()
        out = QueueOutput(q)
        out.writeln("world")
        msg = q.get_nowait()
        assert msg["text"] == "world\n"

    def test_writeln_empty(self):
        q: asyncio.Queue[dict] = asyncio.Queue()
        out = QueueOutput(q)
        out.writeln()
        msg = q.get_nowait()
        assert msg["text"] == "\n"

    def test_error_includes_ansi(self):
        q: asyncio.Queue[dict] = asyncio.Queue()
        out = QueueOutput(q)
        out.error("oops")
        msg = q.get_nowait()
        assert "oops" in msg["text"]
        assert "\033[" in msg["text"]  # ANSI codes present

    def test_styled_preserves_ansi(self):
        q: asyncio.Queue[dict] = asyncio.Queue()
        out = QueueOutput(q)
        result = out.styled("hi", "\033[32m")
        assert "\033[32m" in result
        assert "hi" in result


# ============================================================================
# WebSocketInput tests
# ============================================================================


class TestWebSocketInput:
    async def test_get_line_returns_queued_line(self):
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[dict] = asyncio.Queue()
        inp = WebSocketInput(in_q, out_q)

        in_q.put_nowait("ls -la")
        line = await inp.get_line("$ ")
        assert line == "ls -la"

    async def test_get_line_sends_prompt_to_output_queue(self):
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[dict] = asyncio.Queue()
        inp = WebSocketInput(in_q, out_q)

        in_q.put_nowait("pwd")
        await inp.get_line("user@neon:~$ ")

        prompt_msg = out_q.get_nowait()
        assert prompt_msg["type"] == "prompt"
        assert "user@neon" in prompt_msg["text"]

    async def test_get_line_eof_on_none(self):
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[dict] = asyncio.Queue()
        inp = WebSocketInput(in_q, out_q)

        in_q.put_nowait(None)
        with pytest.raises(EOFError):
            await inp.get_line("$ ")


# ============================================================================
# TerminalSessionManager tests
# ============================================================================


class TestTerminalSessionManager:
    async def test_create_session(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()
        assert session.session_id
        assert mgr.active_count == 1
        await mgr.remove_session(session.session_id)

    async def test_get_session(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()
        found = mgr.get_session(session.session_id)
        assert found is session
        await mgr.remove_session(session.session_id)

    def test_get_session_missing(self, container):
        mgr = TerminalSessionManager(container=container)
        assert mgr.get_session("nonexistent") is None

    async def test_remove_session(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()
        sid = session.session_id
        await mgr.remove_session(sid)
        assert mgr.active_count == 0
        assert mgr.get_session(sid) is None

    async def test_remove_nonexistent_session(self, container):
        """Removing a session that doesn't exist should be a no-op."""
        mgr = TerminalSessionManager(container=container)
        await mgr.remove_session("does-not-exist")
        assert mgr.active_count == 0

    async def test_multiple_sessions(self, container):
        mgr = TerminalSessionManager(container=container)
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        assert mgr.active_count == 2
        assert s1.session_id != s2.session_id
        await mgr.remove_session(s1.session_id)
        await mgr.remove_session(s2.session_id)

    async def test_auto_save_triggered(self, container, tmp_path):
        """Auto-save task should start when a session is created."""
        mgr = TerminalSessionManager(
            container=container,
            data_dir=str(tmp_path),
        )
        # Override interval to make the test fast
        mgr.AUTO_SAVE_INTERVAL_SECONDS = 0.05

        session = mgr.create_session()
        assert mgr._auto_save_task is not None
        assert not mgr._auto_save_task.done()

        # Wait long enough for at least one auto-save cycle
        await asyncio.sleep(0.15)

        # Clean up
        await mgr.remove_session(session.session_id)

        # After removing all sessions, the auto-save task should stop
        # (it may take one more cycle to notice)
        await asyncio.sleep(0.1)


# ============================================================================
# TerminalSession start/stop tests
# ============================================================================


class TestTerminalSession:
    async def test_start_and_stop(self, container):
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        await session.start()
        assert session._shell_task is not None
        assert not session._shell_task.done()

        await session.stop()
        # Shell task should complete after receiving EOF
        await asyncio.sleep(0.1)
        assert session._shell_task.done()

    async def test_feed_line_and_get_output(self, container):
        """Feed a command and verify output appears in the queue."""
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        await session.start()

        # Drain the welcome banner + first prompt
        messages = await _drain_queue(session.output_queue, timeout=2.0)
        assert any(m["type"] == "prompt" for m in messages)
        assert any("Recursive://Neon" in m.get("text", "") for m in messages)

        # Send a command
        session.feed_line("pwd")

        # Read output until the next prompt
        messages = await _drain_queue(session.output_queue, timeout=2.0)
        output_texts = [m["text"] for m in messages if m["type"] == "output"]
        combined = "".join(output_texts)
        assert "/" in combined  # pwd should output "/"

        await session.stop()

    async def test_exit_command_produces_exit_message(self, container):
        """The 'exit' command should produce an exit message."""
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()
        await session.start()

        # Drain welcome banner
        await _drain_queue(session.output_queue, timeout=2.0)

        session.feed_line("exit")
        messages = await _drain_queue(session.output_queue, timeout=2.0)
        assert any(m["type"] == "exit" for m in messages)

    async def test_tab_completion(self, container):
        """Shell.get_completions should work for WebSocket completion requests."""
        mgr = TerminalSessionManager(container=container)
        session = mgr.create_session()

        # Don't need to start the REPL — get_completions works synchronously
        completions = session.shell.get_completions("l")
        assert "ls" in completions

        completions = session.shell.get_completions("ls Doc")
        assert any("Documents" in c for c in completions)


# ============================================================================
# /ws/terminal integration tests
# ============================================================================


class TestTerminalWebSocket:
    def test_connect_and_receive_banner(self, client):
        """Connecting to /ws/terminal should produce welcome banner + prompt."""
        with client.websocket_connect("/ws/terminal") as ws:
            messages = _recv_until_prompt_sync(ws, timeout=5.0)

            output_texts = [m["text"] for m in messages if m["type"] == "output"]
            combined = "".join(output_texts)
            assert "Recursive://Neon" in combined

            prompts = [m for m in messages if m["type"] == "prompt"]
            assert len(prompts) >= 1

    def test_execute_command(self, client):
        """Send 'pwd' and verify we get '/' back."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input", "line": "pwd"})
            messages = _recv_until_prompt_sync(ws, timeout=5.0)

            output_texts = [m["text"] for m in messages if m["type"] == "output"]
            combined = "".join(output_texts)
            assert "/" in combined

    def test_execute_ls(self, client):
        """Send 'ls' and verify filesystem listing."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input", "line": "ls"})
            messages = _recv_until_prompt_sync(ws, timeout=5.0)

            output_texts = [m["text"] for m in messages if m["type"] == "output"]
            combined = "".join(output_texts)
            assert "Documents" in combined

    def test_stateful_cd_then_pwd(self, client):
        """Session state persists across commands."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input", "line": "cd Documents"})
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input", "line": "pwd"})
            messages = _recv_until_prompt_sync(ws, timeout=5.0)

            output_texts = [m["text"] for m in messages if m["type"] == "output"]
            combined = "".join(output_texts)
            assert "/Documents" in combined

    def test_tab_completion_request(self, client):
        """Send a completion request and get results."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "complete", "line": "l"})
            resp = ws.receive_json()
            assert resp["type"] == "completions"
            assert "ls" in resp["items"]

    def test_unknown_message_type(self, client):
        """Unknown message types should return an error."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "bogus"})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    def test_exit_command_closes_session(self, client):
        """Sending 'exit' should produce an exit message."""
        with client.websocket_connect("/ws/terminal") as ws:
            _recv_until_prompt_sync(ws, timeout=5.0)

            ws.send_json({"type": "input", "line": "exit"})
            messages = _recv_all_sync(ws, timeout=5.0)
            assert any(m.get("type") == "exit" for m in messages)


# ============================================================================
# Test helpers
# ============================================================================


async def _drain_queue(
    queue: asyncio.Queue[dict],
    timeout: float = 2.0,
) -> list[dict]:
    """Drain messages from a queue until a prompt or exit message, or timeout."""
    messages: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            msg = await asyncio.wait_for(queue.get(), timeout=remaining)
            messages.append(msg)
            if msg["type"] in ("prompt", "exit"):
                break
        except TimeoutError:
            break
    return messages


def _recv_until_prompt_sync(ws, timeout: float = 5.0) -> list[dict]:
    """Receive WebSocket messages until a prompt message (synchronous TestClient)."""
    import time

    messages = []
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") in ("prompt", "exit"):
                break
        except Exception:
            break
    return messages


def _recv_all_sync(ws, timeout: float = 5.0) -> list[dict]:
    """Receive all WebSocket messages until timeout or connection close."""
    import time

    messages = []
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") == "exit":
                break
        except Exception:
            break
    return messages
