"""query-replace (M-%) and replace-string — split out of
``default_commands`` along the query-replace seam; importing this
module registers the commands (``default_commands`` does so).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from recursive_neon.editor.commands import defcommand

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor
from recursive_neon.editor.mark import Mark

# ═══════════════════════════════════════════════════════════════════════
# Query-replace (M-%)
#
# Emacs-style interactive find-and-replace.  After two sequential
# minibuffer prompts collect the from/to strings, the command installs
# a ``_QueryReplaceSession`` on ``Editor._query_replace_session``.  The
# session is consumed by the top-level routing check in
# ``Editor.process_key`` (between describe-key and the ESC state
# machine), so single keystrokes drive the replacement flow: y/SPC to
# replace, n/DEL to skip, q/RET to exit, ``.`` to replace-and-exit,
# ``!`` to replace-all, u/U to undo one / all, e to edit the
# replacement, C-g to cancel, ``?`` for a one-line help legend.
#
# Undo model: raw ``buf.delete_region`` + ``buf.insert_string`` calls
# during the session do NOT insert undo boundaries, so the entire
# session compacts into a single undo group.  ``u`` issues reverse
# raw ops (which also go into the same group — they compound rather
# than cancel, but a post-session ``C-/`` still walks the whole group
# LIFO and reverts everything to the pre-session state).  See the
# 6l-4 design addendum in ``docs/V2_HANDOVER.md`` for the alternate
# per-replacement-boundary design we considered and rejected.
#
# Deviations from Emacs (documented):
# - ``?`` shows a one-line compact legend in the message area, not a
#   pop-up window.  Real Emacs uses a split window that does not
#   disturb the session; a faithful implementation is disproportionately
#   complex under our synchronous TUI model.
# - ``case-replace`` (preserve input case in replacement) is NOT
#   implemented.  Literal replacement only.
# - ``M-c`` mid-session case-fold toggle is NOT implemented (isearch
#   has it in 6l-3; query-replace's spec doesn't).
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class _Replacement:
    """One applied replacement, stored on the session stack for u/U.

    Positions are absolute line/col in the buffer at the time the
    replacement was applied.  LIFO ordering is an invariant — later
    replacements may sit at positions shifted by earlier ones, so the
    stack must be unwound in reverse application order.
    """

    line: int
    col: int
    from_text: str
    to_text: str


@dataclass
class _QueryReplaceSession:
    """Capture-mode state for query-replace.

    Installed on ``Editor._query_replace_session`` after both entry
    prompts are submitted; cleared on session exit (normal, cancel,
    or ``_reset_transient_state``).
    """

    from_text: str
    to_text: str
    case_fold: bool
    # Session entry point — where to restore on C-g / U.
    start_line: int
    start_col: int
    # Current match start and end (exclusive).  ``None`` once we've run
    # out of matches or before the first match is found.  While a match
    # is on deck GNU Emacs leaves point at the match *end*, so we record
    # the start explicitly rather than reading it off ``ed.buffer.point``.
    current_start_line: int | None = None
    current_start_col: int | None = None
    current_end_line: int | None = None
    current_end_col: int | None = None
    # Applied-replacement stack (LIFO) for u / U.
    replacements: list[_Replacement] = field(default_factory=list)
    # True while the ``e`` sub-phase minibuffer is open; suppresses
    # the routing check so the nested minibuffer handles keys normally.
    paused_for_edit: bool = False
    # Total replacements applied (decremented by u) for reporting.
    replaced_count: int = 0

    def has_current(self) -> bool:
        """Is a match currently on deck (point is at its end)?"""
        return self.current_end_line is not None


def _qr_match_end(text: str, start_line: int, start_col: int) -> tuple[int, int]:
    """Compute the ``(line, col)`` just past a match of *text* starting
    at ``(start_line, start_col)``.  Handles multi-line needles.
    """
    if "\n" not in text:
        return (start_line, start_col + len(text))
    parts = text.split("\n")
    end_line = start_line + len(parts) - 1
    end_col = len(parts[-1])
    return (end_line, end_col)


def _qr_advance_to_next_match(ed: Editor, session: _QueryReplaceSession) -> None:
    """Find the next match from the current point; install it as the
    current match on the session, or mark the session as exhausted
    (no more matches) by leaving ``current_end_*`` as None.
    """
    buf = ed.buffer
    pos = buf.find_forward(
        session.from_text,
        buf.point.line,
        buf.point.col,
        case_fold=session.case_fold,
    )
    if pos is None:
        session.current_start_line = None
        session.current_start_col = None
        session.current_end_line = None
        session.current_end_col = None
        return
    end_line, end_col = _qr_match_end(session.from_text, pos[0], pos[1])
    session.current_start_line = pos[0]
    session.current_start_col = pos[1]
    session.current_end_line = end_line
    session.current_end_col = end_col
    # GNU Emacs prompts with point at the match *end*, not the start.
    buf.point.move_to(end_line, end_col)


def _qr_prompt(session: _QueryReplaceSession) -> str:
    """Build the message-area prompt shown while a match is on deck."""
    return f"Query replacing {session.from_text} with {session.to_text}: (? for help)"


def _qr_replaced_message(count: int) -> str:
    """The closing summary, pluralised the way GNU Emacs does.

    Emacs reports ``Replaced N occurrence`` for ``N == 1`` and
    ``Replaced N occurrences`` otherwise (including ``N == 0``) — the
    ``occurrence%s`` formula from ``perform-replace``. Verified against
    Emacs via the parity harness; see ``scenario_14_query_replace.py``.
    Matches the existing ``replace-string`` summary.
    """
    return f"Replaced {count} occurrence{'s' if count != 1 else ''}"


def _qr_replace_current(ed: Editor, session: _QueryReplaceSession) -> None:
    """Replace the current match with ``session.to_text``.  Records
    the replacement on the stack.  Leaves point just past the inserted
    replacement text so the next ``find_forward`` advances naturally.

    Precondition: ``session.has_current()`` is True. The match bounds are
    read from ``session.current_start_*`` / ``current_end_*`` — point
    itself sits at the match *end* on deck (Emacs's convention), not the
    start.
    """
    assert session.has_current(), "replace_current with no current match"
    buf = ed.buffer
    # Point sits at the match end while on deck, so take the start from
    # the session rather than from point.
    start_line = session.current_start_line
    start_col = session.current_start_col
    end_line = session.current_end_line
    end_col = session.current_end_col
    assert start_line is not None and start_col is not None
    assert end_line is not None and end_col is not None

    # Snapshot the original text for the undo stack.
    start_mark = Mark(start_line, start_col)
    end_mark = Mark(end_line, end_col)

    # Delete the match range, then insert the replacement.  Both ops
    # land on the buffer's undo list without intervening boundaries,
    # so the whole session compacts into one undo group.
    original = buf.delete_region(start_mark, end_mark)
    buf.point.move_to(start_line, start_col)
    buf.insert_string(session.to_text)

    session.replacements.append(
        _Replacement(
            line=start_line,
            col=start_col,
            from_text=original,
            to_text=session.to_text,
        )
    )
    session.replaced_count += 1
    # Current match is consumed.
    session.current_start_line = None
    session.current_start_col = None
    session.current_end_line = None
    session.current_end_col = None


def _qr_undo_one(ed: Editor, session: _QueryReplaceSession) -> bool:
    """Pop the most recent replacement and revert it.  Moves point to
    the (now-reverted) match and re-installs it as the current match
    so the user can re-decide.  Returns True if anything was undone.
    """
    if not session.replacements:
        return False
    r = session.replacements.pop()
    buf = ed.buffer
    # Delete the replacement text, insert the original.
    to_end_line, to_end_col = _qr_match_end(r.to_text, r.line, r.col)
    buf.delete_region(
        Mark(r.line, r.col),
        Mark(to_end_line, to_end_col),
    )
    buf.point.move_to(r.line, r.col)
    buf.insert_string(r.from_text)
    # Re-install the reverted match as the current one so the prompt
    # re-asks. Leave point at the match end, matching the on-deck
    # convention (Emacs prompts with point past the match).
    from_end_line, from_end_col = _qr_match_end(r.from_text, r.line, r.col)
    session.current_start_line = r.line
    session.current_start_col = r.col
    session.current_end_line = from_end_line
    session.current_end_col = from_end_col
    buf.point.move_to(from_end_line, from_end_col)
    session.replaced_count -= 1
    return True


def _qr_exit(
    ed: Editor,
    session: _QueryReplaceSession,
    *,
    message: str | None = None,
    restore_point: bool = False,
) -> None:
    """End the session.  Clears session state and highlight; optionally
    restores point to the session start and/or sets a message.
    """
    buf = ed.buffer
    if restore_point:
        buf.point.move_to(session.start_line, session.start_col)
    ed._query_replace_session = None
    ed.highlight_term = None
    ed.highlight_case_fold = False
    if message is not None:
        ed.message = message


def _qr_handle_key(ed: Editor, key: str) -> None:
    """Dispatch one keystroke while a query-replace session is active.

    Called by ``Editor.process_key`` via the routing hook that runs
    between describe-key and the ESC state machine (so ESC inside the
    session triggers keyboard-escape-quit, which cancels via
    ``_reset_transient_state``).  Must NOT be called while the session
    is ``paused_for_edit`` — that path belongs to the nested minibuffer.
    """
    session = ed._query_replace_session
    assert session is not None, "_qr_handle_key with no session"

    # Normalise key aliases per the spec table.
    # y/SPC = replace, n/DEL = skip, q/RET = exit, . = replace+exit,
    # ! = replace all, u = undo one, U = undo all, e = edit, C-g = cancel,
    # ? = help.  "Backspace" and "Delete" both alias to n.
    if key in (" ", "y"):
        _qr_key_replace(ed, session)
    elif key in ("n", "Backspace", "Delete"):
        _qr_key_skip(ed, session)
    elif key in ("Enter", "q"):
        _qr_key_exit(ed, session)
    elif key == ".":
        _qr_key_replace_once_and_exit(ed, session)
    elif key == "!":
        _qr_key_replace_all(ed, session)
    elif key == "u":
        _qr_key_undo_one(ed, session)
    elif key == "U":
        _qr_key_undo_all(ed, session)
    elif key == "e":
        _qr_key_edit_replacement(ed, session)
    elif key == "C-g":
        _qr_exit(ed, session, message="Quit", restore_point=True)
    elif key == "?":
        ed.message = (
            "y/SPC replace | n/DEL skip | q/RET exit | . once | ! all | "
            "u undo | U undo-all | e edit | C-g cancel"
        )
    else:
        ed.message = "Invalid key — press ? for help"


def _qr_key_replace(ed: Editor, session: _QueryReplaceSession) -> None:
    """y / SPC — replace the current match, find the next one."""
    if not session.has_current():
        _qr_exit(
            ed,
            session,
            message=_qr_replaced_message(session.replaced_count),
        )
        return
    _qr_replace_current(ed, session)
    _qr_advance_to_next_match(ed, session)
    if session.has_current():
        ed.message = _qr_prompt(session)
    else:
        _qr_exit(
            ed,
            session,
            message=_qr_replaced_message(session.replaced_count),
        )


def _qr_key_skip(ed: Editor, session: _QueryReplaceSession) -> None:
    """n / DEL / Backspace — skip the current match, find the next one."""
    if not session.has_current():
        _qr_exit(
            ed,
            session,
            message=_qr_replaced_message(session.replaced_count),
        )
        return
    # Advance point past the current match so find_forward doesn't
    # re-match it.
    buf = ed.buffer
    end_line = session.current_end_line
    end_col = session.current_end_col
    assert end_line is not None and end_col is not None
    # Point is already at the match end (on-deck convention); look past
    # it for the next match.
    buf.point.move_to(end_line, end_col)
    session.current_start_line = None
    session.current_start_col = None
    session.current_end_line = None
    session.current_end_col = None
    _qr_advance_to_next_match(ed, session)
    if session.has_current():
        ed.message = _qr_prompt(session)
    else:
        _qr_exit(
            ed,
            session,
            message=_qr_replaced_message(session.replaced_count),
        )


def _qr_key_exit(ed: Editor, session: _QueryReplaceSession) -> None:
    """q / RET — exit without replacing the current match."""
    _qr_exit(
        ed,
        session,
        message=_qr_replaced_message(session.replaced_count),
    )


def _qr_key_replace_once_and_exit(ed: Editor, session: _QueryReplaceSession) -> None:
    """. — replace the current match, then exit."""
    if session.has_current():
        _qr_replace_current(ed, session)
    _qr_exit(
        ed,
        session,
        message=_qr_replaced_message(session.replaced_count),
    )


def _qr_key_replace_all(ed: Editor, session: _QueryReplaceSession) -> None:
    """! — replace the current match and all remaining matches."""
    while session.has_current():
        _qr_replace_current(ed, session)
        _qr_advance_to_next_match(ed, session)
    _qr_exit(
        ed,
        session,
        message=_qr_replaced_message(session.replaced_count),
    )


def _qr_key_undo_one(ed: Editor, session: _QueryReplaceSession) -> None:
    """u — undo the most recent replacement, stay in session."""
    if not _qr_undo_one(ed, session):
        ed.message = "Nothing to undo"
        return
    ed.message = _qr_prompt(session)


def _qr_key_undo_all(ed: Editor, session: _QueryReplaceSession) -> None:
    """U — undo every replacement made in this session, then exit."""
    count = session.replaced_count
    while session.replacements:
        _qr_undo_one(ed, session)
    _qr_exit(
        ed,
        session,
        message=f"Undid all {count} replacement{'s' if count != 1 else ''}",
        restore_point=True,
    )


def _qr_key_edit_replacement(ed: Editor, session: _QueryReplaceSession) -> None:
    """e — edit the replacement string via a nested minibuffer.

    Pauses the session routing (via ``paused_for_edit``) so the
    minibuffer handles keystrokes normally.  The minibuffer's normal
    callback fires on Enter (updating ``to_text``); a patched
    ``process_key`` catches the cancel path (C-g / Escape) so the
    session resumes cleanly either way.
    """
    session.paused_for_edit = True

    def on_submit(new_text: str) -> None:
        session.to_text = new_text
        session.paused_for_edit = False
        ed.message = _qr_prompt(session)

    ed.start_minibuffer(
        f"Query replacing {session.from_text} with: ",
        on_submit,
        initial=session.to_text,
    )
    if ed.minibuffer is None:
        # Defensive — if the minibuffer couldn't start, resume the session.
        session.paused_for_edit = False
        return

    _qr_install_newline_handler(ed)

    original_process = ed.minibuffer.process_key

    def patched(key: str) -> bool:
        still_active = original_process(key)
        if not still_active and ed.minibuffer is not None and ed.minibuffer.cancelled:
            # Cancelled — resume the session without updating to_text.
            session.paused_for_edit = False
            ed.message = _qr_prompt(session)
        return still_active

    ed.minibuffer.process_key = patched  # type: ignore[method-assign]


def _qr_install_newline_handler(ed: Editor) -> None:
    """Install an ``M-Enter`` handler on the current minibuffer that
    inserts a literal newline into the input text.

    Mirrors the isearch convention (see 6l-3): C-j would be the Emacs
    binding, but ``shell/keys.py`` maps both \\r and \\n to ``"Enter"``,
    so we use M-Enter (unambiguous on every platform) to make
    multi-line search / replacement usable from the UI.
    """
    if ed.minibuffer is None:
        return
    mb = ed.minibuffer

    def insert_newline() -> None:
        if ed.minibuffer is None:
            return
        m = ed.minibuffer
        m.text = m.text[: m.cursor] + "\n" + m.text[m.cursor :]
        m.cursor += 1

    mb.key_handlers["M-Enter"] = insert_newline


# The " → " separator GNU Emacs shows between a default's from and to.
_QR_SEP = " → "


def _qr_push_history(history: list[str], text: str) -> None:
    """Prepend *text* to the query-replace *history*, skipping an empty
    string and a duplicate of the current front (the Emacs minibuffer add)."""
    if text and (not history or history[0] != text):
        history.insert(0, text)


def _replace_read_args(
    ed: Editor,
    prompt_prefix: str,
    on_ready: Callable[[str, str], None],
) -> None:
    """Read the (from, to) replacement pair through the minibuffer.

    The analogue of GNU Emacs's ``query-replace-read-args``, shared by
    ``query-replace`` and ``replace-string`` (both share the
    ``query-replace-defaults`` pair and the ``query-replace`` history in
    Emacs — verified against Emacs 29 via the parity harness): the
    opening prompt shows ``<prefix> (default FROM → TO): `` once a pair
    exists, submitting the from-input empty reuses the pair, and ``M-p``
    offers the combined ``FROM → TO`` entry ahead of the individual
    from/to history. The default is recorded as soon as the args are
    read (before any search), so even a no-match run updates it —
    matches Emacs.
    """
    history = ed._minibuffer_histories.setdefault("query-replace", [])
    defaults = ed._query_replace_defaults

    def set_defaults_and_go(from_text: str, to_text: str) -> None:
        ed._query_replace_defaults = (from_text, to_text)
        on_ready(from_text, to_text)

    def on_from_submitted(from_text: str) -> None:
        if not from_text:
            # Empty input reuses the default pair (skipping the with-prompt).
            if defaults is not None:
                set_defaults_and_go(*defaults)
            else:
                ed.message = ""
            return
        if _QR_SEP in from_text:
            # A combined "FROM → TO" entry recalled from the default history.
            # Its parts are already on the history (pushed when the default
            # was first entered) and the combined form is only a synthetic
            # view, so don't re-push — that would duplicate them. Just begin.
            f, t = from_text.split(_QR_SEP, 1)
            set_defaults_and_go(f, t)
            return
        _qr_push_history(history, from_text)

        def on_to_submitted(to_text: str) -> None:
            _qr_push_history(history, to_text)
            set_defaults_and_go(from_text, to_text)

        ed.start_minibuffer(
            f"{prompt_prefix} {from_text} with: ",
            on_to_submitted,
            history_list=list(history),
        )
        _qr_install_newline_handler(ed)

    if defaults is not None:
        prompt = f"{prompt_prefix} (default {defaults[0]}{_QR_SEP}{defaults[1]}): "
    else:
        prompt = f"{prompt_prefix}: "
    # M-p offers the combined default pair ahead of the individual history.
    nav = list(history)
    if defaults is not None:
        nav.insert(0, f"{defaults[0]}{_QR_SEP}{defaults[1]}")
    ed.start_minibuffer(prompt, on_from_submitted, history_list=nav)
    _qr_install_newline_handler(ed)


@defcommand(
    "query-replace",
    "Interactively replace occurrences of one string with another (M-%).",
)
def query_replace(ed: Editor, prefix: int | None) -> None:
    """Prompt for the search and replacement strings, then enter the
    capture-mode session that walks through each match.

    The arg reading (default pair, combined ``M-p`` history) is shared
    with ``replace-string`` — see ``_replace_read_args``.
    """
    buf = ed.buffer
    start_line = buf.point.line
    start_col = buf.point.col

    def begin_session(from_text: str, to_text: str) -> None:
        # Smart case-fold: fold iff case-fold-search is True AND from_text is
        # all lowercase (matches the isearch rule in 6l-3).
        global_fold = bool(ed.get_variable("case-fold-search"))
        case_fold = global_fold and from_text.islower()
        pos = buf.find_forward(from_text, start_line, start_col, case_fold=case_fold)
        if pos is None:
            ed.message = f"No matches for {from_text}"
            return
        session = _QueryReplaceSession(
            from_text=from_text,
            to_text=to_text,
            case_fold=case_fold,
            start_line=start_line,
            start_col=start_col,
        )
        # Install the first match: record start/end and leave point at the
        # match end (Emacs's on-deck convention).
        end_line, end_col = _qr_match_end(from_text, pos[0], pos[1])
        session.current_start_line = pos[0]
        session.current_start_col = pos[1]
        session.current_end_line = end_line
        session.current_end_col = end_col
        buf.point.move_to(end_line, end_col)
        # Install highlight overlay (reuses 6l-3 isearch machinery).
        ed.highlight_term = from_text
        ed.highlight_case_fold = case_fold
        # Activate the capture-mode session and show the prompt.
        ed._query_replace_session = session
        ed.message = _qr_prompt(session)

    _replace_read_args(ed, "Query replace", begin_session)


# ═══════════════════════════════════════════════════════════════════════
# Replace
# ═══════════════════════════════════════════════════════════════════════


@defcommand(
    "replace-string",
    "Replace occurrences of a string from point to end of buffer.",
)
def replace_string(ed: Editor, prefix: int | None) -> None:
    """Non-interactive bulk replace. Shares the ``query-replace-defaults``
    pair and the ``query-replace`` history with ``query-replace`` (GNU
    Emacs reads both commands' args through ``query-replace-read-args``)
    — see ``_replace_read_args``.
    """

    def do_replace(search: str, replacement: str) -> None:
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
        # Emacs reports the count even when it is zero ("Replaced 0
        # occurrences"), not a separate no-match message.
        ed.message = f"Replaced {count} occurrence{'s' if count != 1 else ''}"

    _replace_read_args(ed, "Replace string", do_replace)
