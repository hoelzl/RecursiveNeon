"""Tests for the Output abstraction and WebSocket composition."""

from __future__ import annotations

import asyncio

import pytest

from recursive_neon.shell.output import CapturedOutput, QueueOutput
from recursive_neon.shell.shell import Shell


def _drain(queue: asyncio.Queue[dict]) -> list[dict]:
    messages: list[dict] = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages


@pytest.mark.unit
class TestOutputComposition:
    def test_queue_output_with_stderr_routes_writes_to_queue(self):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        cap = CapturedOutput()
        composed = QueueOutput(queue).with_stderr(cap)

        composed.write("hello")
        composed.writeln("world")

        messages = _drain(queue)
        assert [m["text"] for m in messages] == ["hello", "world\n"]

    def test_queue_output_with_stderr_routes_errors_to_other(self):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        cap = CapturedOutput()
        composed = QueueOutput(queue).with_stderr(cap)

        composed.error("oops")

        assert "oops" in cap.error_text
        assert not any("oops" in str(m.get("text", "")) for m in _drain(queue))

    def test_queue_output_merge_stderr_routes_errors_to_queue(self):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        merged = QueueOutput(queue).merge_stderr()

        merged.write("stdout")
        merged.error("stderr")

        messages = _drain(queue)
        texts = [m["text"] for m in messages]
        assert any("stdout" in t for t in texts)
        assert any("stderr" in t for t in texts)

    def test_captured_output_with_stderr_routes_errors_to_other(self):
        out = CapturedOutput()
        err = CapturedOutput()
        composed = out.with_stderr(err)

        composed.write("stdout")
        composed.error("stderr")

        assert "stdout" in out.text
        assert "stderr" in err.error_text
        assert "stderr" not in out.text

    def test_captured_output_merge_stderr_merges_errors_to_stdout(self):
        out = CapturedOutput()
        merged = out.merge_stderr()

        merged.write("stdout")
        merged.error("stderr")

        assert "stdout" in out.text
        assert "stderr" in out.text


@pytest.mark.unit
class TestQueueOutputIntegration:
    @pytest.fixture
    def queue(self):
        return asyncio.Queue()

    @pytest.fixture
    def qshell(self, test_container, queue):
        return Shell(container=test_container, output=QueueOutput(queue))

    @pytest.mark.asyncio
    async def test_stderr_redirect_to_file_over_websocket(self, qshell, queue):
        """stderr capture to a file must not leak into the WebSocket queue."""
        exit_code = await qshell.execute_line("cd nonexistent 2> err.txt")
        assert exit_code == 1

        stdout_texts = [m["text"] for m in _drain(queue)]
        assert not any("nonexistent" in t for t in stdout_texts)

        node = qshell.session.resolve_path("err.txt")
        assert "nonexistent" in (node.content or "")

    @pytest.mark.asyncio
    async def test_stdout_preserved_when_stderr_redirected_over_websocket(
        self, qshell, queue
    ):
        """stdout must still reach the WebSocket queue when stderr is redirected."""
        exit_code = await qshell.execute_line("export 2> err.txt")
        assert exit_code == 0

        stdout_texts = [m["text"] for m in _drain(queue)]
        assert any("USER=" in t for t in stdout_texts)

    @pytest.mark.asyncio
    async def test_2and1_redirect_over_websocket(self, qshell, queue):
        """2>&1 must make stderr visible in the WebSocket queue."""
        exit_code = await qshell.execute_line("cat nonexistent 2>&1")
        assert exit_code != 0

        texts = [m["text"] for m in _drain(queue)]
        assert any("nonexistent" in t for t in texts)

    @pytest.mark.asyncio
    async def test_builtin_stderr_redirect_in_pipeline(self, qshell, queue):
        """A builtin in a pipeline with stderr-to-stdout merge must not drop errors."""
        exit_code = await qshell.execute_line("echo foo | cd nonexistent 2>&1")
        assert exit_code == 1

        texts = [m["text"] for m in _drain(queue)]
        assert any("nonexistent" in t for t in texts)
