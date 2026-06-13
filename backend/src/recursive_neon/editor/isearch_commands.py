"""Incremental search commands (C-s / C-r) — split out of
``default_commands`` along the isearch seam; importing this module
registers the commands (``default_commands`` does so).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from recursive_neon.editor.commands import defcommand

if TYPE_CHECKING:
    from recursive_neon.editor.editor import Editor
from recursive_neon.editor.modes import MODES

# ═══════════════════════════════════════════════════════════════════════
# Incremental search
#
# Two commands live in this section:
#
# - ``search-forward`` / ``search-backward`` (M-x only): the legacy
#   incremental-search behaviour — no highlighting, no wrap-around.
#   Useful as a simpler non-interactive alternative.
# - ``isearch-forward`` / ``isearch-backward`` (C-s / C-r): the full
#   incremental search with match highlighting, wrap-around, state-stack
#   backspace, M-c case-fold toggle, and M-Enter for inserting a
#   literal newline into the search string (used for multi-line search).
#
# Deviation from Emacs: Emacs uses C-j for newline insertion in isearch.
# Our key input layer (``shell/keys.py``) maps both CR and LF to
# ``"Enter"``, so C-j and Enter are indistinguishable.  We use M-Enter
# (Alt+Enter) instead — unambiguous on every platform.
# ═══════════════════════════════════════════════════════════════════════


@defcommand(
    "search-forward",
    "Non-interactive forward search (legacy behaviour, via M-x).",
)
def search_forward(ed: Editor, prefix: int | None) -> None:
    _start_legacy_search(ed, forward=True)


@defcommand(
    "search-backward",
    "Non-interactive backward search (legacy behaviour, via M-x).",
)
def search_backward(ed: Editor, prefix: int | None) -> None:
    _start_legacy_search(ed, forward=False)


def _start_legacy_search(ed: Editor, *, forward: bool) -> None:
    """Legacy incremental-search behaviour (pre-Phase 6l-3).

    Retained for ``M-x search-forward`` / ``search-backward`` — no
    highlighting, no wrap-around.  For the full isearch experience,
    use ``C-s`` / ``C-r`` (``isearch-forward`` / ``isearch-backward``).
    """
    buf = ed.buffer
    start_line = buf.point.line
    start_col = buf.point.col
    direction = [forward]

    def on_change(text: str) -> None:
        if not text:
            buf.point.move_to(start_line, start_col)
            ed.message = ""
            return
        _do_search(text, from_current=False)

    def _do_search(text: str, *, from_current: bool) -> None:
        if direction[0]:
            from_col = buf.point.col + (1 if from_current else 0)
            pos = buf.find_forward(text, buf.point.line, from_col)
        else:
            from_col = buf.point.col if from_current else buf.point.col + 1
            pos = buf.find_backward(text, buf.point.line, from_col)
        if pos is not None:
            buf.point.move_to(pos[0], pos[1])
            label = "Search" if direction[0] else "Search backward"
            ed.message = ""
            if ed.minibuffer:
                ed.minibuffer.prompt = f"{label}: "
        else:
            label = "Failing Search" if direction[0] else "Failing Search backward"
            if ed.minibuffer:
                ed.minibuffer.prompt = f"{label}: "

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

    prompt_prefix = "Search" if forward else "Search backward"
    ed.start_minibuffer(
        f"{prompt_prefix}: ",
        on_confirm,
        on_change=on_change,
    )
    if ed.minibuffer:
        ed.minibuffer.key_handlers["C-s"] = repeat_forward
        ed.minibuffer.key_handlers["C-r"] = repeat_backward
        original_process = ed.minibuffer.process_key

        def patched_process(key: str) -> bool:
            if key == "C-g" or key == "Escape":
                on_cancel()
                ed.minibuffer._cancelled = True  # type: ignore[union-attr]
                return False
            return original_process(key)

        ed.minibuffer.process_key = patched_process  # type: ignore[method-assign]


@dataclass
class _IsearchState:
    """One snapshot of the isearch session, pushed on every successful op.

    Backspace pops one state.  Stack is initialised with the entry state
    (text="", at the original point) so backspace at an empty search
    still has somewhere to go.
    """

    text: str
    line: int
    col: int
    direction: bool  # True = forward
    wrapped: bool = False
    failing: bool = False


@defcommand("isearch-forward", "Incremental search forward (C-s).")
def isearch_forward(ed: Editor, prefix: int | None) -> None:
    _start_isearch(ed, forward=True)


@defcommand("isearch-backward", "Incremental search backward (C-r).")
def isearch_backward(ed: Editor, prefix: int | None) -> None:
    _start_isearch(ed, forward=False)


def _activate_isearch_mode(ed: Editor) -> None:
    """Turn on ``isearch-mode`` as a minor mode for the current buffer."""

    mode = MODES.get("isearch-mode")
    if mode is None:
        return
    minor = ed.buffer.minor_modes
    if mode not in minor:
        minor.append(mode)


def _deactivate_isearch_mode(ed: Editor) -> None:
    """Drop ``isearch-mode`` from the current buffer's minor-mode list."""

    mode = MODES.get("isearch-mode")
    if mode is None:
        return
    minor = ed.buffer.minor_modes
    if mode in minor:
        minor.remove(mode)


def _isearch_set_point(
    buf, match_line: int, match_col: int, text: str, *, forward: bool
) -> None:
    """Place point relative to a match the way GNU Emacs's isearch does.

    Forward search leaves point *after* the match (so the user can
    immediately type or perform a region op against just-found text).
    Backward search leaves point at the start of the match. ``text`` is
    the search string; for multi-line strings (M-RET in isearch),
    end-of-match is computed across the embedded newlines.
    """
    if not forward:
        buf.point.move_to(match_line, match_col)
        return
    if "\n" in text:
        parts = text.split("\n")
        end_line = match_line + len(parts) - 1
        end_col = len(parts[-1])
    else:
        end_line = match_line
        end_col = match_col + len(text)
    buf.point.move_to(end_line, end_col)


def _start_isearch(ed: Editor, *, forward: bool) -> None:
    """True incremental search with highlighting, wrap, M-c, M-Enter.

    Session state:
      - ``state_stack``: list of ``_IsearchState`` snapshots.  Every
        successful keystroke (character add, repeat, wrap) pushes one
        state.  Backspace pops.
      - ``explicit_case_fold``: user override via M-c.  ``None`` means
        smart-case (fold iff the search text is all lowercase AND
        ``case-fold-search`` is true).
    """
    buf = ed.buffer
    start_line = buf.point.line
    start_col = buf.point.col

    state_stack: list[_IsearchState] = [
        _IsearchState(
            text="",
            line=start_line,
            col=start_col,
            direction=forward,
            wrapped=False,
            failing=False,
        )
    ]
    explicit_case_fold: list[bool | None] = [None]

    def _effective_case_fold(text: str) -> bool:
        """Resolve smart-case / explicit override to a single bool."""
        if explicit_case_fold[0] is not None:
            return explicit_case_fold[0]
        # Smart default: fold only when text is all lowercase AND the
        # global ``case-fold-search`` variable is True.
        global_fold = bool(ed.get_variable("case-fold-search"))
        return global_fold and text.islower()

    def _current() -> _IsearchState:
        return state_stack[-1]

    def _update_prompt() -> None:
        if ed.minibuffer is None:
            return
        s = _current()
        parts: list[str] = []
        if s.wrapped:
            parts.append("Wrapped ")
        elif s.failing:
            parts.append("Failing ")
        # GNU Emacs spells out the case state when folding is off (either
        # because the user explicitly disabled it with M-c, or because
        # smart-case noticed an uppercase character in the search text):
        # the prompt reads ``Failing case-sensitive I-search: ...``.
        effective_fold = _effective_case_fold(s.text)
        if not effective_fold:
            parts.append("case-sensitive ")
        parts.append("I-search" if s.direction else "I-search backward")
        ed.minibuffer.prompt = "".join(parts) + ": "

    def _update_highlight() -> None:
        """Sync ed.highlight_term / highlight_case_fold with current state."""
        s = _current()
        if s.text:
            ed.highlight_term = s.text
            ed.highlight_case_fold = _effective_case_fold(s.text)
        else:
            ed.highlight_term = None
            ed.highlight_case_fold = False

    def on_change(text: str) -> None:
        """Called on every self-insert (and would-be Backspace notify).

        Searches from the *previous* match position (the current top of
        the stack), extending the search string by one character.
        """
        if not text:
            # Empty: restore to origin, collapse stack to just the root.
            buf.point.move_to(start_line, start_col)
            state_stack.clear()
            state_stack.append(
                _IsearchState(
                    text="",
                    line=start_line,
                    col=start_col,
                    direction=forward,
                    wrapped=False,
                    failing=False,
                )
            )
            _update_highlight()
            _update_prompt()
            return

        prev = _current()
        case_fold = _effective_case_fold(text)
        direction = prev.direction

        # Incremental extension: search from the start of the previous
        # match (prev.line, prev.col).  This lets the point "stay in
        # place" while the match just grows by one character.
        if prev.failing:
            # Previous state was failing — search from the origin (or
            # from prev's position, same thing for a failed match).
            from_line, from_col = prev.line, prev.col
        else:
            from_line, from_col = prev.line, prev.col

        if direction:
            pos = buf.find_forward(text, from_line, from_col, case_fold=case_fold)
        else:
            # Backward: include prev.col as a valid start position.
            pos = buf.find_backward(text, from_line, from_col + 1, case_fold=case_fold)

        if pos is not None:
            _isearch_set_point(buf, pos[0], pos[1], text, forward=direction)
            state_stack.append(
                _IsearchState(
                    text=text,
                    line=pos[0],
                    col=pos[1],
                    direction=direction,
                    wrapped=False,
                    failing=False,
                )
            )
        else:
            # Stay where we are, mark failing.
            state_stack.append(
                _IsearchState(
                    text=text,
                    line=prev.line,
                    col=prev.col,
                    direction=direction,
                    wrapped=False,
                    failing=True,
                )
            )
        _update_highlight()
        _update_prompt()

    def _repeat(direction: bool) -> None:
        if ed.minibuffer is None:
            return
        text = ed.minibuffer.text
        if not text:
            return
        prev = _current()
        case_fold = _effective_case_fold(text)

        if prev.failing and prev.direction == direction:
            # Wrap: start over from the opposite end of the buffer.
            if direction:
                pos = buf.find_forward(text, 0, 0, case_fold=case_fold)
            else:
                last_line = buf.line_count - 1
                last_col = len(buf.lines[last_line]) + 1
                pos = buf.find_backward(text, last_line, last_col, case_fold=case_fold)
            if pos is not None:
                _isearch_set_point(buf, pos[0], pos[1], text, forward=direction)
                state_stack.append(
                    _IsearchState(
                        text=text,
                        line=pos[0],
                        col=pos[1],
                        direction=direction,
                        wrapped=True,
                        failing=False,
                    )
                )
            else:
                state_stack.append(
                    _IsearchState(
                        text=text,
                        line=prev.line,
                        col=prev.col,
                        direction=direction,
                        wrapped=True,
                        failing=True,
                    )
                )
        else:
            # Normal repeat: advance past the current match.
            if direction:
                from_col = prev.col + 1
                pos = buf.find_forward(text, prev.line, from_col, case_fold=case_fold)
            else:
                pos = buf.find_backward(text, prev.line, prev.col, case_fold=case_fold)
            if pos is not None:
                _isearch_set_point(buf, pos[0], pos[1], text, forward=direction)
                state_stack.append(
                    _IsearchState(
                        text=text,
                        line=pos[0],
                        col=pos[1],
                        direction=direction,
                        wrapped=False,
                        failing=False,
                    )
                )
            else:
                state_stack.append(
                    _IsearchState(
                        text=text,
                        line=prev.line,
                        col=prev.col,
                        direction=direction,
                        wrapped=False,
                        failing=True,
                    )
                )
        _update_highlight()
        _update_prompt()

    def repeat_forward() -> None:
        _repeat(True)

    def repeat_backward() -> None:
        _repeat(False)

    def toggle_case_fold() -> None:
        """M-c: flip the case-fold flag for this session."""
        current = _effective_case_fold(_current().text)
        explicit_case_fold[0] = not current
        _update_highlight()
        _update_prompt()

    def insert_newline() -> None:
        """M-Enter: insert a literal newline into the search string.

        Triggers the minibuffer's on_change hook to re-run the search
        with the new multi-line term.  C-j would be the Emacs binding,
        but keys.py maps both \\r and \\n to "Enter", so we use M-Enter
        (unambiguous) instead.
        """
        if ed.minibuffer is None:
            return
        mb = ed.minibuffer
        mb.text = mb.text[: mb.cursor] + "\n" + mb.text[mb.cursor :]
        mb.cursor += 1
        mb._notify_change()

    def on_confirm(text: str) -> None:
        # Exiting normally — clear highlight, leave point at the match.
        ed.highlight_term = None
        ed.highlight_case_fold = False
        _deactivate_isearch_mode(ed)
        # GNU Emacs pushes an *inactive* mark at the original search
        # start so ``C-x C-x`` can return to where the search began, and
        # announces it via the echo area.
        if buf.point.line != start_line or buf.point.col != start_col:
            buf.push_mark(start_line, start_col)
            ed.message = "Mark saved where search started"

    def on_cancel() -> None:
        # C-g / Escape: restore original point, clear highlight.
        buf.point.move_to(start_line, start_col)
        ed.highlight_term = None
        ed.highlight_case_fold = False
        _deactivate_isearch_mode(ed)

    def on_backspace() -> None:
        """Pop one state off the stack, restore text + position."""
        if len(state_stack) <= 1:
            # At the origin — clear search text and reset to origin.
            if ed.minibuffer is not None:
                ed.minibuffer.text = ""
                ed.minibuffer.cursor = 0
            buf.point.move_to(start_line, start_col)
            ed.highlight_term = None
            ed.highlight_case_fold = False
            _update_prompt()
            return
        state_stack.pop()
        s = _current()
        # The state's line/col is the match-start; restore the visible
        # point to the corresponding match end (forward) or start
        # (backward), matching what the original step produced.
        _isearch_set_point(buf, s.line, s.col, s.text, forward=s.direction)
        if ed.minibuffer is not None:
            ed.minibuffer.text = s.text
            ed.minibuffer.cursor = len(s.text)
        _update_highlight()
        _update_prompt()

    prompt_prefix = "I-search" if forward else "I-search backward"
    # Activate ``isearch-mode`` as a minor mode so the modeline reads
    # ``(... Isearch)`` while the search is alive — matches Emacs.
    _activate_isearch_mode(ed)
    ed.start_minibuffer(
        f"{prompt_prefix}: ",
        on_confirm,
        on_change=on_change,
    )
    if ed.minibuffer is not None:
        ed.minibuffer.key_handlers["C-s"] = repeat_forward
        ed.minibuffer.key_handlers["C-r"] = repeat_backward
        ed.minibuffer.key_handlers["M-c"] = toggle_case_fold
        ed.minibuffer.key_handlers["M-Enter"] = insert_newline

        # Patched process_key: intercept C-g/Escape (cancel with point
        # restore) and Backspace (state-stack pop).  Everything else
        # falls through to the minibuffer's default handling, preserving
        # self-insert on_change and unknown-key exit-and-replay.
        original_process = ed.minibuffer.process_key

        def patched_process(key: str) -> bool:
            if key == "C-g" or key == "Escape":
                on_cancel()
                ed.minibuffer._cancelled = True  # type: ignore[union-attr]
                return False
            if key == "Backspace":
                on_backspace()
                return True
            return original_process(key)

        ed.minibuffer.process_key = patched_process  # type: ignore[method-assign]
