"""Tests for shell-in-editor (Phase 6j).

Tests cover:
- ANSI stripping
- BufferOutput capture
- Shell buffer setup
- Input extraction and replacement
- comint-send-input (Enter)
- History navigation (M-p / M-n)
- Tab completion
- Async command execution
- EditorView.on_after_key
- Integration (full command cycle)
"""

from __future__ import annotations

import pytest

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.shell_mode import (
    BufferOutput,
    ShellBufferInput,
    ShellState,
    _comint_next_input,
    _comint_previous_input,
    _comint_send_input,
    _get_current_input,
    _get_input_up_to_point,
    _replace_input,
    _shell_complete,
    execute_shell_command,
    setup_shell_buffer,
    strip_ansi,
)
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.shell import Shell

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def test_container(mock_llm):
    """A test ServiceContainer with initialised filesystem."""
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(
        initial_fs_dir=str(settings.initial_fs_path)
    )
    return container


@pytest.fixture
def shell(test_container):
    """A Shell instance for testing."""
    return Shell(test_container)


@pytest.fixture
def editor():
    """An Editor with default keymap."""
    return Editor(global_keymap=build_default_keymap())


@pytest.fixture
def shell_editor(editor, shell):
    """An editor with a *shell* buffer already set up."""
    buf = editor.create_buffer(name="*shell*")
    setup_shell_buffer(editor, buf, shell)
    return editor


@pytest.fixture
def shell_view(editor, shell):
    """An EditorView with a *shell* buffer, ready for TUI-level testing."""
    editor.shell_factory = lambda: shell
    view = EditorView(editor=editor)
    view.on_start(80, 24)
    # Invoke M-x shell through the view (so window sync works)
    view.on_key("M-x")
    for ch in "shell":
        view.on_key(ch)
    view.on_key("Enter")
    assert editor.buffer.name == "*shell*"
    return view


# ═══════════════════════════════════════════════════════════════════
# strip_ansi
# ═══════════════════════════════════════════════════════════════════


class TestStripAnsi:
    def test_plain_text(self):
        assert strip_ansi("hello") == "hello"

    def test_color_codes(self):
        assert strip_ansi("\033[31mred\033[0m") == "red"

    def test_bold_and_dim(self):
        assert strip_ansi("\033[1mbold\033[2mdim\033[0m") == "bolddim"

    def test_mixed_content(self):
        text = "\033[32muser\033[0m@\033[36mhost\033[0m:/ $ "
        assert strip_ansi(text) == "user@host:/ $ "

    def test_empty_string(self):
        assert strip_ansi("") == ""


# ═══════════════════════════════════════════════════════════════════
# BufferOutput
# ═══════════════════════════════════════════════════════════════════


class TestBufferOutput:
    def test_write(self):
        out = BufferOutput()
        out.write("hello")
        assert out.drain() == "hello"

    def test_writeln(self):
        out = BufferOutput()
        out.writeln("hello")
        assert out.drain() == "hello\n"

    def test_error(self):
        out = BufferOutput()
        out.error("oops")
        assert out.drain() == "oops\n"

    def test_drain_clears(self):
        out = BufferOutput()
        out.write("a")
        out.drain()
        assert out.drain() == ""

    def test_accumulation(self):
        out = BufferOutput()
        out.write("a")
        out.writeln("b")
        out.error("c")
        assert out.drain() == "ab\nc\n"

    def test_preserves_ansi(self):
        """BufferOutput preserves raw ANSI for later parsing by the attr layer."""
        out = BufferOutput()
        out.write("\033[31mred\033[0m text")
        assert out.drain() == "\033[31mred\033[0m text"


# ═══════════════════════════════════════════════════════════════════
# ShellBufferInput
# ═══════════════════════════════════════════════════════════════════


class TestShellBufferInput:
    @pytest.mark.asyncio
    async def test_raises_eof(self):
        inp = ShellBufferInput()
        with pytest.raises(EOFError):
            await inp.get_line("prompt> ")


# ═══════════════════════════════════════════════════════════════════
# setup_shell_buffer
# ═══════════════════════════════════════════════════════════════════


class TestSetupShellBuffer:
    def test_buffer_name(self, shell_editor):
        assert shell_editor.buffer.name == "*shell*"

    def test_major_mode(self, shell_editor):
        assert shell_editor.buffer.major_mode is not None
        assert shell_editor.buffer.major_mode.name == "shell-mode"

    def test_contains_banner(self, shell_editor):
        text = shell_editor.buffer.text
        assert "Recursive://Neon" in text

    def test_contains_prompt(self, shell_editor):
        text = shell_editor.buffer.text
        assert "$ " in text

    def test_input_start_at_end(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        # input_start should be at end of buffer (after prompt)
        last_line = buf.line_count - 1
        last_col = len(buf.lines[-1])
        assert state.input_start.line == last_line
        assert state.input_start.col == last_col

    def test_keymap_present(self, shell_editor):
        assert shell_editor.buffer.keymap is not None
        assert shell_editor.buffer.keymap.name == "shell-mode-map"

    def test_not_modified(self, shell_editor):
        assert not shell_editor.buffer.modified

    def test_shell_output_configured(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert isinstance(state.output, BufferOutput)
        assert state.shell.output is state.output

    def test_input_source_configured(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert isinstance(state.shell._input_source, ShellBufferInput)


# ═══════════════════════════════════════════════════════════════════
# _get_current_input / _get_input_up_to_point
# ═══════════════════════════════════════════════════════════════════


class TestGetCurrentInput:
    def test_empty_input(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == ""

    def test_with_typed_text(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        buf.insert_string("ls -la")
        assert _get_current_input(buf, state) == "ls -la"

    def test_input_up_to_point(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        buf.insert_string("hello world")
        # Move point back to after "hello "
        buf.point.move_to(buf.point.line, buf.point.col - 5)
        assert _get_input_up_to_point(buf, state) == "hello "

    def test_input_up_to_point_at_start(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        # Point is at input_start — no input before cursor
        assert _get_input_up_to_point(buf, state) == ""


# ═══════════════════════════════════════════════════════════════════
# _replace_input
# ═══════════════════════════════════════════════════════════════════


class TestReplaceInput:
    def test_replace_empty_with_text(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        _replace_input(buf, state, "ls")
        assert _get_current_input(buf, state) == "ls"

    def test_replace_text_with_longer(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        buf.insert_string("ls")
        _replace_input(buf, state, "ls -la")
        assert _get_current_input(buf, state) == "ls -la"

    def test_replace_text_with_shorter(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        buf.insert_string("ls -la")
        _replace_input(buf, state, "ls")
        assert _get_current_input(buf, state) == "ls"

    def test_replace_with_empty(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        buf.insert_string("hello")
        _replace_input(buf, state, "")
        assert _get_current_input(buf, state) == ""


# ═══════════════════════════════════════════════════════════════════
# _comint_send_input
# ═══════════════════════════════════════════════════════════════════


class TestComintSendInput:
    def test_queues_after_key(self, shell_editor):
        buf = shell_editor.buffer
        buf.insert_string("ls")
        _comint_send_input(shell_editor, None)
        assert len(shell_editor._after_key_queue) > 0

    def test_inserts_newline(self, shell_editor):
        buf = shell_editor.buffer
        line_count_before = buf.line_count
        buf.insert_string("ls")
        _comint_send_input(shell_editor, None)
        assert buf.line_count == line_count_before + 1

    def test_empty_input_still_queued(self, shell_editor):
        _comint_send_input(shell_editor, None)
        assert len(shell_editor._after_key_queue) > 0

    def test_finished_shell_ignored(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        state.finished = True
        _comint_send_input(shell_editor, None)
        assert len(shell_editor._after_key_queue) == 0

    def test_resets_history_nav(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        state.history_index = 3
        state.saved_input = "partial"
        buf.insert_string("ls")
        _comint_send_input(shell_editor, None)
        assert state.history_index == -1
        assert state.saved_input == ""


# ═══════════════════════════════════════════════════════════════════
# History navigation
# ═══════════════════════════════════════════════════════════════════


class TestHistoryNavigation:
    def _add_history(self, shell_editor, *entries):
        state: ShellState = shell_editor.buffer._shell_state  # type: ignore
        state.shell.session.history.extend(entries)

    def test_previous_shows_last(self, shell_editor):
        self._add_history(shell_editor, "ls", "pwd")
        _comint_previous_input(shell_editor, None)
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == "pwd"

    def test_previous_twice(self, shell_editor):
        self._add_history(shell_editor, "ls", "pwd")
        _comint_previous_input(shell_editor, None)
        _comint_previous_input(shell_editor, None)
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == "ls"

    def test_previous_at_beginning(self, shell_editor):
        self._add_history(shell_editor, "ls")
        _comint_previous_input(shell_editor, None)
        _comint_previous_input(shell_editor, None)
        # Should stay at "ls" and show message
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == "ls"
        assert "Beginning" in shell_editor.message

    def test_next_restores_saved(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        self._add_history(shell_editor, "ls", "pwd")
        # Type partial input
        buf.insert_string("cat")
        # Navigate back
        _comint_previous_input(shell_editor, None)
        assert _get_current_input(buf, state) == "pwd"
        # Navigate forward past end
        _comint_next_input(shell_editor, None)
        _comint_next_input(shell_editor, None)
        assert _get_current_input(buf, state) == "cat"

    def test_next_cycles_forward(self, shell_editor):
        self._add_history(shell_editor, "ls", "pwd", "echo hi")
        _comint_previous_input(shell_editor, None)
        _comint_previous_input(shell_editor, None)
        _comint_previous_input(shell_editor, None)
        _comint_next_input(shell_editor, None)
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == "pwd"

    def test_next_at_end(self, shell_editor):
        _comint_next_input(shell_editor, None)
        assert "End" in shell_editor.message

    def test_empty_history(self, shell_editor):
        _comint_previous_input(shell_editor, None)
        assert "No history" in shell_editor.message

    def test_finished_shell_ignored(self, shell_editor):
        self._add_history(shell_editor, "ls")
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        state.finished = True
        _comint_previous_input(shell_editor, None)
        assert state.history_index == -1


# ═══════════════════════════════════════════════════════════════════
# Shell completion
# ═══════════════════════════════════════════════════════════════════


class TestShellComplete:
    def test_single_match(self, shell_editor):
        buf = shell_editor.buffer
        buf.insert_string("who")
        _shell_complete(shell_editor, None)
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert _get_current_input(buf, state) == "whoami"

    def test_no_match(self, shell_editor):
        buf = shell_editor.buffer
        buf.insert_string("zzznotacmd")
        _shell_complete(shell_editor, None)
        assert "No completions" in shell_editor.message

    def test_multiple_matches_show_message(self, shell_editor):
        buf = shell_editor.buffer
        # "e" should match "echo", "edit", "env", "exit", "export"
        buf.insert_string("e")
        _shell_complete(shell_editor, None)
        # Should show candidates in message line
        assert shell_editor.message  # non-empty message with candidates

    def test_common_prefix_inserted(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        # "ech" should uniquely match "echo"
        buf.insert_string("ech")
        _shell_complete(shell_editor, None)
        assert _get_current_input(buf, state) == "echo"

    def test_finished_shell_ignored(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        state.finished = True
        buf.insert_string("ls")
        _shell_complete(shell_editor, None)
        # Input unchanged
        assert _get_current_input(buf, state) == "ls"


# ═══════════════════════════════════════════════════════════════════
# execute_shell_command (async)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestExecuteShellCommand:
    async def test_ls_output(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "ls")
        text = buf.text
        # ls output should include known files
        assert "welcome.txt" in text

    async def test_prompt_after_command(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "echo hi")
        text = buf.text
        # Should end with a prompt
        assert text.endswith("$ ")

    async def test_input_start_updated(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "echo hi")
        # input_start should be at end of buffer (after new prompt)
        last_line = buf.line_count - 1
        last_col = len(buf.lines[-1])
        assert state.input_start.line == last_line
        assert state.input_start.col == last_col

    async def test_empty_command(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        old_text = buf.text
        await execute_shell_command(buf, state, "")
        # Should still append a prompt
        assert "$ " in buf.text[len(old_text) :]

    async def test_exit_command(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "exit")
        assert state.finished is True
        assert "Process shell finished" in buf.text

    async def test_error_output(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "cat nonexistent_file_xyz")
        text = buf.text
        # Error message should appear in buffer
        assert "not found" in text.lower() or "no such" in text.lower()

    async def test_not_modified_after_command(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "echo hi")
        assert not buf.modified

    async def test_history_recorded(self, shell_editor):
        buf = shell_editor.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        await execute_shell_command(buf, state, "echo hello")
        assert "echo hello" in state.shell.session.history


# ═══════════════════════════════════════════════════════════════════
# EditorView.on_after_key
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestOnAfterKey:
    async def test_no_pending_returns_none(self, shell_view):
        result = await shell_view.on_after_key()
        assert result is None

    async def test_pending_command_executes(self, shell_view):
        ed = shell_view.editor
        buf = ed.buffer
        assert buf.name == "*shell*"

        # Type a command and press Enter
        for ch in "echo hello":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")

        assert len(ed._after_key_queue) > 0

        # Process the pending command
        result = await shell_view.on_after_key()
        assert result is not None  # Got a ScreenBuffer back
        assert len(ed._after_key_queue) == 0  # Drained

        # Output should be in the buffer
        assert "hello" in buf.text

    async def test_buffer_has_new_prompt(self, shell_view):
        ed = shell_view.editor
        buf = ed.buffer

        for ch in "echo test":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        # Buffer should end with a prompt
        assert buf.text.endswith("$ ")


# ═══════════════════════════════════════════════════════════════════
# M-x shell command
# ═══════════════════════════════════════════════════════════════════


class TestShellCommand:
    def test_mx_shell_creates_buffer(self, editor, shell):
        editor.shell_factory = lambda: shell
        editor.create_buffer()  # start with *scratch*
        editor.execute_command("shell")
        assert editor.buffer.name == "*shell*"

    def test_mx_shell_switches_to_existing(self, editor, shell):
        editor.shell_factory = lambda: shell
        editor.create_buffer()
        editor.execute_command("shell")
        # Create another buffer, then switch back
        editor.create_buffer(name="other")
        editor.execute_command("shell")
        assert editor.buffer.name == "*shell*"

    def test_mx_shell_no_factory(self, editor):
        editor.create_buffer()
        editor.execute_command("shell")
        assert "not available" in editor.message

    def test_modeline_shows_shell(self, editor, shell):
        editor.shell_factory = lambda: shell
        editor.create_buffer()
        editor.execute_command("shell")
        assert editor.buffer.major_mode is not None
        assert editor.buffer.major_mode.name == "shell-mode"


# ═══════════════════════════════════════════════════════════════════
# Integration: full command cycle
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestIntegration:
    async def test_full_command_cycle(self, shell_view):
        """Type a command, press Enter, verify output, type another."""
        ed = shell_view.editor
        buf = ed.buffer

        # Execute "echo hello"
        for ch in "echo hello":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        assert "hello" in buf.text

        # Execute "pwd"
        for ch in "pwd":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        assert "/" in buf.text

    async def test_history_across_commands(self, shell_view):
        """Execute commands, then navigate history."""
        ed = shell_view.editor
        buf = ed.buffer
        state: ShellState = buf._shell_state  # type: ignore[attr-defined]

        # Execute two commands
        for ch in "echo first":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        for ch in "echo second":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        # Navigate history with M-p
        shell_view.on_key("M-p")
        assert _get_current_input(buf, state) == "echo second"

        shell_view.on_key("M-p")
        assert _get_current_input(buf, state) == "echo first"

    async def test_multiple_windows(self, shell_view):
        """Shell buffer visible in split window works."""
        ed = shell_view.editor

        # Split window
        shell_view.on_key("C-x")
        shell_view.on_key("2")

        # Type command in active window
        for ch in "echo split":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        assert "split" in ed.buffer.text

    async def test_exit_then_enter(self, shell_view):
        """After exit, Enter does nothing."""
        ed = shell_view.editor
        buf = ed.buffer

        for ch in "exit":
            shell_view.on_key(ch)
        shell_view.on_key("Enter")
        await shell_view.on_after_key()

        state: ShellState = buf._shell_state  # type: ignore[attr-defined]
        assert state.finished

        shell_view.on_key("Enter")
        # No pending async after pressing Enter on finished shell
        result = await shell_view.on_after_key()
        assert result is None
