"""
Default editor commands and keybindings.

Registers the standard Emacs-like commands and builds the default
global keymap.  Import this module to populate the command table.

The larger self-contained command families live in sibling modules —
``isearch_commands`` (C-s/C-r), ``replace_commands`` (M-% +
replace-string) and ``register_commands`` (C-x r) — imported below so
their ``defcommand`` registrations run whenever this module is loaded.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

# Registration side effects + re-exports (editor.py and tests import some
# of these names from here historically; the modules have no imports back
# into this one, so the order is safe).
import recursive_neon.editor.isearch_commands  # noqa: F401
from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.mark import Mark
from recursive_neon.editor.register_commands import (  # noqa: F401
    _char_position,
    _do_register_action,
)
from recursive_neon.editor.replace_commands import (  # noqa: F401
    _QR_SEP,
    _qr_handle_key,
    _QueryReplaceSession,
    _replace_read_args,
)

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
    _char_move(ed, prefix if prefix is not None else 1)


@defcommand("backward-char", "Move point backward one character.")
def backward_char(ed: Editor, prefix: int | None) -> None:
    _char_move(ed, -(prefix if prefix is not None else 1))


def _char_move(ed: Editor, n: int) -> None:
    """Horizontal motion shared by ``forward-char`` and ``backward-char``.

    GNU Emacs signals an end-of-buffer / beginning-of-buffer error when
    the motion cannot consume the full count — point still moves as far
    as it can, and the echo area shows ``End of buffer`` / ``Beginning
    of buffer`` (e.g. ``C-f`` in an empty buffer; verified against Emacs
    29 via parity scenario 26). neon-edit used to be silent here.
    """
    buf = ed.buffer
    before = _char_position(buf, buf.point.line, buf.point.col)
    buf.forward_char(n)
    after = _char_position(buf, buf.point.line, buf.point.col)
    if abs(after - before) < abs(n):
        ed.message = "End of buffer" if n > 0 else "Beginning of buffer"


@defcommand("next-line", "Move point to the next line.")
def next_line(ed: Editor, prefix: int | None) -> None:
    _line_move(ed, prefix if prefix is not None else 1)


@defcommand("previous-line", "Move point to the previous line.")
def previous_line(ed: Editor, prefix: int | None) -> None:
    _line_move(ed, -(prefix if prefix is not None else 1))


def _line_move(ed: Editor, n: int) -> None:
    """Vertical motion shared by ``next-line`` and ``previous-line``.

    When the requested motion would carry point past the buffer's first or
    last line, point lands at ``point-min`` (column 0 of line 0) or
    ``point-max`` (end of last line) respectively, and the echo area shows
    ``Beginning of buffer`` / ``End of buffer`` — matching GNU Emacs.
    """
    buf = ed.buffer
    before_line = buf.point.line
    buf.forward_line(n)
    actually_moved = buf.point.line - before_line
    if actually_moved == n:
        return
    if n > 0:
        last = buf.line_count - 1
        buf.point.line = last
        buf.point.col = len(buf.lines[last])
        ed.message = "End of buffer"
    else:
        buf.point.line = 0
        buf.point.col = 0
        ed.message = "Beginning of buffer"


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


def _push_mark_for_big_motion(ed: Editor, prefix: int | None) -> None:
    """Push a mark before a buffer-spanning motion, GNU Emacs style.

    ``beginning-of-buffer`` / ``end-of-buffer`` push the mark (so the
    user can jump back with C-u C-SPC) unless a prefix arg was given or
    the region is already active; ``push-mark`` itself echoes ``Mark
    set``. The pushed mark is *inactive* — no region highlight (verified
    against Emacs via parity scenario 30's highlight capture).
    """
    buf = ed.buffer
    if prefix is None and not buf.region_active:
        buf.push_mark()
        ed.message = "Mark set"


@defcommand("beginning-of-buffer", "Move point to the beginning of the buffer.")
def beginning_of_buffer(ed: Editor, prefix: int | None) -> None:
    _push_mark_for_big_motion(ed, prefix)
    ed.buffer.beginning_of_buffer()


@defcommand("end-of-buffer", "Move point to the end of the buffer.")
def end_of_buffer(ed: Editor, prefix: int | None) -> None:
    _push_mark_for_big_motion(ed, prefix)
    ed.buffer.end_of_buffer()


# ═══════════════════════════════════════════════════════════════════════
# Editing
# ═══════════════════════════════════════════════════════════════════════


@defcommand(
    "self-insert-command",
    "Insert the character that invoked this command.",
    coalesce_key="insert",
)
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


def _indent_points(line: str) -> list[int]:
    """Columns in *line* where a non-whitespace run begins.

    These are GNU Emacs's "indent points" for ``indent-relative`` — the
    start of each word (a non-blank char at column 0, or preceded by a
    blank). Assumes no tab characters (neon-edit indents with spaces).
    """
    return [
        c
        for c, ch in enumerate(line)
        if ch not in " \t" and (c == 0 or line[c - 1] in " \t")
    ]


def _indent_relative_target(ed: Editor, start_col: int) -> int:
    """The column ``indent-relative`` would indent to from *start_col*.

    Indents to the nearest indent point — past *start_col* — of the closest
    previous non-blank line; with none (or no previous line) falls back to
    ``tab-to-tab-stop`` (the next multiple of ``tab-width``).
    """
    buf = ed.buffer
    for ln in range(buf.point.line - 1, -1, -1):
        if buf.lines[ln].strip():
            for col in _indent_points(buf.lines[ln]):
                if col > start_col:
                    return col
            break  # only the nearest previous non-blank line is consulted
    tw = ed.get_variable("tab-width") or 8
    return ((start_col // tw) + 1) * tw


@defcommand(
    "indent-for-tab-command",
    "Indent the current line (TAB) — text-mode indent-relative.",
)
def indent_for_tab_command(ed: Editor, prefix: int | None) -> None:
    """GNU Emacs's TAB. Dispatches to the major mode's indent-line-function
    when it has one (e.g. python-mode's syntactic, cycling indentation);
    otherwise the text / fundamental default ``indent-relative``: line up
    with the previous line's words, falling back to ``tab-to-tab-stop`` past
    the last one (or on the first line).

    Deviation (documented): we insert spaces rather than the tab/space mix
    Emacs uses under ``indent-tabs-mode`` — the on-screen result is identical.
    """
    buf = ed.buffer
    mode = buf.major_mode
    if mode is not None and mode.indent_line_function is not None:
        mode.indent_line_function(ed)
        return
    start_col = buf.point.col
    target = _indent_relative_target(ed, start_col)
    if target > start_col:
        buf.insert_string(" " * (target - start_col))


@defcommand(
    "delete-char", "Delete the character after point.", coalesce_key="delete-forward"
)
def delete_char(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.delete_char_forward()


@defcommand(
    "delete-backward-char",
    "Delete the character before point.",
    coalesce_key="delete-backward",
)
def delete_backward_char(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.delete_char_backward()


# ═══════════════════════════════════════════════════════════════════════
# Kill / Yank
# ═══════════════════════════════════════════════════════════════════════


@defcommand("kill-line", "Kill from point to end of line.", coalesce_key="kill")
def kill_line(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_line()


@defcommand(
    "kill-region", "Kill the region (text between point and mark).", coalesce_key="kill"
)
def kill_region(ed: Editor, prefix: int | None) -> None:
    ed.buffer.kill_region()


@defcommand(
    "kill-word", "Kill from point to the end of the current word.", coalesce_key="kill"
)
def kill_word(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_word_forward()


@defcommand(
    "kill-backward-word",
    "Kill backward to the start of the current word.",
    coalesce_key="kill",
)
def kill_backward_word(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_word_backward()


@defcommand(
    "kill-sentence", "Kill from point to the end of the sentence.", coalesce_key="kill"
)
def kill_sentence(ed: Editor, prefix: int | None) -> None:
    n = prefix if prefix is not None else 1
    for _ in range(n):
        ed.buffer.kill_sentence()


@defcommand(
    "kill-ring-save",
    "Copy the region to the kill ring (no buffer mutation, M-w).",
)
def kill_ring_save(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    if buf.mark is None:
        ed.message = "The mark is not set now, so there is no region"
        return
    buf.kill_ring_save()


@defcommand("yank", "Yank (paste) the most recent kill.", coalesce_key="yank")
def yank(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    # GNU Emacs's ``yank`` pushes an *inactive* mark at the start of the
    # inserted text so the user can immediately act on the region (e.g.
    # C-w to un-yank, M-w to copy elsewhere — region commands work with
    # an inactive mark). ``push-mark`` itself announces ``Mark set``.
    buf.push_mark(buf.point.line, buf.point.col)
    if buf.yank() is None:
        ed.message = "Kill ring is empty"
        return
    ed.message = "Mark set"


@defcommand(
    "yank-pop",
    "Replace just-yanked text with the next kill ring entry.",
    coalesce_key="yank",
)
def yank_pop(ed: Editor, prefix: int | None) -> None:
    # GNU Emacs >= 28: when the previous command was *not* a yank, M-y
    # runs ``yank-from-kill-ring`` instead of failing — the rotate-in-place
    # behaviour only applies immediately after C-y / M-y.
    if ed.buffer.last_command_type != "yank":
        _yank_from_kill_ring(ed)
        return
    ed.buffer.yank_pop()


def _yank_from_kill_ring(ed: Editor) -> None:
    """``yank-from-kill-ring`` — choose a kill-ring entry via the minibuffer.

    Mirrors GNU Emacs 29 (verified via the parity harness, scenario 22):

    * ``Yank from kill-ring: `` prompt; the ring entries (most recent
      first) are both the M-p/M-n history and the TAB completion
      candidates (``read-from-kill-ring`` passes ``kill-ring`` to
      ``completing-read`` as history *and* collection).
    * RET inserts the minibuffer content literally at point — typed text
      that matches no ring entry is inserted as-is (``completing-read``
      runs with ``require-match`` nil), and empty input inserts nothing.
    * A mark is pushed at the insert position unconditionally
      (``push-mark`` precedes ``insert-for-yank``), echoing ``Mark set``
      even for empty input.
    * The accept does not mark the command as a yank: an immediately
      following M-y re-prompts rather than rotating like yank-pop.
    * On an empty ring, ``current-kill`` signals before the prompt opens:
      the echo area shows ``Kill ring is empty``.
    """
    buf = ed.buffer
    if buf.kill_ring.empty:
        ed.message = "Kill ring is empty"
        return
    entries = list(buf.kill_ring.entries)

    def on_submit(text: str) -> None:
        b = ed.buffer
        b.push_mark(b.point.line, b.point.col)
        if text:
            b.insert_string(text)
        ed.message = "Mark set"

    def completer(text: str) -> list[str]:
        return [e for e in entries if e.startswith(text)]

    ed.start_minibuffer(
        "Yank from kill-ring: ",
        on_submit,
        completer=completer,
        history_list=entries,
    )


# ═══════════════════════════════════════════════════════════════════════
# Undo
# ═══════════════════════════════════════════════════════════════════════


@defcommand("undo", "Undo the last editing operation.")
def undo(ed: Editor, prefix: int | None) -> None:
    if ed.buffer.undo():
        # GNU Emacs echoes "Undo" on every successful undo and "Redo" when
        # the operation is undoing a previous undo. Plain words, no
        # exclamation mark — the "Undo!" form is Emacs-20-era and was
        # dropped by modern Emacs (verified against Emacs 29 via the parity
        # harness; see parity/scenarios/scenario_09_undo_redo.py).
        ed.message = "Redo" if ed.buffer.last_undo_was_redo else "Undo"
    else:
        ed.message = "No further undo information"


# ═══════════════════════════════════════════════════════════════════════
# Mark / Region
# ═══════════════════════════════════════════════════════════════════════


@defcommand("set-mark-command", "Set the mark at point (C-SPC).")
def set_mark_command(ed: Editor, prefix: int | None) -> None:
    """GNU Emacs's ``set-mark-command``, all three behaviours (verified
    against Emacs 29 via the parity probe / scenarios 30-31):

    * ``C-SPC`` — push the old mark onto the ring, set and *activate*
      the mark at point (``Mark set``).
    * ``C-SPC C-SPC`` — an immediately repeated C-SPC deactivates the
      just-set mark (``Mark deactivated``), leaving it on the ring
      flow: set-then-unhighlight.
    * ``C-u C-SPC`` — jump point to the mark and rotate the mark ring
      (``pop-to-mark-command``): silent on a real jump, ``Mark popped``
      when point is already at the mark.
    """
    buf = ed.buffer
    if prefix is not None:
        if buf.mark is None:
            ed.message = "No mark set in this buffer"
            return
        if (buf.point.line, buf.point.col) == (buf.mark.line, buf.mark.col):
            ed.message = "Mark popped"
        buf.point.move_to(buf.mark.line, buf.mark.col)
        buf.pop_mark()
        return
    if ed._last_command_name == "set-mark-command" and buf.mark_active:
        buf.deactivate_mark()
        ed.message = "Mark deactivated"
        return
    buf.push_mark(activate=True)
    ed.message = "Mark set"


@defcommand(
    "exchange-point-and-mark",
    "Swap point and mark, leaving the region intact (C-x C-x).",
)
def exchange_point_and_mark(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    if buf.mark is None:
        ed.message = "No mark set in this buffer"
        return
    mark_line, mark_col = buf.mark.line, buf.mark.col
    point_line, point_col = buf.point.line, buf.point.col
    # set_mark (not push_mark): C-x C-x swaps without growing the mark
    # ring, and *reactivates* the region — Emacs highlights the swapped
    # region even when the mark was inactive (e.g. right after M-w).
    buf.set_mark(point_line, point_col)
    buf.point.move_to(mark_line, mark_col)


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

    ed.start_minibuffer("M-x ", callback, completer=completer, history="command")


@defcommand("switch-to-buffer", "Switch to a different buffer (C-x b).")
def switch_to_buffer(ed: Editor, prefix: int | None) -> None:
    default = ed.other_buffer_name()

    def completer(text: str) -> list[str]:
        return [b.name for b in ed.buffers if b.name.startswith(text)]

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            # Empty input switches to the default (the MRU "other" buffer),
            # matching GNU Emacs. With no other buffer there is nothing to do.
            if default is None:
                return
            name = default
        if not ed.switch_to_buffer(name):
            # No such buffer → create it. Emacs does this silently; the new
            # empty buffer appearing on screen is the only feedback.
            ed.create_buffer(name=name)

    prompt = (
        f"Switch to buffer (default {default}): " if default else "Switch to buffer: "
    )
    ed.start_minibuffer(prompt, callback, completer=completer, history="buffer-name")


@defcommand("kill-buffer", "Kill (close) a buffer (C-x k).")
def kill_buffer(ed: Editor, prefix: int | None) -> None:
    # Emacs's kill-buffer default is the current buffer, offered in the
    # prompt rather than pre-filled into the editable input.
    default = ed.buffer.name

    def completer(text: str) -> list[str]:
        return [b.name for b in ed.buffers if b.name.startswith(text)]

    def callback(name: str) -> None:
        name = name.strip()
        if not name:
            name = default
        target = next((b for b in ed.buffers if b.name == name), None)
        if target is not None and target.modified and target.filepath:
            # A modified *file-visiting* buffer needs confirmation
            # (Emacs's kill-buffer--possibly-save). Modified buffers
            # without a file — *scratch* and friends — are killed
            # silently, matching Emacs.
            _confirm_kill_modified(ed, target)
            return
        if ed.remove_buffer(name):
            # Emacs's kill-buffer is silent on success (remove_buffer left a
            # "Killed buffer" message — clear it to match). A failed kill
            # keeps remove_buffer's "No buffer named …" message.
            ed.message = ""

    ed.start_minibuffer(
        f"Kill buffer (default {default}): ",
        callback,
        completer=completer,
        history="buffer-name",
    )


_KILL_CONFIRM_ANSWERS = ("yes", "no", "save and then kill")


def _confirm_kill_modified(ed: Editor, target: Buffer) -> None:
    """Confirm killing a modified file-visiting buffer.

    Mirrors GNU Emacs 29's ``kill-buffer--possibly-save``: a long-form
    ``read-multiple-choice`` prompt — ``Buffer NAME modified; kill
    anyway? (yes/no/save and then kill)`` — read through the minibuffer
    with completion, so a unique prefix submitted with RET completes to
    its answer (``y`` → ``yes``; verified against Emacs 29 via the
    parity harness, scenario 27). Invalid input re-prompts.
    """
    prompt = f"Buffer {target.name} modified; kill anyway? (yes/no/save and then kill) "

    def completer(text: str) -> list[str]:
        return [a for a in _KILL_CONFIRM_ANSWERS if a.startswith(text)]

    def kill() -> None:
        if ed.remove_buffer(target.name):
            ed.message = ""

    def on_submit(text: str) -> None:
        if text in _KILL_CONFIRM_ANSWERS:
            answer = text
        else:
            matches = completer(text) if text else []
            if len(matches) != 1:
                # No unique completion: Emacs's completing-read (with
                # require-match) refuses to exit — re-prompt.
                _confirm_kill_modified(ed, target)
                return
            answer = matches[0]
        if answer == "no":
            ed.message = ""
            return
        if answer == "save and then kill":
            saved = bool(target.on_save is not None and target.on_save(target))
            if not saved and ed.save_callback is not None:
                saved = ed.save_callback(target)
            if not saved:
                ed.message = "Save failed"
                return
            target.mark_saved()
            _publish_buffer_saved(ed, target)
            kill()
            # The save's "Wrote …" message outlives the (silent) kill.
            ed.message = "Wrote " + (target.filepath or target.name)
            return
        kill()  # "yes"

    ed.start_minibuffer(prompt, on_submit, completer=completer)


@defcommand("write-file", "Write buffer to a file path (C-x C-w).")
def write_file(ed: Editor, prefix: int | None) -> None:
    def callback(path: str) -> None:
        path = path.strip()
        if not path:
            return
        ed.buffer.filepath = path
        ed.buffer.name = path.rsplit("/", 1)[-1] if "/" in path else path
        # Attempt save via on_save hook or save callback
        saved = False
        if ed.buffer.on_save is not None:
            saved = ed.buffer.on_save(ed.buffer)
        if not saved and ed.save_callback is not None:
            saved = ed.save_callback(ed.buffer)
        if saved:
            ed.buffer.mark_saved()
            ed.message = f"Wrote {path}"
            _publish_buffer_saved(ed, ed.buffer)
        elif ed.save_callback is not None or ed.buffer.on_save is not None:
            ed.message = "Save failed"
        else:
            ed.message = f"File path set to {path} (no save handler)"

    initial = ed.buffer.filepath or ""
    ed.start_minibuffer(
        "Write file: ",
        callback,
        initial=initial,
        completer=ed.path_completer,
        history="file-name",
    )


def _auto_detect_mode(ed: Editor, filepath: str) -> None:
    """Set the buffer's major mode based on file extension."""
    from recursive_neon.editor.modes import MODES, detect_mode

    mode_name = detect_mode(filepath)
    mode = MODES.get(mode_name)
    if mode is not None and mode is not ed.buffer.major_mode:
        ed.set_major_mode(mode_name)


@defcommand("find-file", "Open or create a file (C-x C-f).")
def find_file(ed: Editor, prefix: int | None) -> None:
    def callback(path: str) -> None:
        path = path.strip()
        if not path:
            return
        # A directory path opens dired instead (Emacs's find-file).
        from recursive_neon.editor.dired import maybe_open_dired_for_path

        if maybe_open_dired_for_path(ed, path):
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
        _auto_detect_mode(ed, path)
        ed.message = f"Opened {path}" if content else f"(New file) {path}"

    initial = ed.default_directory
    if initial and not initial.endswith("/"):
        initial += "/"
    ed.start_minibuffer(
        "Find file: ",
        callback,
        completer=ed.path_completer,
        initial=initial,
        history="file-name",
    )


# ═══════════════════════════════════════════════════════════════════════
# Help
# ═══════════════════════════════════════════════════════════════════════


DESCRIBE_KEY_PROMPT = "Describe the following key, mouse click, or menu item: "


@defcommand("describe-key", "Show what command a key is bound to (C-h k).")
def describe_key(ed: Editor, prefix: int | None) -> None:
    """Enter a key-reading mode: the next keystroke is described."""
    from recursive_neon.editor.editor import _DescribeKeySession

    ed.message = DESCRIBE_KEY_PROMPT
    ed._describe_key_session = _DescribeKeySession(brief=False)


@defcommand(
    "describe-key-briefly",
    "Show what command a key runs, in the message area (C-h c).",
)
def describe_key_briefly(ed: Editor, prefix: int | None) -> None:
    """Like describe-key but shows in message area, not *Help* buffer."""
    from recursive_neon.editor.editor import _DescribeKeySession

    ed.message = "Describe key briefly: "
    ed._describe_key_session = _DescribeKeySession(brief=True)


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
    ed.buffer.mark_saved()


def _show_popup_buffer(ed: Editor, *, name: str, text: str, major_mode: str) -> None:
    """Populate a read-only popup buffer and show it in the other window.

    Generalises the ``*Help*`` / ``*Completions*`` flow. The active window
    keeps its current buffer and focus; the popup lives in the next sibling
    window (creating a horizontal split if there's only one window so far).
    When no window system is attached (unit tests using ``Editor`` directly),
    falls back to making the popup the active buffer so callers still see
    its content via ``ed.buffer``.
    """
    previous = ed.buffer

    if not ed.switch_to_buffer(name):
        ed.create_buffer(name=name)
    buf = ed.buffer
    buf.read_only = False
    buf.lines = text.split("\n")
    buf.point.move_to(0, 0)
    buf.mark_saved()
    buf.read_only = True
    ed.set_major_mode(major_mode)

    if ed._window_tree is not None:
        for i, b in enumerate(ed._buffers):
            if b is previous:
                ed._current_index = i
                break
        ed.display_buffer_other_window(name)


def _format_buffer_list(ed: Editor) -> str:
    """Build the ``*Buffer List*`` table (GNU Emacs's Buffer-menu).

    Layout matches Emacs 29's tabulated-list defaults on a TTY, verified
    against the parity probe: ``C``/``R``/``M`` flag columns (1 cell
    each, the first two unpadded), a ``Buffer`` name column 19 wide, a
    ``Size`` column 7 wide right-aligned, ``Mode`` 16 wide, then
    ``File``. A name longer than 19 may spill into the size column's
    slack — Emacs lets it run to two cells short of the right-aligned
    size value, then truncates with ``…``.

    Flags: ``.`` marks the buffer current when the list was made, ``%``
    read-only, ``*`` modified. Buffers are listed in buffer-list order
    (current first, then most recently used); the ``*Buffer List*``
    itself is excluded, as in Emacs. On a TTY Emacs renders the header
    via ``header-line-format`` (a window decoration); neon-edit makes it
    the buffer's first line — same pixels, no header-line machinery.
    """
    name_w, size_end = 19, 30  # name column width; size right-aligns at col 30
    current = ed.buffer
    ordered: list[Buffer] = [current]
    by_name = {b.name: b for b in ed.buffers}
    for nm in ed._mru:
        b = by_name.get(nm)
        if b is not None and b is not current and b.name != "*Buffer List*":
            ordered.append(b)
    for b in ed.buffers:
        if b not in ordered and b.name != "*Buffer List*":
            ordered.append(b)

    header = (
        "CRM "
        + "Buffer".ljust(name_w + 1)
        + "Size".rjust(7)
        + " "
        + "Mode".ljust(16)
        + " File"
    )
    rows = [header.rstrip()]
    for b in ordered:
        flags = (
            ("." if b is current else " ")
            + ("%" if b.read_only else " ")
            + ("*" if b.modified else " ")
        )
        size = str(len(b.text))
        name = b.name
        max_name = max(name_w, size_end - len(size) - 2 - 4 + 1)
        if len(name) > max_name:
            name = name[: max_name - 1] + "…"
        row = flags + " " + name
        row += " " * (size_end - len(size) + 1 - len(row)) + size
        if b.major_mode:
            mode = b.major_mode.indicator or (
                b.major_mode.name.removesuffix("-mode").capitalize()
            )
        else:
            mode = "Fundamental"
        row += " " + mode.ljust(16)
        if b.filepath:
            row = row.ljust(48) + " " + b.filepath
        rows.append(row.rstrip())
    return "\n".join(rows)


@defcommand("list-buffers", "Display the buffer list in another window (C-x C-b).")
def list_buffers(ed: Editor, prefix: int | None) -> None:
    """Pop up ``*Buffer List*`` in the other window without selecting it.

    GNU Emacs's ``C-x C-b``: a read-only Buffer-menu table shown via
    ``display-buffer`` — focus stays in the current window, no echo-area
    message. Interactive Buffer-menu commands (RET to visit, ``d``/``x``
    to mark and execute deletions, ``q``) are not yet implemented; see
    docs/PARITY_HARNESS.md.
    """
    text = _format_buffer_list(ed)
    _show_popup_buffer(
        ed, name="*Buffer List*", text=text, major_mode="buffer-menu-mode"
    )


def _show_help_buffer(ed: Editor, text: str) -> None:
    """Show ``text`` in a read-only ``*Help*`` buffer (``help-mode``).

    Displayed in the *other* window so the active window keeps focus,
    matching GNU Emacs's default ``help-window-select`` of nil. The
    echo-area hint tells the user how to dismiss the popup (``q`` is
    bound in ``help-mode``).
    """
    _show_popup_buffer(ed, name="*Help*", text=text, major_mode="help-mode")
    ed.message = "Type q in help window to delete it"


def _format_completions(candidates: list[str], *, width: int) -> str:
    """Format completion candidates the way Emacs's ``*Completions*`` does.

    Emacs lays the (sorted) candidates out row-major in as many columns
    as the window width allows, preceded by a short instruction block
    and a "<N> possible completions:" header. We reproduce that shape.
    """
    sorted_c = sorted(candidates)
    n = len(sorted_c)
    max_w = max((len(c) for c in sorted_c), default=0)
    col_w = max(max_w + 2, 4)
    cols = max(1, width // col_w)
    rows = (n + cols - 1) // cols

    out: list[str] = [
        "In this buffer, type RET to select the completion near point.",
        "",
        f"{n} possible completions:",
    ]
    for r in range(rows):
        chunks: list[str] = []
        for c in range(cols):
            i = r * cols + c
            if i < n:
                chunks.append(sorted_c[i].ljust(max_w))
            else:
                break
        out.append("  ".join(chunks).rstrip())
    return "\n".join(out)


def _show_completions_buffer(ed: Editor, candidates: list[str]) -> None:
    """Pop up the ``*Completions*`` buffer for the current minibuffer."""
    width = 80
    if ed._window_tree is not None:
        # Use the active window's width if available — gives a sensible
        # column count even on narrow frames.
        width = max(20, ed._window_tree.active._width or 80)
    text = _format_completions(candidates, width=width)
    _show_popup_buffer(
        ed, name="*Completions*", text=text, major_mode="completion-list-mode"
    )


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
            if answer == "y":
                saved = False
                if buf_ref.on_save is not None:
                    saved = buf_ref.on_save(buf_ref)
                if not saved and ed.save_callback is not None:
                    saved = ed.save_callback(buf_ref)
                if saved:
                    buf_ref.mark_saved()
                    saved_count[0] += 1
                    _publish_buffer_saved(ed, buf_ref)
            _ask_next()

        ed.start_minibuffer(f"Save buffer {buf.name}? (y/n) ", callback)

    _ask_next()


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
        # Already filled — GNU Emacs's M-q is a silent no-op here.
        return
    # Replace the paragraph text.
    buf.add_undo_boundary()
    start_mark = Mark(start, 0)
    end_mark = Mark(end, len(buf.lines[end]))
    buf.delete_region(start_mark, end_mark)
    buf.point.move_to(start, 0)
    buf.insert_string("\n".join(new_lines))
    # Emacs leaves point at the start of the filled paragraph and prints no
    # echo-area message on a successful fill; match both.
    buf.point.move_to(start, 0)
    buf.add_undo_boundary()


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


@defcommand(
    "column-number-mode",
    "Toggle column number display in the mode line.",
)
def column_number_mode(ed: Editor, prefix: int | None) -> None:
    # A *global* minor mode in GNU Emacs: it flips the display for every
    # buffer and the toggle message has no "in current buffer" suffix
    # (unlike buffer-local modes such as auto-fill-mode). The mode-line
    # effect — "L2" becoming "(2,3)" — lives in view._render_modeline.
    # Prefix semantics match define-minor-mode: no prefix toggles, a
    # positive prefix enables, zero/negative disables.
    current = bool(ed.get_variable("column-number-mode"))
    enable = not current if prefix is None else prefix > 0
    ed.set_variable("column-number-mode", enable)
    state = "enabled" if enable else "disabled"
    ed.message = f"Column-Number mode {state}"


@defcommand(
    "read-only-mode",
    "Toggle the buffer's read-only state (C-x C-q).",
)
def read_only_mode(ed: Editor, prefix: int | None) -> None:
    # Emacs's read-only-mode flips buffer-read-only-p and echoes the
    # minor-mode toggle message. (A prefix arg would force a direction in
    # Emacs; a plain toggle covers the interactive C-x C-q case.)
    buf = ed.buffer
    buf.read_only = not buf.read_only
    state = "enabled" if buf.read_only else "disabled"
    ed.message = f"Read-Only mode {state} in current buffer"


@defcommand("save-buffer", "Save the current buffer to its file.")
def save_buffer(ed: Editor, prefix: int | None) -> None:
    buf = ed.buffer
    # Try buffer-specific on_save first (e.g., note/task-list bridge)
    if buf.on_save is not None and buf.on_save(buf):
        buf.mark_saved()
        ed.message = "Wrote " + (buf.filepath or buf.name)
        _publish_buffer_saved(ed, buf)
        return
    if ed.save_callback is None:
        ed.message = "No save handler configured"
        return
    if ed.save_callback(buf):
        buf.mark_saved()
        ed.message = "Wrote " + (buf.filepath or buf.name)
        _publish_buffer_saved(ed, buf)
    else:
        ed.message = "Save failed"


def _publish_buffer_saved(ed: Editor, buf: Buffer) -> None:
    """Publish an ``editor.buffer_saved`` event if an event bus is wired."""
    if ed.event_bus is not None:
        ed.event_bus.publish(
            "editor.buffer_saved",
            {
                "buffer_name": buf.name,
                "filepath": buf.filepath,
                "contents": buf.text,
            },
        )


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
    "quit-window",
    "Quit the current window (q in *Help* / *Completions*).",
)
def quit_window(ed: Editor, prefix: int | None) -> None:
    """Dismiss a popup window without disturbing the others.

    Behaves like Emacs's ``quit-window``: if the current window can be
    deleted (there is more than one), do so and the previously-active
    window regains focus. When this is the only window, the window shows
    the previously-selected buffer instead and the quitted buffer is
    buried (verified against Emacs 29.3: ``q`` in a fullscreen dired
    returns to the buffer it was opened from).
    """
    tree = ed._window_tree
    if tree is None or tree.is_single():
        quitted = ed.buffer.name
        other = ed.other_buffer_name()
        if other is not None:
            ed.switch_to_buffer(other)
            # Bury the quitted buffer: drop it to the bottom of the
            # recency order so C-x b / a second quit-window prefers
            # anything else over it (Emacs's bury-buffer).
            if quitted in ed._mru:
                ed._mru.remove(quitted)
                ed._mru.append(quitted)
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
        # A directory path opens dired in this window (Emacs's
        # find-file-other-window runs dired-other-window).
        from recursive_neon.editor.dired import maybe_open_dired_for_path

        if maybe_open_dired_for_path(ed, path):
            return
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
        _auto_detect_mode(ed, path)
        ed.message = f"Opened {path}" if content else f"(New file) {path}"

    ed.start_minibuffer(
        "Find file: ", callback, completer=ed.path_completer, history="file-name"
    )


# ═══════════════════════════════════════════════════════════════════════
# Default keymap
# ═══════════════════════════════════════════════════════════════════════


def build_default_keymap() -> Keymap:
    # Ensure shell-mode commands/mode are registered
    # Ensure game-bridge commands are registered (open-note, etc.)
    # Ensure dired commands/mode are registered (C-x d, dired-*)
    # Ensure the TUI app host is registered (M-x codebreaker, sysmon, …)
    import recursive_neon.editor.app_host  # noqa: F401
    import recursive_neon.editor.dired  # noqa: F401
    import recursive_neon.editor.game_bridge  # noqa: F401
    import recursive_neon.editor.shell_mode  # noqa: F401

    # Register built-in language modes for auto-detection
    from recursive_neon.editor.modes import register_language_modes

    register_language_modes()

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
    km.bind("Tab", "indent-for-tab-command")
    km.bind("C-d", "delete-char")
    km.bind("Delete", "delete-char")
    km.bind("Backspace", "delete-backward-char")

    # Kill / Yank
    km.bind("C-k", "kill-line")
    km.bind("C-w", "kill-region")
    km.bind("M-w", "kill-ring-save")
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

    # Query replace
    km.bind("M-%", "query-replace")

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
    cx.bind("C-x", "exchange-point-and-mark")
    cx.bind("s", "save-some-buffers")
    cx.bind("C-w", "write-file")
    cx.bind("C-f", "find-file")
    cx.bind("b", "switch-to-buffer")
    cx.bind("k", "kill-buffer")
    cx.bind("C-b", "list-buffers")
    cx.bind("d", "dired")
    cx.bind("C-c", "quit-editor")
    cx.bind("u", "undo")
    cx.bind("f", "set-fill-column")
    cx.bind("C-q", "read-only-mode")
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
    # C-x r prefix map (registers): SPC saves point, j jumps to it,
    # s copies the region into a register, i inserts one at point.
    cxr = Keymap("C-x r prefix")
    cxr.bind(" ", "point-to-register")
    cxr.bind("j", "jump-to-register")
    cxr.bind("s", "copy-to-register")
    cxr.bind("i", "insert-register")
    cx.bind("r", cxr)
    km.bind("C-x", cx)

    # Mode-local keymap: ``help-mode`` binds ``q`` to quit the window.
    # The major-mode keymap delegates to ``km`` for every other key, so
    # navigation (C-n, C-v, etc.) still works inside *Help*.
    from recursive_neon.editor.modes import MODES

    help_km = Keymap("help-mode", parent=km)
    help_km.bind("q", "quit-window")
    MODES["help-mode"].keymap = help_km

    return km
