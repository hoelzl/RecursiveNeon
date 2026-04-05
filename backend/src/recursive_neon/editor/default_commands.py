"""
Default editor commands and keybindings.

Registers the standard Emacs-like commands and builds the default
global keymap.  Import this module to populate the command table.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.mark import Mark

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor
    from recursive_neon.editor.window import Window

_TUTORIAL_PATH = (
    Path(__file__).resolve().parent.parent / "initial_fs" / "Documents" / "TUTORIAL.txt"
)


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


@defcommand("forward-sentence", "Move point forward one sentence.")
def forward_sentence(ed: Editor, prefix: int | None) -> None:
    ed.buffer.forward_sentence(prefix if prefix is not None else 1)


@defcommand("backward-sentence", "Move point backward one sentence.")
def backward_sentence(ed: Editor, prefix: int | None) -> None:
    ed.buffer.backward_sentence(prefix if prefix is not None else 1)


# ═══════════════════════════════════════════════════════════════════════
# Viewport scrolling
# ═══════════════════════════════════════════════════════════════════════


@defcommand("scroll-up", "Scroll forward one screenful.")
def scroll_up(ed: Editor, prefix: int | None) -> None:
    vp = ed.viewport
    if vp is None:
        return
    n = prefix if prefix is not None else vp.text_height
    new_top = min(vp.scroll_top + n, max(0, ed.buffer.line_count - 1))
    vp.scroll_to(new_top)
    ed.buffer.point.move_to(new_top, 0)


@defcommand("scroll-down", "Scroll backward one screenful.")
def scroll_down(ed: Editor, prefix: int | None) -> None:
    vp = ed.viewport
    if vp is None:
        return
    n = prefix if prefix is not None else vp.text_height
    new_top = max(0, vp.scroll_top - n)
    vp.scroll_to(new_top)
    target_line = min(new_top + vp.text_height - 1, ed.buffer.line_count - 1)
    ed.buffer.point.move_to(target_line, 0)


_RECENTER_POSITIONS = ("center", "top", "bottom")


@defcommand(
    "recenter",
    "Center viewport around point; consecutive presses cycle center/top/bottom.",
)
def recenter(ed: Editor, prefix: int | None) -> None:
    vp = ed.viewport
    if vp is None:
        return
    cursor_line = ed.buffer.point.line

    if ed._last_command_name == "recenter":
        ed._recenter_index = (ed._recenter_index + 1) % 3
    else:
        ed._recenter_index = 0

    position = _RECENTER_POSITIONS[ed._recenter_index]
    if position == "center":
        vp.scroll_to(cursor_line - vp.text_height // 2)
    elif position == "top":
        vp.scroll_to(cursor_line)
    elif position == "bottom":
        vp.scroll_to(cursor_line - vp.text_height + 1)


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
    # Auto-fill: break line at fill-column when typing a space
    if key == " " and ed.get_variable("auto-fill"):
        fill_col = ed.get_variable("fill-column") or 70
        buf = ed.buffer
        if buf.point.col > fill_col:
            _auto_fill_break(buf, fill_col)


def _auto_fill_break(buf: Buffer, fill_col: int) -> None:
    """Break the current line at the last space before *fill_col*."""
    line = buf.lines[buf.point.line]
    # Find the last space at or before fill_col
    break_col = line.rfind(" ", 0, fill_col)
    if break_col <= 0:
        return
    # Replace the space with a newline
    saved_line = buf.point.line
    saved_col = buf.point.col
    buf.point.move_to(saved_line, break_col)
    buf.delete_char_forward()  # remove the space
    buf.insert_char("\n")
    # Restore point relative to the break
    if saved_col > break_col:
        buf.point.move_to(saved_line + 1, saved_col - break_col - 1)
    else:
        buf.point.move_to(saved_line, saved_col)


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


@defcommand("kill-sentence", "Kill from point to the end of the sentence.")
def kill_sentence(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_sentence()


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
    """Cancel the current operation (C-g).

    Clears every kind of transient state that an interactive command
    might be mid-flight in: pending prefix keymap, prefix argument,
    describe-key capture mode, and the region/mark.  The minibuffer is
    cancelled separately by ``Minibuffer.process_key`` when it sees C-g,
    which sets the minibuffer's cancelled flag; the editor then displays
    ``"Quit"`` at the top of ``process_key``.
    """
    ed._reset_transient_state()
    ed.message = "Quit"


@defcommand(
    "keyboard-escape-quit",
    "Cancel operation and dismiss temporary windows (ESC ESC ESC).",
)
def keyboard_escape_quit(ed: Editor, prefix: int | None) -> None:
    """Cancel everything *and* dismiss temporary display windows.

    Like ``keyboard-quit`` but additionally:

    - Dismisses the ``*Help*`` buffer if currently displayed (switches
      back to the most recent non-``*Help*`` buffer — the buffer stays
      on the list so the user can return to it later).
    - Cancels the minibuffer, including isearch's position-restoring
      cancel path (via the minibuffer's own ``C-g`` handling).
    - Exits describe-key / describe-key-briefly capture modes.
    - Clears mark/region, prefix-arg, and any pending prefix keymap.

    Bound to ``ESC ESC ESC`` via the ESC-as-Meta state machine in
    ``Editor.process_key``.  Can also be invoked directly via
    ``M-x keyboard-escape-quit``.
    """
    # 1. Cancel the minibuffer, if any.  We delegate to the
    # minibuffer's own C-g handling so isearch-style patched cancels
    # (which restore the pre-search point) still fire.
    if ed.minibuffer is not None:
        old_mb = ed.minibuffer
        old_mb.process_key("C-g")
        # Only clear if the cancel callback didn't start a new minibuffer
        if ed.minibuffer is old_mb:
            ed.minibuffer = None

    # 2. Dismiss the *Help* buffer: if it's current, switch to another
    # buffer.  We intentionally do *not* kill the *Help* buffer — it
    # stays on the list so the user can C-x b back to it if wanted.
    if ed.buffer.name == "*Help*":
        for i, buf in enumerate(ed._buffers):
            if buf.name != "*Help*":
                ed._current_index = i
                if buf.on_focus is not None:
                    buf.on_focus()
                break

    # 3. Clear every other transient interactive state.
    ed._reset_transient_state()
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
    ed._describing_key = True


@defcommand(
    "describe-key-briefly",
    "Show what command a key runs, in the message area (C-h c).",
)
def describe_key_briefly(ed: Editor, prefix: int | None) -> None:
    """Like describe-key but shows in message area, not *Help* buffer."""
    ed.message = "Describe key briefly: "
    ed._describing_key_briefly = True


@defcommand(
    "describe-mode",
    "Show the current mode and key bindings (C-h m).",
)
def describe_mode(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    lines: list[str] = []
    # Major mode
    if buf.major_mode is not None:
        lines.append(f"Major mode: {buf.major_mode.name}")
        if buf.major_mode.doc:
            lines.append(f"  {buf.major_mode.doc}")
    else:
        lines.append("Major mode: (none)")
    # Minor modes
    if buf.minor_modes:
        lines.append("")
        lines.append("Minor modes:")
        for m in buf.minor_modes:
            doc = f" — {m.doc}" if m.doc else ""
            lines.append(f"  {m.name}{doc}")
    lines.append("")
    keymap = ed._resolve_keymap()
    lines.append(f"Key bindings in {keymap.name}:")
    lines.append("")
    _format_bindings(keymap, "", lines)
    _show_help_buffer(ed, "\n".join(lines))


def _format_bindings(km: Keymap, prefix: str, lines: list[str]) -> None:
    """Append formatted binding lines from *km* (recursing into sub-keymaps)."""
    for key, target in sorted(km.all_bindings().items()):
        full = f"{prefix} {key}" if prefix else key
        if isinstance(target, str):
            lines.append(f"  {full:<20s} {target}")
        elif isinstance(target, Keymap):
            _format_bindings(target, full, lines)


def _format_bindings_local(km: Keymap, prefix: str, lines: list[str]) -> None:
    """Append binding lines from *km* only (no parent-chain walk).

    Sub-keymaps bound as prefix keys *are* recursed into — those are
    proper children, not ancestors in the inheritance chain.
    """
    for key, target in sorted(km.bindings().items()):
        full = f"{prefix} {key}" if prefix else key
        if isinstance(target, str):
            lines.append(f"  {full:<20s} {target}")
        elif isinstance(target, Keymap):
            _format_bindings_local(target, full, lines)


@defcommand(
    "describe-bindings",
    "Show all currently-active key bindings (C-h b).",
)
def describe_bindings(ed: Editor, prefix: int | None) -> None:
    """List every key binding reachable from the current buffer.

    Bindings are grouped by layer (buffer-local → minor modes → major
    mode → global) so the resolution order is visible at a glance.
    """
    buf = ed.buffer
    lines: list[str] = ["Key Bindings", "=" * 40, ""]

    # Buffer-local keymap (e.g., *Notes*, *shell*)
    if buf.keymap is not None:
        lines.append(f"Buffer-local bindings ({buf.keymap.name}):")
        lines.append("")
        _format_bindings_local(buf.keymap, "", lines)
        lines.append("")

    # Minor-mode keymaps (last added = highest priority)
    for mode in reversed(buf.minor_modes):
        if mode.keymap is not None:
            lines.append(f"Minor mode bindings ({mode.name}):")
            lines.append("")
            _format_bindings_local(mode.keymap, "", lines)
            lines.append("")

    # Major-mode keymap
    if buf.major_mode is not None and buf.major_mode.keymap is not None:
        lines.append(f"Major mode bindings ({buf.major_mode.name}):")
        lines.append("")
        _format_bindings_local(buf.major_mode.keymap, "", lines)
        lines.append("")

    # Global keymap (always present)
    lines.append(f"Global bindings ({ed.global_keymap.name}):")
    lines.append("")
    _format_bindings_local(ed.global_keymap, "", lines)

    _show_help_buffer(ed, "\n".join(lines))


@defcommand(
    "where-is",
    "Show which key(s) a command is bound to (C-h x).",
)
def where_is(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.commands import COMMANDS

    def completer(text: str) -> list[str]:
        return sorted(n for n in COMMANDS if n.startswith(text))

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            return
        keymap = ed._resolve_keymap()
        keys = keymap.reverse_lookup(name)
        if keys:
            key_str = ", ".join(keys)
            ed.message = f"{name} is on {key_str}"
        else:
            ed.message = f"{name} is not on any key"

    ed.start_minibuffer("Where is command: ", callback, completer=completer)


@defcommand(
    "describe-variable",
    "Show the value and documentation of a variable (C-h v).",
)
def describe_variable(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.variables import VARIABLES

    def completer(text: str) -> list[str]:
        return sorted(n for n in VARIABLES if n.startswith(text))

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            return
        var = VARIABLES.get(name)
        if var is None:
            ed.message = f"Unknown variable: {name}"
            return
        current = ed.get_variable(name)
        lines = [
            f"{name} is a variable.",
            "",
            f"  Value: {current!r}",
            f"  Default: {var.default!r}",
            f"  Type: {var.type.__name__}",
        ]
        if var.doc:
            lines.append("")
            lines.append(f"  {var.doc}")
        # Show if buffer-local
        if name in ed.buffer.local_variables:
            lines.append("")
            lines.append(f"  Buffer-local value: {ed.buffer.local_variables[name]!r}")
        _show_help_buffer(ed, "\n".join(lines))

    ed.start_minibuffer("Describe variable: ", callback, completer=completer)


@defcommand(
    "set-variable",
    "Set the value of an editor variable.",
)
def set_variable(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.variables import VARIABLES

    def completer(text: str) -> list[str]:
        return sorted(n for n in VARIABLES if n.startswith(text))

    def callback_name(name: str) -> None:
        name = name.strip()
        if not name:
            return
        var = VARIABLES.get(name)
        if var is None:
            ed.message = f"Unknown variable: {name}"
            return

        def callback_value(value_str: str) -> None:
            value_str = value_str.strip()
            if not value_str:
                return
            try:
                value = var.validate(value_str)
            except ValueError as e:
                ed.message = str(e)
                return
            var.default = value
            ed.message = f"Set {name} to {value!r}"

        current = ed.get_variable(name)
        ed.start_minibuffer(
            f"Set {name} (currently {current!r}) to: ",
            callback_value,
        )

    ed.start_minibuffer("Set variable: ", callback_name, completer=completer)


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


@defcommand("help-tutorial", "Open the neon-edit tutorial (C-h t).")
def help_tutorial(ed: Editor, prefix: int | None) -> None:
    # Switch to existing tutorial buffer if open
    for buf in ed.buffers:
        if buf.name == "TUTORIAL.txt":
            ed.switch_to_buffer("TUTORIAL.txt")
            return
    # Load from disk
    try:
        text = _TUTORIAL_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        ed.message = "Tutorial file not found"
        return
    ed.create_buffer(name="TUTORIAL.txt", text=text)
    ed.buffer.read_only = True
    ed.buffer.modified = False


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


@defcommand(
    "save-some-buffers",
    "Offer to save each modified buffer (C-x s).",
)
def save_some_buffers(ed: Editor, prefix: int | None) -> None:
    modified = [b for b in ed.buffers if b.modified and b.filepath]
    if not modified:
        ed.message = "(No buffers need saving)"
        return

    saved_count = [0]
    remaining = list(modified)

    def _ask_next() -> None:
        if not remaining:
            if saved_count[0]:
                ed.message = f"Saved {saved_count[0]} buffer(s)"
            else:
                ed.message = "(No buffers saved)"
            return
        buf = remaining[0]

        def callback(answer: str) -> None:
            answer = answer.strip().lower()
            buf_ref = remaining.pop(0)
            if (
                answer == "y"
                and ed.save_callback is not None
                and ed.save_callback(buf_ref)
            ):
                buf_ref.modified = False
                saved_count[0] += 1
            _ask_next()

        ed.start_minibuffer(f"Save buffer {buf.name}? (y/n) ", callback)

    _ask_next()


# ═══════════════════════════════════════════════════════════════════════
# Replace
# ═══════════════════════════════════════════════════════════════════════


@defcommand(
    "replace-string",
    "Replace occurrences of a string from point to end of buffer.",
)
def replace_string(ed: Editor, prefix: int | None) -> None:
    def ask_search(search: str) -> None:
        search = search.strip()
        if not search:
            return

        def ask_replacement(replacement: str) -> None:
            buf = ed.buffer
            count = 0
            # Single undo group for the entire replacement
            buf.add_undo_boundary()
            ln = buf.point.line
            col = buf.point.col
            while True:
                pos = buf.find_forward(search, ln, col)
                if pos is None:
                    break
                # Move point to start of match, delete match, insert replacement
                buf.point.move_to(pos[0], pos[1])
                end = Mark(pos[0], pos[1] + len(search))
                # Handle multi-line search strings would need more, but
                # for now search is single-line (find_forward is line-based)
                buf.delete_region(buf.point.copy(), end)
                buf.insert_string(replacement)
                count += 1
                # Continue from after the replacement
                ln = buf.point.line
                col = buf.point.col
            buf.add_undo_boundary()
            if count:
                ed.message = f"Replaced {count} occurrence{'s' if count != 1 else ''}"
            else:
                ed.message = "No matches"

        ed.start_minibuffer(f"Replace string {search} with: ", ask_replacement)

    ed.start_minibuffer("Replace string: ", ask_search)


# ═══════════════════════════════════════════════════════════════════════
# Fill / paragraph
# ═══════════════════════════════════════════════════════════════════════


def _find_paragraph_bounds(buf: Buffer, line: int) -> tuple[int, int]:
    """Return (start_line, end_line) of the paragraph containing *line*.

    A paragraph is delimited by blank lines (or buffer boundaries).
    *end_line* is inclusive.
    """
    # Search backward for paragraph start
    start = line
    while start > 0 and buf.lines[start - 1].strip():
        start -= 1
    # Search forward for paragraph end
    end = line
    while end < buf.line_count - 1 and buf.lines[end + 1].strip():
        end += 1
    return start, end


def _fill_lines(lines: list[str], fill_column: int) -> list[str]:
    """Re-flow *lines* into a paragraph wrapped at *fill_column*."""
    # Join all words
    words: list[str] = []
    for line in lines:
        words.extend(line.split())
    if not words:
        return [""]

    result: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= fill_column:
            current += " " + word
        else:
            result.append(current)
            current = word
    result.append(current)
    return result


@defcommand(
    "fill-paragraph",
    "Rewrap the current paragraph to fill-column width (M-q).",
)
def fill_paragraph(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    if buf.read_only:
        ed.message = "Buffer is read-only"
        return
    # If point is on a blank line, nothing to fill
    if not buf.lines[buf.point.line].strip():
        ed.message = "No paragraph to fill"
        return
    fill_col = ed.get_variable("fill-column") or 70
    start, end = _find_paragraph_bounds(buf, buf.point.line)
    para_lines = buf.lines[start : end + 1]
    new_lines = _fill_lines(para_lines, fill_col)
    if new_lines == para_lines:
        ed.message = "Paragraph unchanged"
        return
    # Replace the paragraph text
    buf.add_undo_boundary()
    start_mark = Mark(start, 0)
    end_mark = Mark(end, len(buf.lines[end]))
    buf.delete_region(start_mark, end_mark)
    buf.point.move_to(start, 0)
    buf.insert_string("\n".join(new_lines))
    buf.add_undo_boundary()
    ed.message = "Filled paragraph"


@defcommand(
    "set-fill-column",
    "Set the fill column (C-x f). With prefix arg, set to that value.",
)
def set_fill_column(ed: Editor, prefix: int | None) -> None:
    if prefix is not None:
        ed.set_variable("fill-column", prefix)
        ed.message = f"fill-column set to {prefix}"
    else:
        col = ed.buffer.point.col
        ed.set_variable("fill-column", col)
        ed.message = f"fill-column set to {col}"


@defcommand(
    "auto-fill-mode",
    "Toggle auto-fill minor mode.",
)
def auto_fill_mode(ed: Editor, prefix: int | None) -> None:
    ed.toggle_minor_mode("auto-fill-mode")


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
# Window commands
# ═══════════════════════════════════════════════════════════════════════


def _switch_to_window(ed: Editor, win: Window) -> None:
    """Common logic: switch editor focus to *win*."""
    # Switch editor's current buffer to the window's buffer
    for i, b in enumerate(ed._buffers):
        if b is win.buffer:
            ed._current_index = i
            break
    # Restore window's point into buffer
    win.sync_to_buffer()
    # Update viewport
    ed.viewport = win


@defcommand(
    "split-window-below",
    "Split the current window into two, one above the other (C-x 2).",
)
def split_window_below(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.window import SplitDirection

    tree = ed._window_tree
    if tree is None:
        ed.message = "No window system"
        return
    tree.active.sync_from_buffer()
    tree.split(SplitDirection.HORIZONTAL)
    ed.message = ""


@defcommand(
    "split-window-right",
    "Split the current window side by side (C-x 3).",
)
def split_window_right(ed: Editor, prefix: int | None) -> None:
    from recursive_neon.editor.window import SplitDirection

    tree = ed._window_tree
    if tree is None:
        ed.message = "No window system"
        return
    tree.active.sync_from_buffer()
    tree.split(SplitDirection.VERTICAL)
    ed.message = ""


@defcommand("other-window", "Select the next window (C-x o).")
def other_window(ed: Editor, prefix: int | None) -> None:
    tree = ed._window_tree
    if tree is None or tree.is_single():
        ed.message = "Only one window"
        return
    tree.active.sync_from_buffer()
    new = tree.next_window()
    _switch_to_window(ed, new)


@defcommand(
    "delete-window",
    "Delete the current window (C-x 0).",
)
def delete_window(ed: Editor, prefix: int | None) -> None:
    tree = ed._window_tree
    if tree is None or tree.is_single():
        ed.message = "Attempt to delete sole ordinary window"
        return
    tree.active.sync_from_buffer()
    new = tree.delete_window()
    if new is not None:
        _switch_to_window(ed, new)


@defcommand(
    "delete-other-windows",
    "Make the current window fill the frame (C-x 1).",
)
def delete_other_windows(ed: Editor, prefix: int | None) -> None:
    tree = ed._window_tree
    if tree is None:
        ed.message = "No window system"
        return
    if tree.is_single():
        ed.message = "Already only one window"
        return
    tree.active.sync_from_buffer()
    tree.delete_other_windows()
    ed.message = ""


@defcommand(
    "scroll-other-window",
    "Scroll the other window forward one screenful (C-M-v).",
)
def scroll_other_window(ed: Editor, prefix: int | None) -> None:
    tree = ed._window_tree
    if tree is None or tree.is_single():
        ed.message = "Only one window"
        return
    other = tree.other_window()
    if other is None:
        ed.message = "Only one window"
        return
    n = prefix if prefix is not None else other.text_height
    new_top = min(other.scroll_top + n, max(0, other.buffer.line_count - 1))
    other.scroll_to(new_top)


@defcommand(
    "find-file-other-window",
    "Open a file in the other window (C-x 4 C-f).",
)
def find_file_other_window(ed: Editor, prefix: int | None) -> None:
    tree = ed._window_tree
    if tree is None:
        ed.message = "No window system"
        return

    def callback(path: str) -> None:
        from recursive_neon.editor.window import SplitDirection

        path = path.strip()
        if not path:
            return
        # If only one window, split first
        if tree.is_single():
            tree.active.sync_from_buffer()
            tree.split(SplitDirection.HORIZONTAL)
        # Switch to the other window
        tree.active.sync_from_buffer()
        other = tree.other_window()
        if other is not None:
            tree.active = other
            _switch_to_window(ed, other)
        # Now open/switch to the file in this window
        for buf in ed.buffers:
            if buf.filepath == path:
                ed.switch_to_buffer(buf.name)
                ed.message = f"Switched to {buf.name}"
                return
        content = ""
        if ed.open_callback is not None:
            content = ed.open_callback(path)
        name = path.rsplit("/", 1)[-1] if "/" in path else path
        ed.create_buffer(name=name, text=content, filepath=path)
        ed.message = f"Opened {path}" if content else f"(New file) {path}"

    ed.start_minibuffer("Find file: ", callback, completer=ed.path_completer)


# ═══════════════════════════════════════════════════════════════════════
# Default keymap
# ═══════════════════════════════════════════════════════════════════════


def build_default_keymap() -> Keymap:
    # Ensure shell-mode commands/mode are registered
    import recursive_neon.editor.shell_mode  # noqa: F401

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

    # Sentence movement
    km.bind("M-e", "forward-sentence")
    km.bind("M-a", "backward-sentence")
    km.bind("M-k", "kill-sentence")

    # Fill
    km.bind("M-q", "fill-paragraph")

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

    # Viewport scrolling
    km.bind("C-v", "scroll-up")
    km.bind("PageDown", "scroll-up")
    km.bind("M-v", "scroll-down")
    km.bind("PageUp", "scroll-down")
    km.bind("C-l", "recenter")
    km.bind("C-M-v", "scroll-other-window")

    # M-x
    km.bind("M-x", "execute-extended-command")

    # C-h prefix map (help)
    ch = Keymap("C-h prefix")
    ch.bind("k", "describe-key")
    ch.bind("c", "describe-key-briefly")
    ch.bind("a", "command-apropos")
    ch.bind("b", "describe-bindings")
    ch.bind("t", "help-tutorial")
    ch.bind("m", "describe-mode")
    ch.bind("v", "describe-variable")
    ch.bind("x", "where-is")
    km.bind("C-h", ch)

    # C-x prefix map
    cx = Keymap("C-x prefix")
    cx.bind("C-s", "save-buffer")
    cx.bind("s", "save-some-buffers")
    cx.bind("C-w", "write-file")
    cx.bind("C-f", "find-file")
    cx.bind("b", "switch-to-buffer")
    cx.bind("k", "kill-buffer")
    cx.bind("C-b", "list-buffers")
    cx.bind("C-c", "quit-editor")
    cx.bind("u", "undo")
    cx.bind("f", "set-fill-column")
    # Window commands
    cx.bind("2", "split-window-below")
    cx.bind("3", "split-window-right")
    cx.bind("o", "other-window")
    cx.bind("0", "delete-window")
    cx.bind("1", "delete-other-windows")
    # C-x 4 prefix map
    cx4 = Keymap("C-x 4 prefix")
    cx4.bind("C-f", "find-file-other-window")
    cx.bind("4", cx4)
    km.bind("C-x", cx)

    return km
