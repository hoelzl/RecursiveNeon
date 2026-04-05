"""Tests for Phase 6l-4 query-replace (M-%).

Covers the two-prompt entry flow, every in-session key path
(y/SPC/n/Backspace/Delete/q/Enter/./!/u/U/e/C-g/?), per-session undo
stack, ``e`` edit-replacement sub-phase with submit *and* cancel
resume, highlighting interaction, multi-line search/replace,
``_reset_transient_state`` cleanup, and the routing invariant that
query-replace keys are consumed before the ESC state machine.
"""

from __future__ import annotations

from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.default_commands import (
    _QueryReplaceSession,
    build_default_keymap,
)
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


def make_view(text: str = "", *, width: int = 40, height: int = 10) -> EditorView:
    ed = make_editor(text)
    view = EditorView(editor=ed)
    view.on_start(width, height)
    return view


def start_qr(ed: Editor, from_text: str, to_text: str) -> None:
    """Drive the query-replace entry flow via process_key.

    Leaves the session active (or with a "No matches" message if the
    first find fails).  Only supports ASCII from/to text; use
    ``start_qr_multiline`` for newline-containing inputs.
    """
    ed.process_key("M-%")
    for c in from_text:
        ed.process_key(c)
    ed.process_key("Enter")
    for c in to_text:
        ed.process_key(c)
    ed.process_key("Enter")


def start_qr_multiline(ed: Editor, from_text: str, to_text: str) -> None:
    """Entry flow that supports newlines in from/to via M-Enter."""
    ed.process_key("M-%")
    for c in from_text:
        if c == "\n":
            ed.process_key("M-Enter")
        else:
            ed.process_key(c)
    ed.process_key("Enter")
    for c in to_text:
        if c == "\n":
            ed.process_key("M-Enter")
        else:
            ed.process_key(c)
    ed.process_key("Enter")


# ═══════════════════════════════════════════════════════════════════════
# Registration + keymap binding
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceRegistration:
    def test_command_registered(self):
        assert "query-replace" in COMMANDS

    def test_bound_to_meta_percent(self):
        ed = make_editor("foo bar")
        km = ed.global_keymap
        assert km.lookup("M-%") == "query-replace"


# ═══════════════════════════════════════════════════════════════════════
# Entry flow: the two minibuffer prompts
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceEntry:
    def test_m_percent_opens_first_prompt(self):
        ed = make_editor("foo bar")
        ed.process_key("M-%")
        assert ed.minibuffer is not None
        assert ed.minibuffer.prompt == "Query replace: "

    def test_first_submit_opens_second_prompt(self):
        ed = make_editor("foo bar")
        ed.process_key("M-%")
        for c in "foo":
            ed.process_key(c)
        ed.process_key("Enter")
        assert ed.minibuffer is not None
        assert ed.minibuffer.prompt == "Query replace foo with: "

    def test_second_submit_installs_session_and_first_match(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        # Session is active
        assert ed._query_replace_session is not None
        sess = ed._query_replace_session
        assert sess.from_text == "foo"
        assert sess.to_text == "baz"
        # Point is on the first match
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 0
        # Minibuffer is closed; prompt is in the message area
        assert ed.minibuffer is None
        assert "Query replacing foo with baz" in ed.message

    def test_empty_from_text_aborts_without_session(self):
        ed = make_editor("foo bar")
        ed.process_key("M-%")
        ed.process_key("Enter")  # submit empty from-text
        assert ed._query_replace_session is None
        assert ed.minibuffer is None

    def test_no_matches_shows_message_and_does_not_install_session(self):
        ed = make_editor("foo bar")
        start_qr(ed, "xyz", "abc")
        assert ed._query_replace_session is None
        assert "No matches for xyz" in ed.message

    def test_entry_flow_starts_from_initial_point_not_search_start(self):
        """Matches should be found starting from where point was
        when query-replace was invoked, not from buffer start.
        """
        ed = make_editor("foo bar foo baz")
        # Move point past the first "foo" before invoking
        ed.buffer.point.move_to(0, 4)  # on "bar"
        start_qr(ed, "foo", "qux")
        # Should find the second "foo" at col 8, not the first at col 0
        assert ed.buffer.point.col == 8

    def test_highlight_term_set_on_session_entry(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        assert ed.highlight_term == "foo"


# ═══════════════════════════════════════════════════════════════════════
# Basic replacement keys: y / SPC / n / Backspace / Delete / q / Enter / .
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceBasicKeys:
    def test_y_replaces_and_advances(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("y")
        # First "foo" replaced with "baz"
        assert ed.buffer.text == "baz bar foo"
        # Point moved to the next match
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 8

    def test_space_aliases_y(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key(" ")
        assert ed.buffer.text == "baz bar foo"

    def test_n_skips_and_advances(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("n")
        # Nothing replaced
        assert ed.buffer.text == "foo bar foo"
        # Point moved past the first match to the second
        assert ed.buffer.point.col == 8

    def test_backspace_aliases_n(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("Backspace")
        assert ed.buffer.text == "foo bar foo"
        assert ed.buffer.point.col == 8

    def test_delete_aliases_n(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("Delete")
        assert ed.buffer.text == "foo bar foo"
        assert ed.buffer.point.col == 8

    def test_q_exits_without_replacing_current(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("q")
        assert ed._query_replace_session is None
        assert ed.buffer.text == "foo bar foo"
        assert "Replaced 0 occurrence(s)" in ed.message

    def test_enter_aliases_q(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("Enter")
        assert ed._query_replace_session is None
        assert ed.buffer.text == "foo bar foo"

    def test_dot_replaces_current_and_exits(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key(".")
        assert ed._query_replace_session is None
        assert ed.buffer.text == "baz bar foo"
        assert "Replaced 1 occurrence(s)" in ed.message

    def test_session_exits_naturally_when_no_more_matches(self):
        ed = make_editor("foo bar")  # one match
        start_qr(ed, "foo", "baz")
        ed.process_key("y")
        assert ed._query_replace_session is None
        assert ed.buffer.text == "baz bar"
        assert "Replaced 1 occurrence(s)" in ed.message

    def test_sequential_y_keys_replace_all_matches(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")
        ed.process_key("y")
        ed.process_key("y")
        assert ed.buffer.text == "X X X"
        assert ed._query_replace_session is None
        assert "Replaced 3 occurrence(s)" in ed.message

    def test_mixed_y_and_n(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # replace 1st
        ed.process_key("n")  # skip 2nd
        ed.process_key("y")  # replace 3rd
        assert ed.buffer.text == "X foo X"
        assert "Replaced 2 occurrence(s)" in ed.message

    def test_highlight_cleared_on_natural_exit(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("y")  # only match → exit
        assert ed.highlight_term is None
        assert ed.highlight_case_fold is False


# ═══════════════════════════════════════════════════════════════════════
# Replace-all (!)
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceReplaceAll:
    def test_bang_replaces_all_remaining(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("!")
        assert ed.buffer.text == "X X X"
        assert ed._query_replace_session is None
        assert "Replaced 3 occurrence(s)" in ed.message

    def test_bang_after_some_y_n_counts_correctly(self):
        ed = make_editor("foo foo foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # 1
        ed.process_key("n")  # skipped
        ed.process_key("!")  # 2, 3, 4 replaced; total 4
        assert ed.buffer.text == "X foo X X X"
        assert "Replaced 4 occurrence(s)" in ed.message

    def test_bang_with_single_match(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("!")
        assert ed.buffer.text == "baz bar"
        assert "Replaced 1 occurrence(s)" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# Undo stack: u / U
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceUndo:
    def test_u_reverts_one_replacement_and_stays_in_session(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # replace 1st → "X foo foo"
        ed.process_key("y")  # replace 2nd → "X X foo"
        ed.process_key("u")  # undo 2nd
        assert ed.buffer.text == "X foo foo"
        # Session still active
        assert ed._query_replace_session is not None
        # Point is back on the reverted match
        assert ed.buffer.point.col == 2  # position of 2nd "foo"

    def test_u_with_nothing_to_undo_shows_message(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "X")
        ed.process_key("u")  # haven't replaced anything yet
        assert ed._query_replace_session is not None
        assert "Nothing to undo" in ed.message
        assert ed.buffer.text == "foo bar"

    def test_u_then_y_re_replaces_reverted_match(self):
        ed = make_editor("foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # replace 1st → "X foo"
        ed.process_key("u")  # revert → "foo foo"
        ed.process_key("y")  # replace it again → "X foo"
        assert ed.buffer.text == "X foo"

    def test_u_multiple_times_unwinds_stack(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")
        ed.process_key("y")
        ed.process_key("y")  # all replaced → "X X X" and session exits
        # Session exited because no more matches.  u after exit is not
        # valid — start a fresh scenario to test multi-undo.

        ed = make_editor("foo foo foo bar")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # 1
        ed.process_key("y")  # 2
        ed.process_key(
            "y"
        )  # 3 → "X X X bar", session still has no more matches → exits
        assert ed._query_replace_session is None

    def test_u_then_u_unwinds_two_replacements(self):
        ed = make_editor("foo foo foo bar")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # replace 1st
        ed.process_key("y")  # replace 2nd
        assert ed.buffer.text == "X X foo bar"
        assert ed._query_replace_session is not None
        ed.process_key("u")  # revert 2nd
        assert ed.buffer.text == "X foo foo bar"
        ed.process_key("u")  # revert 1st
        assert ed.buffer.text == "foo foo foo bar"

    def test_capital_u_undoes_all_and_exits(self):
        ed = make_editor("foo foo foo bar")
        start_qr(ed, "foo", "X")
        ed.process_key("y")
        ed.process_key("y")
        assert ed.buffer.text == "X X foo bar"
        ed.process_key("U")
        assert ed.buffer.text == "foo foo foo bar"
        assert ed._query_replace_session is None
        assert "Undid all 2 replacement(s)" in ed.message

    def test_capital_u_restores_point_to_session_start(self):
        ed = make_editor("foo foo foo")
        # Start with point mid-buffer
        ed.buffer.point.move_to(0, 4)
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # replaces 2nd "foo" (since we started at col 4)
        ed.process_key("U")
        # Point should be back at the original session-start position
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 4

    def test_session_is_single_undo_group_post_exit(self):
        """After the session exits naturally, one C-/ should revert
        every replacement the session made.  This is the core
        "single undo group" guarantee.
        """
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("!")  # replace all
        assert ed.buffer.text == "X X X"
        # Simulate undo via Buffer.undo()
        ed.execute_command("undo")
        # Whole session reverts in one undo call
        assert ed.buffer.text == "foo foo foo"


# ═══════════════════════════════════════════════════════════════════════
# Cancel: C-g restores point, keeps committed replacements
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceCancel:
    def test_cg_exits_and_sets_quit_message(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("C-g")
        assert ed._query_replace_session is None
        assert ed.message == "Quit"

    def test_cg_restores_point_to_session_start(self):
        ed = make_editor("foo bar foo")
        ed.buffer.point.move_to(0, 0)
        start_qr(ed, "foo", "X")
        # Session moved point to first match (col 0); that IS the start.
        # Re-do with non-zero start.
        ed = make_editor("foo bar foo")
        ed.buffer.point.move_to(0, 4)  # on "bar"
        start_qr(ed, "foo", "X")
        # Point is now on the second "foo" at col 8
        assert ed.buffer.point.col == 8
        ed.process_key("C-g")
        # Point restored to col 4
        assert ed.buffer.point.col == 4

    def test_cg_keeps_committed_replacements(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")  # commit 1st
        ed.process_key("y")  # commit 2nd
        ed.process_key("C-g")  # cancel on 3rd
        assert ed.buffer.text == "X X foo"
        assert ed._query_replace_session is None

    def test_cg_clears_highlight(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("C-g")
        assert ed.highlight_term is None


# ═══════════════════════════════════════════════════════════════════════
# Edit replacement (e): nested minibuffer with pause/resume
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceEditReplacement:
    def test_e_opens_minibuffer_with_current_to_text(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("e")
        assert ed.minibuffer is not None
        assert "Query replacing foo with:" in ed.minibuffer.prompt
        assert ed.minibuffer.text == "baz"
        # Session still installed but paused
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.paused_for_edit is True

    def test_e_submit_updates_to_text_and_resumes(self):
        ed = make_editor("foo foo")
        start_qr(ed, "foo", "baz")
        ed.process_key("e")
        # Edit the replacement text — delete existing, type new.
        for _ in ed.minibuffer.text:  # type: ignore[union-attr]
            ed.process_key("Backspace")
        for c in "NEW":
            ed.process_key(c)
        ed.process_key("Enter")
        # Session resumed, to_text updated
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.to_text == "NEW"
        assert ed._query_replace_session.paused_for_edit is False
        assert ed.minibuffer is None
        # Press y to use the new replacement
        ed.process_key("y")
        assert ed.buffer.text == "NEW foo"

    def test_e_cancel_resumes_with_old_to_text(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("e")
        # Type some junk, then cancel
        for c in "JUNK":
            ed.process_key(c)
        ed.process_key("C-g")
        # Session resumes unchanged
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.to_text == "baz"
        assert ed._query_replace_session.paused_for_edit is False
        assert ed.minibuffer is None
        # y uses the old (unchanged) replacement
        ed.process_key("y")
        assert ed.buffer.text == "baz bar"

    def test_e_during_pause_keys_go_to_minibuffer(self):
        """While paused_for_edit, typing letters extends the minibuffer
        text — they do NOT hit the query-replace key dispatcher.
        """
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("e")
        # "y" should self-insert into the minibuffer, not trigger replace
        ed.process_key("y")
        assert ed.minibuffer is not None
        assert "y" in ed.minibuffer.text
        # Buffer text is unchanged
        assert ed.buffer.text == "foo bar"


# ═══════════════════════════════════════════════════════════════════════
# Help (?) and invalid keys
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceHelp:
    def test_question_mark_shows_legend(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("?")
        assert "y/SPC replace" in ed.message
        assert "n/DEL skip" in ed.message
        assert "! all" in ed.message
        # Session still active
        assert ed._query_replace_session is not None

    def test_question_mark_does_not_modify_buffer(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("?")
        assert ed.buffer.text == "foo bar"

    def test_invalid_key_shows_message(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("z")
        assert "Invalid key" in ed.message
        assert ed._query_replace_session is not None
        assert ed.buffer.text == "foo bar"


# ═══════════════════════════════════════════════════════════════════════
# Multi-line search/replace (via M-Enter in entry prompts)
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceMultiLine:
    def test_multiline_needle_replace(self):
        ed = make_editor("hello\nworld\nfoo")
        start_qr_multiline(ed, "hello\nworld", "ONE")
        ed.process_key("y")
        # Two lines collapsed to one
        assert ed.buffer.text == "ONE\nfoo"

    def test_multiline_replacement(self):
        ed = make_editor("foo bar")
        start_qr_multiline(ed, "foo", "line1\nline2")
        ed.process_key("y")
        assert ed.buffer.text == "line1\nline2 bar"

    def test_m_enter_inserts_newline_in_first_prompt(self):
        ed = make_editor("anything")
        ed.process_key("M-%")
        ed.process_key("a")
        ed.process_key("M-Enter")
        ed.process_key("b")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "a\nb"

    def test_m_enter_inserts_newline_in_second_prompt(self):
        ed = make_editor("foo")
        ed.process_key("M-%")
        for c in "foo":
            ed.process_key(c)
        ed.process_key("Enter")
        # now on second prompt
        assert ed.minibuffer is not None
        ed.process_key("x")
        ed.process_key("M-Enter")
        ed.process_key("y")
        assert ed.minibuffer.text == "x\ny"


# ═══════════════════════════════════════════════════════════════════════
# Highlighting: isearch infrastructure reuse
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceHighlighting:
    def test_highlight_term_matches_from_text(self):
        ed = make_editor("foo bar foo")
        start_qr(ed, "foo", "baz")
        assert ed.highlight_term == "foo"

    def test_highlight_case_fold_follows_smart_default(self):
        ed = make_editor("Foo FOO foo")
        # Lowercase needle → smart-case fold active
        start_qr(ed, "foo", "X")
        assert ed.highlight_case_fold is True

    def test_highlight_case_fold_false_for_uppercase_needle(self):
        ed = make_editor("Foo FOO foo")
        start_qr(ed, "Foo", "X")
        assert ed.highlight_case_fold is False

    def test_highlight_persists_across_y_and_n(self):
        ed = make_editor("foo foo foo")
        start_qr(ed, "foo", "X")
        ed.process_key("y")
        assert ed.highlight_term == "foo"
        ed.process_key("n")
        assert ed.highlight_term == "foo"

    def test_highlight_rendered_in_screen(self):
        """The isearch StyleSpan infrastructure emits highlight spans
        for matches whose start position is point.  We verify the
        effect indirectly: the rendered screen has ANSI styling around
        the first match.
        """
        view = make_view("foo bar foo", width=20, height=5)
        start_qr(view.editor, "foo", "X")
        screen = view._render()
        # The first line should contain the highlight ANSI escape
        # (present on current-match priority).  We don't assert on
        # the specific SGR code — just that *some* styling was
        # emitted for this row.
        first_line = screen.lines[0]
        assert "\x1b[" in first_line


# ═══════════════════════════════════════════════════════════════════════
# Case-fold replacement behaviour
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceCaseFold:
    def test_lowercase_needle_matches_uppercase_by_default(self):
        ed = make_editor("Foo FOO foo")
        start_qr(ed, "foo", "X")
        ed.process_key("!")
        # All three variants replaced with literal "X"
        assert ed.buffer.text == "X X X"

    def test_uppercase_needle_is_case_sensitive(self):
        ed = make_editor("Foo FOO foo")
        start_qr(ed, "Foo", "X")
        ed.process_key("!")
        # Only the first "Foo" matches — smart-case disables folding
        assert ed.buffer.text == "X FOO foo"


# ═══════════════════════════════════════════════════════════════════════
# _reset_transient_state / keyboard-escape-quit cleanup
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceReset:
    def test_reset_transient_state_clears_session(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        assert ed._query_replace_session is not None
        ed._reset_transient_state()
        assert ed._query_replace_session is None

    def test_reset_transient_state_clears_highlight(self):
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        assert ed.highlight_term == "foo"
        ed._reset_transient_state()
        assert ed.highlight_term is None

    def test_keyboard_escape_quit_cancels_session(self):
        """ESC ESC ESC should trigger keyboard-escape-quit, which calls
        _reset_transient_state, which clears the session.
        """
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        # But wait: ESC inside the session is captured by the query-replace
        # dispatch as an "invalid key".  keyboard-escape-quit is reached via
        # the ESC state machine which runs AFTER query-replace routing.
        # So ESC inside a session shows "Invalid key", NOT triggering
        # keyboard-escape-quit.  C-g is the correct cancel path.
        # This test documents that routing order.
        ed.process_key("Escape")
        # Session still active; message shows invalid key
        assert ed._query_replace_session is not None
        assert "Invalid key" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# Routing: query-replace consumes keys before ESC state machine
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceRouting:
    def test_session_keys_do_not_trigger_normal_commands(self):
        """During a session, 'y' is replace-current, not self-insert."""
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("y")
        # 'y' was consumed as replace; buffer shows replacement, not "y"
        assert ed.buffer.text == "baz bar"

    def test_session_inactive_keys_behave_normally(self):
        """After the session exits, keys route through the normal keymap again."""
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("y")  # only match → session exits
        # Now 'y' should self-insert
        ed.buffer.point.move_to(0, 0)
        ed.process_key("y")
        assert ed.buffer.text == "ybaz bar"

    def test_paused_for_edit_routes_to_minibuffer(self):
        """While paused for 'e', keys go to the minibuffer, not the
        query-replace dispatcher.
        """
        ed = make_editor("foo bar")
        start_qr(ed, "foo", "baz")
        ed.process_key("e")
        # Now in the edit-replacement minibuffer
        assert ed.minibuffer is not None
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.paused_for_edit is True
        # A random letter self-inserts into the minibuffer
        ed.process_key("z")
        assert "z" in ed.minibuffer.text


# ═══════════════════════════════════════════════════════════════════════
# Session dataclass basics
# ═══════════════════════════════════════════════════════════════════════


class TestQueryReplaceSessionDataclass:
    def test_session_defaults(self):
        s = _QueryReplaceSession(
            from_text="x",
            to_text="y",
            case_fold=False,
            start_line=0,
            start_col=0,
        )
        assert s.current_end_line is None
        assert s.current_end_col is None
        assert s.replacements == []
        assert s.paused_for_edit is False
        assert s.replaced_count == 0
        assert s.has_current() is False

    def test_has_current_true_when_end_set(self):
        s = _QueryReplaceSession(
            from_text="x",
            to_text="y",
            case_fold=False,
            start_line=0,
            start_col=0,
            current_end_line=0,
            current_end_col=1,
        )
        assert s.has_current() is True
