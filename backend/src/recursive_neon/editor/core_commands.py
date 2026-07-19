"""Capability-free command allowlist for deterministic core editor sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.editor.commands import Command
from recursive_neon.editor.editing_primitives import auto_fill_break
from recursive_neon.editor.keymap import Keymap

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor


def _char_position(ed: Editor, line: int, column: int) -> int:
    return sum(len(text) + 1 for text in ed.buffer.lines[:line]) + column


def _char_move(ed: Editor, count: int) -> None:
    before = _char_position(ed, ed.buffer.point.line, ed.buffer.point.col)
    ed.buffer.forward_char(count)
    after = _char_position(ed, ed.buffer.point.line, ed.buffer.point.col)
    if abs(after - before) < abs(count):
        ed.message = "End of buffer" if count > 0 else "Beginning of buffer"


def _line_move(ed: Editor, count: int) -> None:
    before_line = ed.buffer.point.line
    ed.buffer.forward_line(count)
    if ed.buffer.point.line - before_line == count:
        return
    if count > 0:
        last = ed.buffer.line_count - 1
        ed.buffer.point.line = last
        ed.buffer.point.col = len(ed.buffer.lines[last])
        ed.message = "End of buffer"
    else:
        ed.buffer.point.line = 0
        ed.buffer.point.col = 0
        ed.message = "Beginning of buffer"


def _forward_char(ed: Editor, prefix: int | None) -> None:
    _char_move(ed, prefix if prefix is not None else 1)


def _backward_char(ed: Editor, prefix: int | None) -> None:
    _char_move(ed, -(prefix if prefix is not None else 1))


def _next_line(ed: Editor, prefix: int | None) -> None:
    _line_move(ed, prefix if prefix is not None else 1)


def _previous_line(ed: Editor, prefix: int | None) -> None:
    _line_move(ed, -(prefix if prefix is not None else 1))


def _beginning_of_line(ed: Editor, prefix: int | None) -> None:
    del prefix
    ed.buffer.beginning_of_line()


def _end_of_line(ed: Editor, prefix: int | None) -> None:
    del prefix
    ed.buffer.end_of_line()


def _push_mark_for_big_motion(ed: Editor, prefix: int | None) -> None:
    if prefix is None and not ed.buffer.region_active:
        ed.buffer.push_mark()
        ed.message = "Mark set"


def _beginning_of_buffer(ed: Editor, prefix: int | None) -> None:
    _push_mark_for_big_motion(ed, prefix)
    ed.buffer.beginning_of_buffer()


def _end_of_buffer(ed: Editor, prefix: int | None) -> None:
    _push_mark_for_big_motion(ed, prefix)
    ed.buffer.end_of_buffer()


def _self_insert(ed: Editor, prefix: int | None) -> None:
    key = ed._current_key
    if key is None:
        return
    for _ in range(prefix if prefix is not None else 1):
        ed.buffer.insert_char(key)
    if key == " " and ed.get_variable("auto-fill"):
        fill_column = ed.get_variable("fill-column") or 70
        if ed.buffer.point.col > fill_column:
            auto_fill_break(ed.buffer, fill_column)


def _newline(ed: Editor, prefix: int | None) -> None:
    del prefix
    ed.buffer.insert_char("\n")


def _delete_char(ed: Editor, prefix: int | None) -> None:
    for _ in range(prefix if prefix is not None else 1):
        ed.buffer.delete_char_forward()


def _delete_backward_char(ed: Editor, prefix: int | None) -> None:
    for _ in range(prefix if prefix is not None else 1):
        ed.buffer.delete_char_backward()


def _undo(ed: Editor, prefix: int | None) -> None:
    del prefix
    if ed.buffer.undo():
        ed.message = "Redo" if ed.buffer.last_undo_was_redo else "Undo"
    else:
        ed.message = "No further undo information"


def _keyboard_quit(ed: Editor, prefix: int | None) -> None:
    del prefix
    ed._reset_transient_state()
    ed.message = "Quit"


def _quit_editor(ed: Editor, prefix: int | None) -> None:
    del prefix
    ed.quit()


_CORE_COMMAND_TEMPLATES = (
    Command("backward-char", _backward_char, "Move point backward one character."),
    Command(
        "beginning-of-buffer",
        _beginning_of_buffer,
        "Move point to the beginning of the buffer.",
    ),
    Command(
        "beginning-of-line",
        _beginning_of_line,
        "Move point to the beginning of the line.",
    ),
    Command(
        "delete-backward-char",
        _delete_backward_char,
        "Delete the character before point.",
        coalesce_key="delete-backward",
    ),
    Command(
        "delete-char",
        _delete_char,
        "Delete the character after point.",
        coalesce_key="delete-forward",
    ),
    Command(
        "end-of-buffer",
        _end_of_buffer,
        "Move point to the end of the buffer.",
    ),
    Command("end-of-line", _end_of_line, "Move point to the end of the line."),
    Command("forward-char", _forward_char, "Move point forward one character."),
    Command("keyboard-quit", _keyboard_quit, "Cancel the current operation."),
    Command("newline", _newline, "Insert a newline."),
    Command("next-line", _next_line, "Move point to the next line."),
    Command("previous-line", _previous_line, "Move point to the previous line."),
    Command("quit-editor", _quit_editor, "Exit the editor."),
    Command(
        "self-insert-command",
        _self_insert,
        "Insert the character that invoked this command.",
        coalesce_key="insert",
    ),
    Command("undo", _undo, "Undo the last editing operation."),
)


def build_core_commands() -> dict[str, Command]:
    """Return fresh command metadata for the deterministic core profile."""
    return {
        template.name: Command(
            name=template.name,
            function=template.function,
            doc=template.doc,
            coalesce_key=template.coalesce_key,
        )
        for template in _CORE_COMMAND_TEMPLATES
    }


def build_core_keymap() -> Keymap:
    """Return a fresh keymap containing only synchronous core commands."""
    keymap = Keymap("core")
    for key, command in (
        ("C-f", "forward-char"),
        ("C-b", "backward-char"),
        ("C-n", "next-line"),
        ("C-p", "previous-line"),
        ("C-a", "beginning-of-line"),
        ("C-e", "end-of-line"),
        ("M-<", "beginning-of-buffer"),
        ("M->", "end-of-buffer"),
        ("ArrowRight", "forward-char"),
        ("ArrowLeft", "backward-char"),
        ("ArrowDown", "next-line"),
        ("ArrowUp", "previous-line"),
        ("Home", "beginning-of-line"),
        ("End", "end-of-line"),
        ("Enter", "newline"),
        ("C-d", "delete-char"),
        ("Delete", "delete-char"),
        ("Backspace", "delete-backward-char"),
        ("C-/", "undo"),
        ("C-_", "undo"),
        ("C-g", "keyboard-quit"),
    ):
        keymap.bind(key, command)

    control_x = Keymap("C-x prefix")
    control_x.bind("C-c", "quit-editor")
    control_x.bind("u", "undo")
    keymap.bind("C-x", control_x)
    return keymap
