"""
Default editor commands and keybindings.

Registers the standard Emacs-like commands and builds the default
global keymap.  Import this module to populate the command table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor


# ═══════════════════════════════════════════════════════════════════════
# Movement
# ═══════════════════════════════════════════════════════════════════════


@defcommand("forward-char", "Move point forward one character.")
def forward_char(ed: Editor, prefix: int | None) -> None:
    ed.buffer.forward_char(prefix if prefix is not None else 1)


@defcommand("backward-char", "Move point backward one character.")
def backward_char(ed: Editor, prefix: int | None) -> None:
    ed.buffer.backward_char(prefix if prefix is not None else 1)


@defcommand("next-line", "Move point to the next line.")
def next_line(ed: Editor, prefix: int | None) -> None:
    ed.buffer.forward_line(prefix if prefix is not None else 1)


@defcommand("previous-line", "Move point to the previous line.")
def previous_line(ed: Editor, prefix: int | None) -> None:
    ed.buffer.backward_line(prefix if prefix is not None else 1)


@defcommand("beginning-of-line", "Move point to the beginning of the line.")
def beginning_of_line(ed: Editor, prefix: int | None) -> None:
    ed.buffer.beginning_of_line()


@defcommand("end-of-line", "Move point to the end of the line.")
def end_of_line(ed: Editor, prefix: int | None) -> None:
    ed.buffer.end_of_line()


@defcommand("beginning-of-buffer", "Move point to the beginning of the buffer.")
def beginning_of_buffer(ed: Editor, prefix: int | None) -> None:
    ed.buffer.beginning_of_buffer()


@defcommand("end-of-buffer", "Move point to the end of the buffer.")
def end_of_buffer(ed: Editor, prefix: int | None) -> None:
    ed.buffer.end_of_buffer()


# ═══════════════════════════════════════════════════════════════════════
# Editing
# ═══════════════════════════════════════════════════════════════════════


@defcommand("self-insert-command", "Insert the character that invoked this command.")
def self_insert_command(ed: Editor, prefix: int | None) -> None:
    key = getattr(ed, "_current_key", None)
    if key is None:
        return
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.insert_char(key)


@defcommand("newline", "Insert a newline.")
def newline(ed: Editor, prefix: int | None) -> None:
    ed.buffer.insert_char("\n")


@defcommand("delete-char", "Delete the character after point.")
def delete_char(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.delete_char_forward()


@defcommand("delete-backward-char", "Delete the character before point.")
def delete_backward_char(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.delete_char_backward()


# ═══════════════════════════════════════════════════════════════════════
# Kill / Yank
# ═══════════════════════════════════════════════════════════════════════


@defcommand("kill-line", "Kill from point to end of line.")
def kill_line(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_line()


@defcommand("kill-region", "Kill the region (text between point and mark).")
def kill_region(ed: Editor, prefix: int | None) -> None:
    ed.buffer.kill_region()


@defcommand("kill-word", "Kill from point to the end of the current word.")
def kill_word(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_word_forward()


@defcommand("yank", "Yank (paste) the most recent kill.")
def yank(ed: Editor, prefix: int | None) -> None:
    ed.buffer.yank()


@defcommand("yank-pop", "Replace just-yanked text with the next kill ring entry.")
def yank_pop(ed: Editor, prefix: int | None) -> None:
    ed.buffer.yank_pop()


# ═══════════════════════════════════════════════════════════════════════
# Undo
# ═══════════════════════════════════════════════════════════════════════


@defcommand("undo", "Undo the last editing operation.")
def undo(ed: Editor, prefix: int | None) -> None:
    if not ed.buffer.undo():
        ed.message = "No further undo information"


# ═══════════════════════════════════════════════════════════════════════
# Mark / Region
# ═══════════════════════════════════════════════════════════════════════


@defcommand("set-mark-command", "Set the mark at point.")
def set_mark_command(ed: Editor, prefix: int | None) -> None:
    ed.buffer.set_mark()
    ed.message = "Mark set"


# ═══════════════════════════════════════════════════════════════════════
# Editor control
# ═══════════════════════════════════════════════════════════════════════


@defcommand("keyboard-quit", "Cancel the current operation.")
def keyboard_quit(ed: Editor, prefix: int | None) -> None:
    ed.buffer.clear_mark()
    ed._pending_keymap = None
    ed._prefix_arg = None
    ed.message = "Quit"


@defcommand("save-buffer", "Save the current buffer to its file.")
def save_buffer(ed: Editor, prefix: int | None) -> None:
    if ed.save_callback is None:
        ed.message = "No save handler configured"
        return
    if ed.save_callback(ed.buffer):
        ed.buffer.modified = False
        ed.message = "Wrote " + (ed.buffer.filepath or ed.buffer.name)
    else:
        ed.message = "Save failed"


@defcommand("quit-editor", "Exit the editor.")
def quit_editor(ed: Editor, prefix: int | None) -> None:
    ed.quit()


# ═══════════════════════════════════════════════════════════════════════
# Default keymap
# ═══════════════════════════════════════════════════════════════════════


def build_default_keymap() -> Keymap:
    """Build and return the default global keymap with Emacs bindings."""
    km = Keymap("global")

    # Movement
    km.bind("C-f", "forward-char")
    km.bind("C-b", "backward-char")
    km.bind("C-n", "next-line")
    km.bind("C-p", "previous-line")
    km.bind("C-a", "beginning-of-line")
    km.bind("C-e", "end-of-line")
    km.bind("M-<", "beginning-of-buffer")
    km.bind("M->", "end-of-buffer")

    # Arrow keys
    km.bind("ArrowRight", "forward-char")
    km.bind("ArrowLeft", "backward-char")
    km.bind("ArrowDown", "next-line")
    km.bind("ArrowUp", "previous-line")

    # Editing
    km.bind("Enter", "newline")
    km.bind("C-d", "delete-char")
    km.bind("Backspace", "delete-backward-char")

    # Kill / Yank
    km.bind("C-k", "kill-line")
    km.bind("C-w", "kill-region")
    km.bind("M-d", "kill-word")
    km.bind("C-y", "yank")
    km.bind("M-y", "yank-pop")

    # Undo
    km.bind("C-/", "undo")
    km.bind("C-_", "undo")  # alternative

    # Mark
    km.bind("C-space", "set-mark-command")

    # Cancel
    km.bind("C-g", "keyboard-quit")

    # C-x prefix map
    cx = Keymap("C-x prefix")
    cx.bind("C-s", "save-buffer")
    cx.bind("C-c", "quit-editor")
    km.bind("C-x", cx)

    return km
