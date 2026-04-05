"""
Tests for ``keyboard-quit`` (C-g) and all its cancellation paths.

Every interactive mode in the editor has to cancel cleanly on C-g and
show the ``"Quit"`` message.  These tests exercise each path explicitly
so regressions in cancellation handling get caught early.

Paths covered:

- Pending prefix keymap (mid-``C-x``)
- Prefix argument being built (``C-u``, ``C-u 4``)
- Stacked C-u + prefix keymap
- Transient region / mark
- Minibuffer — ``M-x``, ``C-x b``, ``C-x C-f``
- ``execute-extended-command`` mid-typing
- Incremental search (``C-s``) — restores original point
- Emacs-style describe-key: C-g inside describe-key describes
  ``keyboard-quit`` rather than cancelling (matching Emacs).
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
# Pending prefix keymap
# ═══════════════════════════════════════════════════════════════════════


class TestQuitPendingPrefix:
    def test_cg_cancels_mid_cx(self):
        """C-g during a C-x prefix clears pending state and shows Quit."""
        ed = make_editor("hello")
        ed.process_key("C-x")
        assert ed._pending_keymap is not None
        assert ed._prefix_keys == "C-x"

        ed.process_key("C-g")

        assert ed._pending_keymap is None
        assert ed._prefix_keys == ""
        assert ed.message == "Quit"

    def test_cg_cancels_mid_ch(self):
        """C-g during a C-h (help) prefix clears pending state."""
        ed = make_editor()
        ed.process_key("C-h")
        assert ed._pending_keymap is not None

        ed.process_key("C-g")

        assert ed._pending_keymap is None
        assert ed.message == "Quit"

    def test_next_key_after_quit_runs_normally(self):
        """After C-g cancels the prefix, the next key is dispatched fresh."""
        ed = make_editor("hello")
        ed.process_key("C-x")
        ed.process_key("C-g")
        ed.process_key("C-f")  # forward-char from the global map
        assert ed.buffer.point.col == 1


# ═══════════════════════════════════════════════════════════════════════
# Prefix argument (C-u)
# ═══════════════════════════════════════════════════════════════════════


class TestQuitPrefixArg:
    def test_cg_cancels_cu(self):
        """C-g after C-u clears the prefix argument and flags."""
        ed = make_editor("hello")
        ed.process_key("C-u")
        assert ed._prefix_arg == 4
        assert ed._building_prefix is True

        ed.process_key("C-g")

        assert ed._prefix_arg is None
        assert ed._building_prefix is False
        assert ed._prefix_has_digits is False
        assert ed.message == "Quit"

    def test_cg_cancels_cu_with_digit(self):
        """C-g after C-u 5 clears the in-progress prefix arg."""
        ed = make_editor("x" * 20)
        ed.process_key("C-u")
        ed.process_key("5")
        assert ed._prefix_arg == 5

        ed.process_key("C-g")

        assert ed._prefix_arg is None
        assert ed._building_prefix is False
        assert ed.message == "Quit"

    def test_next_digit_after_quit_is_self_insert(self):
        """After C-u C-g, a following digit should self-insert, not
        extend a phantom prefix arg.
        """
        ed = make_editor()
        ed.process_key("C-u")
        ed.process_key("C-g")
        ed.process_key("5")
        assert ed.buffer.text == "5"


# ═══════════════════════════════════════════════════════════════════════
# Stacked C-u + prefix keymap
# ═══════════════════════════════════════════════════════════════════════


class TestQuitStacked:
    def test_cg_clears_cu_and_prefix(self):
        """C-u C-x C-g: both the prefix arg and the pending C-x clear."""
        ed = make_editor()
        ed.process_key("C-u")
        ed.process_key("C-x")
        # Both states should be live
        assert ed._prefix_arg == 4
        assert ed._pending_keymap is not None

        ed.process_key("C-g")

        assert ed._prefix_arg is None
        assert ed._pending_keymap is None
        assert ed._building_prefix is False
        assert ed.message == "Quit"


# ═══════════════════════════════════════════════════════════════════════
# Region / mark
# ═══════════════════════════════════════════════════════════════════════


class TestQuitRegion:
    def test_cg_clears_active_mark(self):
        """C-g at top level deactivates the region."""
        ed = make_editor("hello")
        ed.process_key("C-space")
        assert ed.buffer.mark is not None

        ed.process_key("C-g")

        assert ed.buffer.mark is None
        assert ed.message == "Quit"

    def test_cg_with_no_mark_is_harmless(self):
        """C-g at top level with no mark still shows Quit."""
        ed = make_editor()
        assert ed.buffer.mark is None

        ed.process_key("C-g")

        assert ed.buffer.mark is None
        assert ed.message == "Quit"


# ═══════════════════════════════════════════════════════════════════════
# Minibuffer — M-x, C-x b, C-x C-f
# ═══════════════════════════════════════════════════════════════════════


class TestQuitMinibuffer:
    def test_cg_cancels_mx(self):
        ed = make_editor()
        ed.process_key("M-x")
        assert ed.minibuffer is not None

        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_cg_cancels_mx_mid_typing(self):
        """C-g while typing in M-x still cancels cleanly."""
        ed = make_editor()
        ed.process_key("M-x")
        ed.process_key("f")
        ed.process_key("o")
        ed.process_key("o")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "foo"

        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_cg_cancels_switch_buffer(self):
        """C-x b then C-g closes the buffer-switch minibuffer."""
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("b")
        assert ed.minibuffer is not None

        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.message == "Quit"
        # And the pending prefix is gone
        assert ed._pending_keymap is None
        assert ed._prefix_keys == ""

    def test_cg_cancels_find_file(self):
        """C-x C-f then C-g closes the find-file minibuffer."""
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("C-f")
        assert ed.minibuffer is not None

        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.message == "Quit"

    def test_cg_in_minibuffer_preserves_mark(self):
        """Emacs behaviour: cancelling a minibuffer prompt does *not*
        deactivate the mark that was active when the prompt opened.
        """
        ed = make_editor("hello world")
        ed.process_key("C-space")
        mark_before = ed.buffer.mark
        assert mark_before is not None

        ed.process_key("M-x")
        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.message == "Quit"
        assert ed.buffer.mark is not None  # mark preserved


# ═══════════════════════════════════════════════════════════════════════
# Isearch — C-g restores original point
# ═══════════════════════════════════════════════════════════════════════


class TestQuitIsearch:
    def test_cg_cancels_isearch_and_restores_point(self):
        ed = make_editor("hello world")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("C-s")
        ed.process_key("w")
        assert ed.buffer.point.col == 6  # found "w" in "world"

        ed.process_key("C-g")

        assert ed.minibuffer is None
        assert ed.buffer.point.col == 0  # restored to starting position
        assert ed.message == "Quit"


# ═══════════════════════════════════════════════════════════════════════
# Describe-key — Emacs behaviour: C-g describes, does NOT cancel
# ═══════════════════════════════════════════════════════════════════════


class TestDescribeKeyCG:
    def test_cg_in_describe_key_describes_keyboard_quit(self):
        """Matches Emacs: C-h k C-g shows the binding for C-g."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("k")
        assert ed._describe_key_session is not None
        assert ed._describe_key_session.brief is False

        ed.process_key("C-g")

        # Describe-key capture consumed C-g and produced a describe-key
        # result; the capture mode is cleared.
        assert ed._describe_key_session is None
        # The Help buffer was shown with the keyboard-quit binding
        help_buf = next((b for b in ed.buffers if b.name == "*Help*"), None)
        assert help_buf is not None
        assert "keyboard-quit" in help_buf.text

    def test_cg_in_describe_key_briefly_describes(self):
        """C-h c C-g shows keyboard-quit in the message area."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("c")
        assert ed._describe_key_session is not None
        assert ed._describe_key_session.brief is True

        ed.process_key("C-g")

        assert ed._describe_key_session is None
        assert "keyboard-quit" in ed.message


# ═══════════════════════════════════════════════════════════════════════
# keyboard-quit command directly (via M-x / execute_command)
# ═══════════════════════════════════════════════════════════════════════


class TestQuitCommandDirect:
    def test_execute_command_keyboard_quit(self):
        """Running keyboard-quit directly clears state and sets Quit."""
        ed = make_editor("hello")
        ed.process_key("C-space")
        ed._prefix_arg = 7  # simulate weird state
        ed._pending_keymap = ed.global_keymap  # simulate weird state

        ed.execute_command("keyboard-quit")

        assert ed.buffer.mark is None
        assert ed._prefix_arg is None
        assert ed._pending_keymap is None
        assert ed.message == "Quit"

    def test_reset_transient_state_clears_describe_key(self):
        """_reset_transient_state clears describe-key state too (used
        by keyboard-escape-quit).
        """
        from recursive_neon.editor.editor import _DescribeKeySession

        ed = make_editor()
        ed._describe_key_session = _DescribeKeySession(
            brief=False, prefix="C-x", prefix_map=ed.global_keymap
        )

        ed._reset_transient_state()

        assert ed._describe_key_session is None
