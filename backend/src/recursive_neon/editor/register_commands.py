"""Registers (C-x r) — split out of ``default_commands`` along the
registers seam; importing this module registers the commands
(``default_commands`` does so).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.editor.commands import defcommand

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor, _RegisterSession
# ═══════════════════════════════════════════════════════════════════════
# Registers (C-x r) — point save/jump and text copy/insert
#
# ``point-to-register`` (C-x r SPC), ``jump-to-register`` (C-x r j),
# ``copy-to-register`` (C-x r s) and ``insert-register`` (C-x r i) each
# read one more key — the register *name* — the same way describe-key
# (C-h k) reads a key. The command installs an ``Editor._register_session``;
# ``Editor.process_key`` consumes the next keystroke as the name and calls
# ``_do_register_action`` to finish.
#
# A register holds either a point location (``tuple[int, int]``) or text
# (``str``). Type mismatches reproduce Emacs's errors: jumping to a text
# register says "Register doesn't contain a buffer position or
# configuration" (curly apostrophe — Emacs's default text-quoting-style),
# inserting an *empty* register says "Register does not contain text",
# and inserting a *point* register inserts the buffer position as a
# number, all verified against Emacs 29 via the parity harness
# (scenario 23).
#
# Deviations from Emacs (documented):
# - We store a static ``(line, col)`` in the current buffer, not an
#   edit-tracking marker into a specific buffer. Point save/jump without
#   intervening edits (the common case) is faithful; a jump after the saved
#   text moved would land at the stale position rather than following it.
# - Number / rectangle / window registers and the register preview popup
#   are not implemented. See docs/PARITY_HARNESS.md.
# ═══════════════════════════════════════════════════════════════════════


@defcommand(
    "point-to-register",
    "Save the current point location in a register (C-x r SPC).",
)
def point_to_register(ed: Editor, prefix: int | None) -> None:
    """Prompt for a register name; the next key is read as that name."""
    from recursive_neon.editor.editor import _RegisterSession

    ed._register_session = _RegisterSession(action="point")
    ed.message = "Point to register: "


@defcommand(
    "jump-to-register",
    "Jump to a point location saved in a register (C-x r j).",
)
def jump_to_register(ed: Editor, prefix: int | None) -> None:
    """Prompt for a register name; the next key is read as that name."""
    from recursive_neon.editor.editor import _RegisterSession

    ed._register_session = _RegisterSession(action="jump")
    ed.message = "Jump to register: "


@defcommand(
    "copy-to-register",
    "Copy the region into a register (C-x r s).",
)
def copy_to_register(ed: Editor, prefix: int | None) -> None:
    """Prompt for a register name; the next key is read as that name."""
    from recursive_neon.editor.editor import _RegisterSession

    ed._register_session = _RegisterSession(action="copy")
    ed.message = "Copy to register: "


@defcommand(
    "insert-register",
    "Insert the contents of a register at point (C-x r i).",
)
def insert_register(ed: Editor, prefix: int | None) -> None:
    """Prompt for a register name; the next key is read as that name."""
    from recursive_neon.editor.editor import _RegisterSession

    ed._register_session = _RegisterSession(action="insert")
    ed.message = "Insert register: "


def _char_position(buf: Buffer, line: int, col: int) -> int:
    """The Emacs buffer position (1-based char offset) of ``(line, col)``.

    Emacs's ``insert-register`` on a point register inserts the marker's
    position as a number; our registers store ``(line, col)``, so the
    offset is reconstructed against the current buffer content.
    """
    return sum(len(buf.lines[i]) + 1 for i in range(line)) + col + 1


def _do_register_action(ed: Editor, key: str, session: _RegisterSession) -> None:
    """Complete a register command once the register name has been read.

    ``key`` is the register name (any single character). ``C-g`` cancels
    the read with ``Quit``, matching Emacs's ``read-key`` quit.
    """
    if key == "C-g":
        ed.message = "Quit"
        return
    name = key
    buf = ed.buffer
    if session.action == "point":
        ed._registers[name] = (buf.point.line, buf.point.col)
        ed.message = ""
    elif session.action == "copy":
        # Emacs reads the register name *before* evaluating the region
        # (interactive-spec order), so the no-region error comes after
        # the prompt — mirror that by checking here, not in the command.
        if buf.mark is None:
            ed.message = "The mark is not set now, so there is no region"
            return
        ed._registers[name] = buf.region_text or ""
        # Like kill-ring-save, the copy deactivates the region (clears
        # the mark in our always-active-mark model) and leaves the echo
        # area empty — Emacs shows no confirmation message.
        buf.clear_mark()
        ed.message = ""
    elif session.action == "insert":
        val = ed._registers.get(name)
        if val is None:
            ed.message = "Register does not contain text"
            return
        # A point register inserts its buffer position as a number
        # (Emacs's register-val-insert on a marker).
        text = str(_char_position(buf, *val)) if isinstance(val, tuple) else val
        # GNU Emacs >=28: called interactively, insert-register leaves
        # point *after* the inserted text and the (inactive) mark before
        # it (push-mark echoes "Mark set").
        buf.push_mark(buf.point.line, buf.point.col)
        buf.insert_string(text)
        ed.message = "Mark set"
    else:  # "jump"
        loc = ed._registers.get(name)
        if loc is None:
            ed.message = f"Register {name} is empty"
            return
        if isinstance(loc, str):
            # Text register: Emacs's error, curly apostrophe included
            # (the default text-quoting-style curves quotes in messages).
            ed.message = "Register doesn’t contain a buffer position or configuration"
            return
        line, col = loc
        # Clamp defensively in case the buffer shrank since the save.
        line = max(0, min(line, buf.line_count - 1))
        col = max(0, min(col, len(buf.lines[line])))
        # GNU Emacs pushes an *inactive* mark at the old point before
        # jumping (so the user can return) and echoes "Mark set".
        buf.push_mark()
        buf.point.move_to(line, col)
        ed.message = "Mark set"
