"""Tests for WebSocket client --command batch mode (Phase 7b-4)."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from unittest.mock import patch

import pytest

from recursive_neon.wsclient.client import run_batch_client


class FakeWebSocket:
    """Mock WebSocket that replays a scripted server conversation."""

    def __init__(self, messages: list[dict]) -> None:
        self._messages = [json.dumps(m) for m in messages]
        self._idx = 0
        self._sent: list[dict] = []

    async def recv(self) -> str:
        if self._idx >= len(self._messages):
            raise asyncio.CancelledError
        msg = self._messages[self._idx]
        self._idx += 1
        return msg

    async def send(self, data: str) -> None:
        self._sent.append(json.loads(data))

    @property
    def sent(self) -> list[dict]:
        return self._sent

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.unit
class TestBatchClient:
    """Tests for run_batch_client."""

    @pytest.mark.asyncio
    async def test_basic_command(self):
        """Batch client runs a command and captures output."""
        ws = FakeWebSocket(
            [
                {"type": "output", "text": "Welcome\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "output", "text": "hello world\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "exit"},
            ]
        )

        stdout = io.StringIO()
        with (
            patch("recursive_neon.wsclient.client.connect", return_value=ws),
            patch.object(sys, "stdout", stdout),
        ):
            exit_code = await run_batch_client("ws://test/ws/terminal", "echo hello")

        assert exit_code == 0
        assert "hello world" in stdout.getvalue()
        # Should have sent the command and then exit
        assert ws.sent[0] == {"type": "input", "line": "echo hello"}
        assert ws.sent[1] == {"type": "input", "line": "exit"}

    @pytest.mark.asyncio
    async def test_ansi_stripping_non_tty(self):
        """ANSI codes are stripped when stdout is not a TTY."""
        ws = FakeWebSocket(
            [
                {"type": "prompt", "text": "$ "},
                {"type": "output", "text": "\033[32mgreen\033[0m\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "exit"},
            ]
        )

        stdout = io.StringIO()
        stdout.isatty = lambda: False  # type: ignore[assignment]
        with (
            patch("recursive_neon.wsclient.client.connect", return_value=ws),
            patch.object(sys, "stdout", stdout),
        ):
            exit_code = await run_batch_client("ws://test/ws/terminal", "ls")

        assert exit_code == 0
        output = stdout.getvalue()
        assert "green" in output
        assert "\033[" not in output

    @pytest.mark.asyncio
    async def test_ansi_preserved_tty(self):
        """ANSI codes are preserved when stdout is a TTY."""
        ws = FakeWebSocket(
            [
                {"type": "prompt", "text": "$ "},
                {"type": "output", "text": "\033[32mgreen\033[0m\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "exit"},
            ]
        )

        stdout = io.StringIO()
        stdout.isatty = lambda: True  # type: ignore[assignment]
        with (
            patch("recursive_neon.wsclient.client.connect", return_value=ws),
            patch.object(sys, "stdout", stdout),
        ):
            exit_code = await run_batch_client("ws://test/ws/terminal", "ls")

        assert exit_code == 0
        assert "\033[32m" in stdout.getvalue()

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Connection failure returns exit code 1."""
        stderr = io.StringIO()
        with (
            patch(
                "recursive_neon.wsclient.client.connect",
                side_effect=OSError("Connection refused"),
            ),
            patch.object(sys, "stderr", stderr),
        ):
            exit_code = await run_batch_client("ws://bad/ws/terminal", "ls")

        assert exit_code == 1
        assert "Connection" in stderr.getvalue()

    @pytest.mark.asyncio
    async def test_server_error(self):
        """Server error messages are printed to stderr."""
        ws = FakeWebSocket(
            [
                {"type": "prompt", "text": "$ "},
                {"type": "error", "message": "Internal error"},
                {"type": "prompt", "text": "$ "},
                {"type": "exit"},
            ]
        )

        stderr = io.StringIO()
        stdout = io.StringIO()
        with (
            patch("recursive_neon.wsclient.client.connect", return_value=ws),
            patch.object(sys, "stdout", stdout),
            patch.object(sys, "stderr", stderr),
        ):
            exit_code = await run_batch_client("ws://test/ws/terminal", "bad")

        assert exit_code == 1
        assert "Internal error" in stderr.getvalue()

    @pytest.mark.asyncio
    async def test_welcome_banner_skipped_non_tty(self):
        """Welcome banner is not printed when stdout is not a TTY."""
        ws = FakeWebSocket(
            [
                {"type": "output", "text": "Welcome to Neon!\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "output", "text": "result\n"},
                {"type": "prompt", "text": "$ "},
                {"type": "exit"},
            ]
        )

        stdout = io.StringIO()
        stdout.isatty = lambda: False  # type: ignore[assignment]
        with (
            patch("recursive_neon.wsclient.client.connect", return_value=ws),
            patch.object(sys, "stdout", stdout),
        ):
            await run_batch_client("ws://test/ws/terminal", "cmd")

        output = stdout.getvalue()
        assert "Welcome" not in output
        assert "result" in output
