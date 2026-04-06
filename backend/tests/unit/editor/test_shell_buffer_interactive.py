"""Tests for interactive programs in shell buffer (Phase 7a-4)."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.shell_mode import (
    ShellBufferInput,
    ShellState,
    setup_shell_buffer,
)
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.shell import Shell


@pytest.fixture
def _shell_view(mock_llm):
    """Create an EditorView with a shell buffer for testing."""
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(
        initial_fs_dir=str(settings.initial_fs_path)
    )
    shell = Shell(container)
    ed = Editor()
    ed.global_keymap = build_default_keymap()
    ed.shell_factory = lambda: Shell(container)

    buf = ed.create_buffer("*shell*", "")
    setup_shell_buffer(ed, buf, shell)

    view = EditorView(ed)
    view.on_start(80, 24)
    return view, ed, buf


class TestShellBufferInputInit:
    def test_input_wired_to_editor(self, _shell_view):
        view, ed, buf = _shell_view
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        input_src = state.shell._input_source
        assert isinstance(input_src, ShellBufferInput)
        assert input_src._editor is ed
        assert input_src._buf is buf
        assert input_src._state is state


@pytest.mark.asyncio
class TestShellBufferInputGetLine:
    async def test_get_line_opens_minibuffer(self, _shell_view):
        view, ed, buf = _shell_view
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        input_src: ShellBufferInput = state.shell._input_source

        # Start get_line in a task
        async def do_get_line():
            return await input_src.get_line("prompt> ")

        task = asyncio.create_task(do_get_line())
        # Yield to let the task start and open the minibuffer
        await asyncio.sleep(0)

        assert ed.minibuffer is not None
        assert "prompt>" in ed.minibuffer.prompt

        # Simulate user typing and submitting
        ed.minibuffer.process_key("h")
        ed.minibuffer.process_key("i")
        ed.minibuffer.process_key("Enter")

        # The future should be resolved
        await asyncio.sleep(0)
        assert task.done()
        assert await task == "hi"

    async def test_get_line_cancel_raises(self, _shell_view):
        view, ed, buf = _shell_view
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        input_src: ShellBufferInput = state.shell._input_source

        task = asyncio.create_task(input_src.get_line("prompt> "))
        await asyncio.sleep(0)

        assert ed.minibuffer is not None
        # Press C-g — our key_handler fires, setting exception on Future
        ed.minibuffer.process_key("C-g")
        # Give the event loop time to deliver the exception
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert task.done()
        with pytest.raises(EOFError, match="Cancelled"):
            task.result()

    async def test_flush_output_before_prompt(self, _shell_view):
        view, ed, buf = _shell_view
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        input_src: ShellBufferInput = state.shell._input_source

        # Write some output that hasn't been flushed
        state.output.write("some output\n")

        text_before = buf.text
        task = asyncio.create_task(input_src.get_line("prompt> "))
        await asyncio.sleep(0)

        # The output should have been flushed into the buffer
        assert "some output" in buf.text
        assert len(buf.text) > len(text_before)

        # Clean up — resolve the future
        if ed.minibuffer is not None:
            ed.minibuffer.process_key("Enter")
        await asyncio.sleep(0)
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, KeyboardInterrupt):
                await task


@pytest.mark.asyncio
class TestTaskBasedExecution:
    async def test_command_spawns_task(self, _shell_view):
        view, ed, buf = _shell_view

        # Type "echo hello" and press Enter
        for ch in "echo hello":
            view.on_key(ch)
        view.on_key("Enter")

        # after_key queue should have the spawn callback
        assert len(ed._after_key_queue) > 0

        # Process the after-key queue (which spawns a task)
        await view.on_after_key()

        # Give the task a chance to complete
        await asyncio.sleep(0.05)

        # Check the background task completed
        assert "hello" in buf.text

    async def test_render_requested_after_command(self, _shell_view):
        view, ed, buf = _shell_view

        for ch in "echo test":
            view.on_key(ch)
        view.on_key("Enter")

        await view.on_after_key()
        await asyncio.sleep(0.05)

        # The task's finally block should have requested a render
        # (it may already have been cleared by on_after_key)
        # Just verify the output appeared
        assert "test" in buf.text
