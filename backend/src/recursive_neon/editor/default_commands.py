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


@defcommand("forward-word", "Move point forward one word.")
def forward_word(ed: Editor, prefix: int | None) -> None:
    ed.buffer.forward_word(prefix if prefix is not None else 1)


@defcommand("backward-word", "Move point backward one word.")
def backward_word(ed: Editor, prefix: int | None) -> None:
    ed.buffer.backward_word(prefix if prefix is not None else 1)


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


@defcommand("kill-backward-word", "Kill backward to the start of the current word.")
def kill_backward_word(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_word_backward()


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


# ═══════════════════════════════════════════════════════════════════════
# Minibuffer commands (M-x, file ops, buffer switching)
# ═══════════════════════════════════════════════════════════════════════


@defcommand("execute-extended-command", "Execute a command by name (M-x).")
def execute_extended_command(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.commands import COMMANDS

    def completer(text: str) -> list[str]:
        return sorted(n for n in COMMANDS if n.startswith(text))

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            return
        if not ed.execute_command(name, prefix):
            ed.message = f"Unknown command: {name}"

    ed.start_minibuffer("M-x ", callback, completer=completer)


@defcommand("switch-to-buffer", "Switch to a different buffer (C-x b).")
def switch_to_buffer(ed: Editor, prefix: int | None) -> None:
    def completer(text: str) -> list[str]:
        return [b.name for b in ed.buffers if b.name.startswith(text)]

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            return
        if not ed.switch_to_buffer(name):
            # Create a new empty buffer with that name
            ed.create_buffer(name=name)
            ed.message = f"(New buffer {name})"

    ed.start_minibuffer("Switch to buffer: ", callback, completer=completer)


@defcommand("list-buffers", "Show a list of all buffers (C-x C-b).")
def list_buffers(ed: Editor, prefix: int | None) -> None:
    lines = ["  Buffer               Size  File"]
    lines.append("  ------               ----  ----")
    for buf in ed.buffers:
        mod = "*" if buf.modified else " "
        ro = "%" if buf.read_only else " "
        size = sum(len(ln) for ln in buf.lines) + buf.line_count - 1
        path = buf.filepath or ""
        lines.append(f"{mod}{ro} {buf.name:<20s} {size:>5d}  {path}")
    text = "\n".join(lines)

    # Show in a read-only buffer
    if not ed.switch_to_buffer("*Buffer List*"):
        ed.create_buffer(name="*Buffer List*")
    bl = ed.buffer
    # Replace content (temporarily disable read-only)
    bl.read_only = False
    bl.lines = text.split("\n")
    bl.point.move_to(0, 0)
    bl.modified = False
    bl.read_only = True


@defcommand("kill-buffer", "Kill (close) a buffer (C-x k).")
def kill_buffer(ed: Editor, prefix: int | None) -> None:
    current_name = ed.buffer.name

    def completer(text: str) -> list[str]:
        return [b.name for b in ed.buffers if b.name.startswith(text)]

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            return
        ed.remove_buffer(name)

    ed.start_minibuffer(
        "Kill buffer: ", callback, completer=completer, initial=current_name
    )


@defcommand("write-file", "Write buffer to a file path (C-x C-w).")
def write_file(ed: Editor, prefix: int | None) -> None:
    def callback(path: str) -> None:
        path = path.strip()
        if not path:
            return
        ed.buffer.filepath = path
        ed.buffer.name = path.rsplit("/", 1)[-1] if "/" in path else path
        # Attempt save via the save callback
        if ed.save_callback is not None:
            if ed.save_callback(ed.buffer):
                ed.buffer.modified = False
                ed.message = f"Wrote {path}"
            else:
                ed.message = "Save failed"
        else:
            ed.message = f"File path set to {path} (no save handler)"

    initial = ed.buffer.filepath or ""
    ed.start_minibuffer(
        "Write file: ", callback, initial=initial, completer=ed.path_completer
    )


@defcommand("find-file", "Open or create a file (C-x C-f).")
def find_file(ed: Editor, prefix: int | None) -> None:
    def callback(path: str) -> None:
        path = path.strip()
        if not path:
            return
        # Check if already open
        for buf in ed.buffers:
            if buf.filepath == path:
                ed.switch_to_buffer(buf.name)
                ed.message = f"Switched to {buf.name}"
                return
        # Try to load via the open_callback
        content = ""
        if ed.open_callback is not None:
            content = ed.open_callback(path)

        name = path.rsplit("/", 1)[-1] if "/" in path else path
        ed.create_buffer(name=name, text=content, filepath=path)
        ed.message = f"Opened {path}" if content else f"(New file) {path}"

    ed.start_minibuffer("Find file: ", callback, completer=ed.path_completer)


# ═══════════════════════════════════════════════════════════════════════
# Incremental search
# ═══════════════════════════════════════════════════════════════════════


@defcommand("isearch-forward", "Incremental search forward (C-s).")
def isearch_forward(ed: Editor, prefix: int | None) -> None:
    _start_isearch(ed, forward=True)


@defcommand("isearch-backward", "Incremental search backward (C-r).")
def isearch_backward(ed: Editor, prefix: int | None) -> None:
    _start_isearch(ed, forward=False)


def _start_isearch(ed: Editor, *, forward: bool) -> None:
    """Set up an incremental search session via the minibuffer."""
    buf = ed.buffer
    start_line = buf.point.line
    start_col = buf.point.col
    # Stack of (line, col) positions for backspace-undo
    positions: list[tuple[int, int]] = [(start_line, start_col)]
    direction = [forward]  # mutable so closures can update

    def on_change(text: str) -> None:
        if not text:
            buf.point.move_to(start_line, start_col)
            ed.message = ""
            return
        _do_search(text, from_current=False)

    def _do_search(text: str, *, from_current: bool) -> None:
        if direction[0]:
            # Search forward: skip past current match when repeating
            from_col = buf.point.col + (1 if from_current else 0)
            pos = buf.find_forward(text, buf.point.line, from_col)
        else:
            # Search backward: include current col for fresh search,
            # exclude it when repeating (to find the previous match)
            from_col = buf.point.col if from_current else buf.point.col + 1
            pos = buf.find_backward(text, buf.point.line, from_col)
        if pos is not None:
            positions.append(pos)
            buf.point.move_to(pos[0], pos[1])
            prefix = "I-search" if direction[0] else "I-search backward"
            ed.message = ""
            if ed.minibuffer:
                ed.minibuffer.prompt = f"{prefix}: "
        else:
            prefix = "Failing I-search" if direction[0] else "Failing I-search backward"
            if ed.minibuffer:
                ed.minibuffer.prompt = f"{prefix}: "

    def on_confirm(text: str) -> None:
        pass  # Leave point at the match

    def on_cancel() -> None:
        buf.point.move_to(start_line, start_col)

    def repeat_forward() -> None:
        direction[0] = True
        if ed.minibuffer and ed.minibuffer.text:
            _do_search(ed.minibuffer.text, from_current=True)

    def repeat_backward() -> None:
        direction[0] = False
        if ed.minibuffer and ed.minibuffer.text:
            _do_search(ed.minibuffer.text, from_current=True)

    prompt_prefix = "I-search" if forward else "I-search backward"

    # Use a wrapper for on_cancel since Minibuffer callback takes no args
    def cancel_wrapper(text: str) -> None:
        pass  # Not used — cancel is handled separately

    ed.start_minibuffer(
        f"{prompt_prefix}: ",
        on_confirm,
        on_change=on_change,
    )
    if ed.minibuffer:
        ed.minibuffer.key_handlers["C-s"] = repeat_forward
        ed.minibuffer.key_handlers["C-r"] = repeat_backward
        # Override C-g to restore position
        original_process = ed.minibuffer.process_key

        def patched_process(key: str) -> bool:
            if key == "C-g" or key == "Escape":
                on_cancel()
                ed.minibuffer._cancelled = True  # type: ignore[union-attr]
                return False
            return original_process(key)

        ed.minibuffer.process_key = patched_process  # type: ignore[method-assign]


# ═══════════════════════════════════════════════════════════════════════
# Help
# ═══════════════════════════════════════════════════════════════════════


@defcommand("describe-key", "Show what command a key is bound to (C-h k).")
def describe_key(ed: Editor, prefix: int | None) -> None:
    """Enter a key-reading mode: the next keystroke is described."""
    ed.message = "Describe key: "
    # We need to intercept the NEXT keystroke. Use the minibuffer with
    # a single-key handler that captures the first key and describes it.
    ed._describing_key = True


@defcommand("command-apropos", "Search commands by name or doc (C-h a).")
def command_apropos(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.commands import COMMANDS

    def callback(pattern: str) -> None:
        pattern = pattern.strip().lower()
        if not pattern:
            return
        matches = [
            (name, cmd.doc)
            for name, cmd in sorted(COMMANDS.items())
            if pattern in name.lower() or pattern in cmd.doc.lower()
        ]
        if not matches:
            ed.message = f"No commands matching '{pattern}'"
            return
        lines = [f"Commands matching '{pattern}':", ""]
        for name, doc in matches:
            lines.append(f"  {name}")
            if doc:
                lines.append(f"    {doc}")
        text = "\n".join(lines)
        _show_help_buffer(ed, text)

    ed.start_minibuffer("Apropos command: ", callback)


def _show_help_buffer(ed: Editor, text: str) -> None:
    """Show text in a read-only *Help* buffer."""
    if not ed.switch_to_buffer("*Help*"):
        ed.create_buffer(name="*Help*")
    buf = ed.buffer
    buf.read_only = False
    buf.lines = text.split("\n")
    buf.point.move_to(0, 0)
    buf.modified = False
    buf.read_only = True


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

    # Word movement
    km.bind("M-f", "forward-word")
    km.bind("M-b", "backward-word")

    # Arrow keys
    km.bind("ArrowRight", "forward-char")
    km.bind("ArrowLeft", "backward-char")
    km.bind("ArrowDown", "next-line")
    km.bind("ArrowUp", "previous-line")
    km.bind("Home", "beginning-of-line")
    km.bind("End", "end-of-line")

    # Editing
    km.bind("Enter", "newline")
    km.bind("C-d", "delete-char")
    km.bind("Delete", "delete-char")
    km.bind("Backspace", "delete-backward-char")

    # Kill / Yank
    km.bind("C-k", "kill-line")
    km.bind("C-w", "kill-region")
    km.bind("M-d", "kill-word")
    km.bind("M-Backspace", "kill-backward-word")
    km.bind("C-y", "yank")
    km.bind("M-y", "yank-pop")

    # Undo
    km.bind("C-/", "undo")
    km.bind("C-_", "undo")  # alternative

    # Mark
    km.bind("C-space", "set-mark-command")

    # Cancel
    km.bind("C-g", "keyboard-quit")

    # Search
    km.bind("C-s", "isearch-forward")
    km.bind("C-r", "isearch-backward")

    # M-x
    km.bind("M-x", "execute-extended-command")

    # C-h prefix map (help)
    ch = Keymap("C-h prefix")
    ch.bind("k", "describe-key")
    ch.bind("a", "command-apropos")
    km.bind("C-h", ch)

    # C-x prefix map
    cx = Keymap("C-x prefix")
    cx.bind("C-s", "save-buffer")
    cx.bind("C-w", "write-file")
    cx.bind("C-f", "find-file")
    cx.bind("b", "switch-to-buffer")
    cx.bind("k", "kill-buffer")
    cx.bind("C-b", "list-buffers")
    cx.bind("C-c", "quit-editor")
    km.bind("C-x", cx)

    return km
