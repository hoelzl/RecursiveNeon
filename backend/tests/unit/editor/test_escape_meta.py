"""
Tests for Phase 6l-2: ESC-as-Meta + ``keyboard-escape-quit``.

Two tightly related features:

1. **ESC-as-Meta state machine** — a bare ``Escape`` keystroke acts as
   the Meta prefix.  The next non-ESC key is rewritten as ``M-<key>``
   before keymap lookup (e.g., ``ESC f`` runs ``forward-word``).  This
   complements the platform-level ESC+key detection in ``keys.py``,
   handling the slow-ESC case when the user deliberately presses ESC
   and then a follow-up key.

2. **``keyboard-escape-quit``** — new command bound to ``ESC ESC ESC``
   via the state machine's three-escape terminal transition.  Does
   everything ``keyboard-quit`` does *plus* dismisses the ``*Help*``
   buffer and forces the minibuffer shut.

The state machine runs at the very top of ``Editor.process_key``,
before minibuffer routing and C-g handling but **after** describe-key
capture (which consumes any key, ESC included, to match Emacs).
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    """Create an editor with the default keymap and one buffer."""
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


# ═══════════════════════════════════════════════════════════════════════
# ESC-as-Meta basics: ESC <key> === M-<key>
# ═══════════════════════════════════════════════════════════════════════


class TestEscAsMeta:
    def test_esc_then_f_runs_forward_word(self):
        """ESC f is equivalent to M-f (forward-word)."""
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("Escape")
        assert ed._meta_pending is True
        ed.process_key("f")
        assert ed._meta_pending is False
        assert ed.buffer.point.col == 5  # moved over "hello"

    def test_esc_then_b_runs_backward_word(self):
        """ESC b is equivalent to M-b (backward-word)."""
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 11)  # end of "world"
        ed.process_key("Escape")
        ed.process_key("b")
        assert ed.buffer.point.col == 6  # start of "world"

    def test_esc_then_x_opens_execute_extended_command(self):
        """ESC x is equivalent to M-x (execute-extended-command)."""
        ed = make_editor()
        ed.process_key("Escape")
        ed.process_key("x")
        assert ed.minibuffer is not None
        assert "M-x" in ed.minibuffer.prompt

    def test_esc_then_ctrl_key_becomes_c_m(self):
        """ESC C-v is equivalent to C-M-v (scroll-other-window)."""
        ed = make_editor()
        ed.process_key("Escape")
        ed.process_key("C-v")
        # scroll-other-window with a single window → "Only one window"
        # (We just need to confirm the rewrite happened and dispatched
        # without error; the message is the observable side effect.)
        assert ed._meta_pending is False
        assert ed.message == "Only one window"

    def test_esc_then_gt_runs_end_of_buffer(self):
        """ESC > is equivalent to M-> (end-of-buffer)."""
        ed = make_editor("first\nsecond\nthird")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("Escape")
        ed.process_key(">")
        assert ed.buffer.point.line == 2  # at "third"

    def test_esc_then_lt_runs_beginning_of_buffer(self):
        """ESC < is equivalent to M-< (beginning-of-buffer)."""
        ed = make_editor("first\nsecond\nthird")
        ed.buffer.end_of_buffer()
        ed.process_key("Escape")
        ed.process_key("<")
        assert ed.buffer.point.line == 0
        assert ed.buffer.point.col == 0

    def test_meta_prefixed_key_passes_through(self):
        """A key already in M-<…> form is not double-prefixed."""
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 0)
        # Simulate the fast-ESC path where keys.py already produced M-f.
        ed.process_key("Escape")
        ed.process_key("M-f")  # should dispatch as M-f, not M-M-f
        assert ed.buffer.point.col == 5

    def test_meta_pending_cleared_after_dispatch(self):
        """After ESC-<key> dispatches, the state machine is idle again."""
        ed = make_editor("hello")
        ed.process_key("Escape")
        ed.process_key("f")
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False
        # Next plain key should NOT be Meta-prefixed
        ed.process_key("b")  # self-insert "b"
        assert "b" in ed.buffer.text


# ═══════════════════════════════════════════════════════════════════════
# ESC ESC ESC: keyboard-escape-quit
# ═══════════════════════════════════════════════════════════════════════


class TestEscapeQuitNormalMode:
    def test_three_escapes_triggers_keyboard_escape_quit(self):
        """ESC ESC ESC at top level runs keyboard-escape-quit."""
        ed = make_editor("hello")
        ed.process_key("Escape")
        assert ed._meta_pending is True
        ed.process_key("Escape")
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is True
        ed.process_key("Escape")
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False
        assert ed.message == "Quit"

    def test_keyboard_escape_quit_clears_region(self):
        """Three ESCs clear an active region/mark."""
        ed = make_editor("hello")
        ed.process_key("C-space")  # set mark
        assert ed.buffer.mark is not None
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.buffer.mark is None
        assert ed.message == "Quit"

    def test_keyboard_escape_quit_clears_prefix_arg(self):
        """Three ESCs clear an in-progress C-u prefix argument."""
        ed = make_editor()
        ed.process_key("C-u")
        ed.process_key("5")
        assert ed._prefix_arg == 5
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed._prefix_arg is None
        assert ed._building_prefix is False

    def test_keyboard_escape_quit_clears_pending_prefix_keymap(self):
        """Three ESCs cancel a pending C-x prefix keymap."""
        ed = make_editor()
        ed.process_key("C-x")
        assert ed._pending_keymap is not None
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed._pending_keymap is None
        assert ed._prefix_keys == ""


# ═══════════════════════════════════════════════════════════════════════
# ESC ESC ESC from the minibuffer
# ═══════════════════════════════════════════════════════════════════════


class TestEscapeQuitMinibuffer:
    def test_three_escapes_dismiss_minibuffer(self):
        """ESC ESC ESC from inside M-x dismisses the minibuffer."""
        ed = make_editor()
        ed.process_key("M-x")
        assert ed.minibuffer is not None
        ed.process_key("Escape")
        # Minibuffer still active after first ESC (it's meta-pending)
        assert ed.minibuffer is not None
        assert ed._meta_pending is True
        ed.process_key("Escape")
        # Still active after second ESC (escape-quit-pending)
        assert ed.minibuffer is not None
        assert ed._escape_quit_pending is True
        ed.process_key("Escape")
        # Third ESC → keyboard-escape-quit dismisses the minibuffer
        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_three_escapes_dismiss_find_file_minibuffer(self):
        """ESC ESC ESC works from the C-x C-f find-file prompt."""
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("C-f")
        assert ed.minibuffer is not None
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_three_escapes_with_typed_text_still_cancel(self):
        """ESC ESC ESC dismisses the minibuffer even after typing input."""
        ed = make_editor()
        ed.process_key("M-x")
        for ch in "forw":
            ed.process_key(ch)
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "forw"
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_esc_followed_by_printable_in_minibuffer_stays_open(self):
        """A single ESC in the minibuffer followed by an unbound key
        leaves the minibuffer open and silently ignores the M-<key>.
        """
        ed = make_editor()
        ed.process_key("M-x")
        ed.process_key("Escape")
        assert ed._meta_pending is True
        ed.process_key("f")  # rewritten as M-f → no minibuffer binding
        # Minibuffer stays open; state machine cleared; "f" not inserted
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == ""
        assert ed._meta_pending is False

    def test_minibuffer_unit_level_escape_still_cancels(self):
        """The Minibuffer class's own Escape handling is preserved for
        direct-invocation callers (the unit-level contract).  This is
        the "terminal case" the Phase 6l-2 handover refers to.
        """
        from recursive_neon.editor.minibuffer import Minibuffer

        mb = Minibuffer("prompt: ", lambda s: None)
        active = mb.process_key("Escape")
        assert not active
        assert mb.cancelled


# ═══════════════════════════════════════════════════════════════════════
# ESC ESC ESC from the *Help* buffer
# ═══════════════════════════════════════════════════════════════════════


class TestEscapeQuitHelpBuffer:
    def test_three_escapes_dismiss_help_buffer(self):
        """ESC ESC ESC while viewing *Help* switches back to a regular
        buffer.  The *Help* buffer itself stays on the list.
        """
        ed = make_editor("main text")
        # Open *Help* via describe-bindings (C-h b)
        ed.process_key("C-h")
        ed.process_key("b")
        assert ed.buffer.name == "*Help*"
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.buffer.name != "*Help*"
        # *Help* still exists in the buffer list
        assert any(b.name == "*Help*" for b in ed.buffers)
        assert ed.message == "Quit"

    def test_escape_quit_from_help_switches_to_first_non_help(self):
        """The dismissal picks the first non-*Help* buffer (not random)."""
        ed = make_editor("original")
        original_name = ed.buffer.name
        ed.process_key("C-h")
        ed.process_key("b")  # describe-bindings opens *Help*
        assert ed.buffer.name == "*Help*"
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.buffer.name == original_name


# ═══════════════════════════════════════════════════════════════════════
# keyboard-escape-quit directly (via M-x / execute_command)
# ═══════════════════════════════════════════════════════════════════════


class TestKeyboardEscapeQuitDirect:
    def test_execute_command_keyboard_escape_quit(self):
        """Running the command directly clears state, dismisses help
        and minibuffer, and shows "Quit".
        """
        ed = make_editor("hello")
        ed.process_key("C-space")
        ed._prefix_arg = 7
        ed._pending_keymap = ed.global_keymap
        ed.execute_command("keyboard-escape-quit")
        assert ed.buffer.mark is None
        assert ed._prefix_arg is None
        assert ed._pending_keymap is None
        assert ed.message == "Quit"

    def test_keyboard_escape_quit_dismisses_active_minibuffer(self):
        """Direct invocation dismisses an active minibuffer."""
        ed = make_editor()
        ed.process_key("M-x")
        assert ed.minibuffer is not None
        ed.execute_command("keyboard-escape-quit")
        assert ed.minibuffer is None

    def test_keyboard_escape_quit_switches_from_help(self):
        """Direct invocation switches away from *Help* buffer."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        assert ed.buffer.name == "*Help*"
        ed.execute_command("keyboard-escape-quit")
        assert ed.buffer.name != "*Help*"

    def test_keyboard_escape_quit_registered(self):
        """keyboard-escape-quit is in the COMMANDS registry."""
        from recursive_neon.editor.commands import COMMANDS

        assert "keyboard-escape-quit" in COMMANDS


# ═══════════════════════════════════════════════════════════════════════
# Interaction with describe-key (ESC during describe-key capture)
# ═══════════════════════════════════════════════════════════════════════


class TestEscapeDescribeKey:
    def test_describe_key_escape_describes_meta_role(self):
        """C-h k ESC describes Escape as the Meta prefix (not "not
        bound" or "keyboard-escape-quit"), matching Emacs's spirit.
        """
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("k")
        assert ed._describe_key_session is not None
        assert ed._describe_key_session.brief is False
        ed.process_key("Escape")  # describe-key captures ESC
        assert ed._describe_key_session is None
        # State machine was NOT entered
        assert ed._meta_pending is False
        # *Help* buffer shows the ESC-as-Meta explanation
        help_buf = next((b for b in ed.buffers if b.name == "*Help*"), None)
        assert help_buf is not None
        assert "Meta" in help_buf.text
        assert "keyboard-escape-quit" in help_buf.text

    def test_describe_key_briefly_escape_describes_meta_role(self):
        """C-h c ESC shows the Meta-prefix description in the message area."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("c")
        assert ed._describe_key_session is not None
        assert ed._describe_key_session.brief is True
        ed.process_key("Escape")
        assert ed._describe_key_session is None
        assert ed._meta_pending is False
        assert "Meta" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# Interaction with isearch
# ═══════════════════════════════════════════════════════════════════════


class TestEscapeInIsearch:
    def test_three_escapes_exit_isearch(self):
        """ESC ESC ESC during isearch dismisses the search minibuffer."""
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("C-s")
        ed.process_key("w")
        assert ed.buffer.point.col == 6
        assert ed.minibuffer is not None
        ed.process_key("Escape")
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed.minibuffer is None
        # keyboard-escape-quit calls minibuffer.process_key("C-g"),
        # which fires isearch's on_cancel and restores the point.
        assert ed.buffer.point.col == 0


# ═══════════════════════════════════════════════════════════════════════
# State machine edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestEscStateMachine:
    def test_esc_esc_then_key_is_meta(self):
        """After two ESCs, a non-ESC key still dispatches as M-<key>
        (the second ESC was the active meta prefix; escape-quit-pending
        collapses back to a single meta prefix).
        """
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed._escape_quit_pending is True
        ed.process_key("f")  # rewritten to M-f → forward-word
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False
        assert ed.buffer.point.col == 5  # moved over "hello"

    def test_cg_in_meta_pending_runs_keyboard_quit(self):
        """C-g during meta-pending cancels, without being rewritten to
        C-M-g.  C-g is a universal quit signal and must always cancel,
        regardless of any in-progress state machine.
        """
        ed = make_editor("hello")
        ed.process_key("C-space")  # set mark so we can observe the quit
        ed.process_key("Escape")
        assert ed._meta_pending is True
        ed.process_key("C-g")
        # State machine cleared and keyboard-quit ran
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False
        assert ed.buffer.mark is None  # region cleared by keyboard-quit
        assert ed.message == "Quit"

    def test_cg_in_escape_quit_pending_runs_keyboard_quit(self):
        """C-g during escape-quit-pending also cancels normally."""
        ed = make_editor()
        ed.process_key("Escape")
        ed.process_key("Escape")
        assert ed._escape_quit_pending is True
        ed.process_key("C-g")
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False
        assert ed.message == "Quit"

    def test_reset_transient_state_clears_meta_flags(self):
        """_reset_transient_state clears the ESC-as-Meta state fields."""
        ed = make_editor()
        ed._meta_pending = True
        ed._escape_quit_pending = True
        ed._reset_transient_state()
        assert ed._meta_pending is False
        assert ed._escape_quit_pending is False

    def test_keyboard_quit_via_cg_clears_meta_state(self):
        """C-g at top level runs keyboard-quit, which clears the
        ESC-as-Meta state along with everything else.
        """
        ed = make_editor()
        # Simulate a half-finished ESC state that somehow survived
        ed._meta_pending = True
        ed.process_key("C-g")
        # C-g is special-cased in the state machine: it clears pending
        # flags and falls through to keyboard-quit normally.
        assert ed._meta_pending is False
        assert ed.message == "Quit"

    def test_esc_in_prefix_keymap_allows_m_key_lookup(self):
        """While C-x is pending, ESC-<key> rewrites to M-<key> and looks
        up in the pending keymap (not the global keymap).  Unbound M-<key>
        in C-x's prefix map → "undefined" message.
        """
        ed = make_editor()
        ed.process_key("C-x")
        assert ed._pending_keymap is not None
        ed.process_key("Escape")
        # Pending C-x keymap should still be live; the ESC just set
        # _meta_pending without cancelling it.
        assert ed._pending_keymap is not None
        assert ed._meta_pending is True
        ed.process_key("q")  # rewritten to M-q → not bound under C-x
        assert ed._pending_keymap is None
        assert ed._meta_pending is False
        assert "undefined" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# _rewrite_as_meta helper behaviour
# ═══════════════════════════════════════════════════════════════════════


class TestRewriteAsMeta:
    def test_printable_char_gets_m_prefix(self):
        assert Editor._rewrite_as_meta("f") == "M-f"
        assert Editor._rewrite_as_meta("x") == "M-x"

    def test_named_key_gets_m_prefix(self):
        assert Editor._rewrite_as_meta("Enter") == "M-Enter"
        assert Editor._rewrite_as_meta("Backspace") == "M-Backspace"
        assert Editor._rewrite_as_meta("Tab") == "M-Tab"

    def test_ctrl_key_becomes_c_m(self):
        assert Editor._rewrite_as_meta("C-f") == "C-M-f"
        assert Editor._rewrite_as_meta("C-v") == "C-M-v"

    def test_already_meta_is_unchanged(self):
        assert Editor._rewrite_as_meta("M-f") == "M-f"
        assert Editor._rewrite_as_meta("M-Enter") == "M-Enter"

    def test_already_c_m_is_unchanged(self):
        assert Editor._rewrite_as_meta("C-M-f") == "C-M-f"

    def test_symbol_gets_m_prefix(self):
        assert Editor._rewrite_as_meta(">") == "M->"
        assert Editor._rewrite_as_meta("<") == "M-<"
