"""
Shell-in-editor — run the game shell inside an editor buffer.

Implements an Emacs comint-style shell mode: the user types commands
at a prompt in an editor buffer, presses Enter, and sees command
output appear.  The shell is an in-process Python object (no subprocess).

Architecture:
- ``BufferOutput`` captures shell output as ANSI-stripped plain text.
- ``ShellState`` tracks per-buffer shell state (input mark, history).
- ``setup_shell_buffer()`` initialises a buffer for shell interaction.
- Enter triggers ``_comint_send_input`` which stores a pending async
  callback on ``editor._pending_async``.  The TUI runner's
  ``on_after_key()`` awaits it, then re-renders.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.modes import defmode
from recursive_neon.shell.output import Output

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor
    from recursive_neon.shell.shell import Shell

# ------------------------------------------------------------------
# ANSI stripping
# ------------------------------------------------------------------

_ANSI_RE = re.compile(r"\033\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


# ------------------------------------------------------------------
# BufferOutput — captures shell output for buffer insertion
# ------------------------------------------------------------------


class BufferOutput(Output):
    """Shell output that captures text for later insertion into a buffer.

    ANSI escape codes are stripped at write time because the editor
    buffer stores plain text only.
    """

    def __init__(self) -> None:
        self._chunks: list[str] = []
        dummy = io.StringIO()
        super().__init__(stream=dummy, err_stream=dummy, color=True)

    def write(self, text: str) -> None:
        self._chunks.append(strip_ansi(text))

    def writeln(self, text: str = "") -> None:
        self._chunks.append(strip_ansi(text) + "\n")

    def error(self, text: str) -> None:
        self._chunks.append(strip_ansi(text) + "\n")

    def drain(self) -> str:
        """Return all captured text and clear the internal buffer."""
        result = "".join(self._chunks)
        self._chunks.clear()
        return result


# ------------------------------------------------------------------
# ShellBufferInput — stub InputSource for ctx.get_line
# ------------------------------------------------------------------


class ShellBufferInput:
    """Minimal ``InputSource`` stub for shell-in-editor.

    Interactive sub-prompts (``ctx.get_line``) are not supported in
    this phase; programs that call it will receive ``EOFError``.
    """

    async def get_line(
        self,
        prompt: str,
        *,
        complete: bool = True,
        history_id: str | None = None,
    ) -> str:
        raise EOFError("Interactive input not available in editor shell")


# ------------------------------------------------------------------
# ShellState — per-buffer shell state
# ------------------------------------------------------------------


@dataclass
class ShellState:
    """State attached to a ``*shell*`` buffer."""

    shell: Any  # Shell instance (typed as Any to avoid hard import)
    input_start: Mark  # Start of user input (just after prompt)
    output: BufferOutput  # Shared output capture
    history_index: int = -1  # -1 = not navigating
    saved_input: str = ""  # Partial input saved during history nav
    finished: bool = False  # True after ``exit`` command


# ------------------------------------------------------------------
# Mode registration
# ------------------------------------------------------------------

defmode(
    "shell-mode",
    is_major=True,
    doc="Major mode for interacting with the neon shell inside an editor buffer.",
)


# ------------------------------------------------------------------
# Buffer setup
# ------------------------------------------------------------------


def setup_shell_buffer(editor: Editor, buf: Buffer, shell: Shell) -> None:
    """Initialise *buf* for shell interaction.

    Sets the major mode, creates the shell-mode keymap, inserts the
    welcome banner and first prompt, and attaches a ``ShellState``.
    """
    # Configure shell for buffer-based I/O
    output = BufferOutput()
    shell.output = output
    shell._input_source = ShellBufferInput()

    # Create input_start mark — kind="left" so it stays put when the
    # user types text at its position.
    input_start = Mark(0, 0, kind="left")
    buf.track_mark(input_start)

    # Attach state
    state = ShellState(shell=shell, input_start=input_start, output=output)
    buf._shell_state = state  # type: ignore[attr-defined]

    # Set major mode
    editor.set_major_mode("shell-mode")

    # Build buffer-local keymap (parent = global so unbound keys fall through)
    km = Keymap("shell-mode-map", parent=editor.global_keymap)
    km.bind("Enter", _comint_send_input)
    km.bind("M-p", _comint_previous_input)
    km.bind("M-n", _comint_next_input)
    km.bind("Tab", _shell_complete)
    buf.keymap = km

    # Insert welcome banner + initial prompt (no undo recorded)
    from recursive_neon.shell.shell import WELCOME_BANNER

    banner = strip_ansi(WELCOME_BANNER)
    prompt = strip_ansi(shell._build_prompt())
    initial_text = banner + prompt

    buf._undo_recording = False
    buf.insert_string(initial_text)
    buf._undo_recording = True

    # input_start should be at point (end of prompt) — since the mark
    # is "left" kind, it stayed at (0, 0) during insertion.  Move it
    # explicitly to the current point.
    input_start.move_to(buf.point.line, buf.point.col)

    buf.modified = False


# ------------------------------------------------------------------
# Input helpers
# ------------------------------------------------------------------


def _get_current_input(buf: Buffer, state: ShellState) -> str:
    """Return text from ``input_start`` to end of buffer."""
    start = state.input_start
    if start.line >= buf.line_count:
        return ""
    end = Mark(buf.line_count - 1, len(buf.lines[-1]))
    return buf.get_text(start, end)


def _get_input_up_to_point(buf: Buffer, state: ShellState) -> str:
    """Return text from ``input_start`` to point (for completion)."""
    start = state.input_start
    if start.line >= buf.line_count:
        return ""
    if buf.point <= start:
        return ""
    return buf.get_text(start, buf.point)


def _replace_input(buf: Buffer, state: ShellState, new_text: str) -> None:
    """Replace current input (``input_start`` to EOB) with *new_text*."""
    start = state.input_start
    end_line = buf.line_count - 1
    end_col = len(buf.lines[end_line])

    # Move point to input start
    buf.point.move_to(start.line, start.col)

    # Delete existing input if any
    if (start.line, start.col) < (end_line, end_col):
        end = Mark(end_line, end_col)
        buf.delete_region(start, end)

    # Insert replacement text
    if new_text:
        buf.insert_string(new_text)


# ------------------------------------------------------------------
# Shell-mode commands (bound as callables in the keymap)
# ------------------------------------------------------------------


def _comint_send_input(editor: Any, prefix: Any) -> None:
    """Send the current input line to the shell (Enter in shell mode)."""
    buf = editor.buffer
    state: ShellState | None = getattr(buf, "_shell_state", None)
    if state is None or state.finished:
        # If finished, just insert a newline
        if state is not None and state.finished:
            editor.message = "[Process shell finished]"
        return

    # Extract input text
    input_text = _get_current_input(buf, state)

    # Move point to end of buffer and insert newline
    buf.end_of_buffer()
    buf.insert_char("\n")

    # Reset history navigation
    state.history_index = -1
    state.saved_input = ""

    # Store async callback for the TUI runner
    async def _execute() -> None:
        await execute_shell_command(buf, state, input_text)

    editor._pending_async = _execute


def _comint_previous_input(editor: Any, prefix: Any) -> None:
    """Navigate to previous shell history entry (M-p)."""
    buf = editor.buffer
    state: ShellState | None = getattr(buf, "_shell_state", None)
    if state is None or state.finished:
        return

    history: list[str] = state.shell.session.history
    if not history:
        editor.message = "[No history]"
        return

    if state.history_index == -1:
        # First press — save current input, start at the end
        state.saved_input = _get_current_input(buf, state)
        state.history_index = len(history)

    if state.history_index > 0:
        state.history_index -= 1
        _replace_input(buf, state, history[state.history_index])
    else:
        editor.message = "[Beginning of history]"


def _comint_next_input(editor: Any, prefix: Any) -> None:
    """Navigate to next shell history entry (M-n)."""
    buf = editor.buffer
    state: ShellState | None = getattr(buf, "_shell_state", None)
    if state is None or state.finished:
        return

    if state.history_index == -1:
        editor.message = "[End of history]"
        return

    history: list[str] = state.shell.session.history
    state.history_index += 1

    if state.history_index >= len(history):
        # Past the end — restore saved input
        state.history_index = -1
        _replace_input(buf, state, state.saved_input)
    else:
        _replace_input(buf, state, history[state.history_index])


def _shell_complete(editor: Any, prefix: Any) -> None:
    """Tab completion in the shell buffer."""
    buf = editor.buffer
    state: ShellState | None = getattr(buf, "_shell_state", None)
    if state is None or state.finished:
        return

    input_text = _get_input_up_to_point(buf, state)
    items, replace_len = state.shell.get_completions_ext(input_text)

    if not items:
        editor.message = "[No completions]"
        return

    if len(items) == 1:
        # Single match — insert it
        for _ in range(replace_len):
            buf.delete_char_backward()
        buf.insert_string(items[0])
    else:
        # Multiple matches — complete common prefix
        common = os.path.commonprefix(items)
        if len(common) > replace_len:
            for _ in range(replace_len):
                buf.delete_char_backward()
            buf.insert_string(common)
        # Show candidates in message line
        display = "  ".join(items[:20])
        if len(items) > 20:
            display += f"  ... ({len(items)} total)"
        editor.message = display


# ------------------------------------------------------------------
# Async command execution (called from on_after_key)
# ------------------------------------------------------------------


async def execute_shell_command(buf: Buffer, state: ShellState, command: str) -> None:
    """Execute a shell command and append output + new prompt to *buf*.

    Called by ``EditorView.on_after_key()`` after the user presses Enter.
    """
    shell = state.shell

    # Ensure output goes to our BufferOutput
    shell.output = state.output

    # Execute command (skip empty lines)
    stripped = command.strip()
    if stripped:
        shell.session.history.append(stripped)
        exit_code = await shell.execute_line(stripped)
    else:
        exit_code = 0

    # Collect captured output
    text = state.output.drain()

    # Append output to buffer (no undo recording)
    buf._undo_recording = False
    try:
        buf.end_of_buffer()
        if text:
            buf.insert_string(text)

        if exit_code == -1:
            # Shell exited
            buf.insert_string("[Process shell finished]\n")
            state.finished = True
        else:
            shell.session.last_exit_code = exit_code
            # Append new prompt
            prompt = strip_ansi(shell._build_prompt())
            buf.insert_string(prompt)
            # Update input_start to current point (end of prompt)
            state.input_start.move_to(buf.point.line, buf.point.col)
    finally:
        buf._undo_recording = True
        buf.modified = False


# ------------------------------------------------------------------
# M-x shell command (registered via @defcommand)
# ------------------------------------------------------------------


@defcommand("shell", "Run the game shell in an editor buffer (M-x shell).")
def cmd_shell(ed: Editor, prefix: int | None) -> None:
    """Create or switch to a ``*shell*`` buffer."""
    # Reuse existing *shell* buffer
    if ed.switch_to_buffer("*shell*"):
        return

    # Need a shell factory (set by the edit shell program)
    factory = getattr(ed, "shell_factory", None)
    if factory is None:
        ed.message = "Shell not available in this context"
        return

    # Create and configure the shell
    shell = factory()
    buf = ed.create_buffer(name="*shell*")
    setup_shell_buffer(ed, buf, shell)
    ed.message = ""
