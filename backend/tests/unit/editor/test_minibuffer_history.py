"""Tests for minibuffer input history (M-p / M-n).

Covers the Minibuffer navigation primitives and the end-to-end flow
through the editor (M-x command history, per-prompt separation).
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.minibuffer import Minibuffer


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


# ═══════════════════════════════════════════════════════════════════════
# Minibuffer-level navigation
# ═══════════════════════════════════════════════════════════════════════


class TestMinibufferHistoryNavigation:
    def test_mp_walks_back_then_stops_at_oldest(self) -> None:
        hist = ["second", "first"]  # newest first
        mb = Minibuffer("> ", lambda t: None, history=hist)
        mb.process_key("M-p")
        assert mb.text == "second"
        # Emacs leaves point at the start of the recalled element.
        assert mb.cursor == 0
        mb.process_key("M-p")
        assert mb.text == "first"
        mb.process_key("M-p")  # already at the oldest — no-op
        assert mb.text == "first"

    def test_mn_walks_forward_and_restores_typed_input(self) -> None:
        mb = Minibuffer("> ", lambda t: None, history=["a", "b"])
        mb.process_key("x")  # typed input
        mb.process_key("M-p")
        assert mb.text == "a"
        mb.process_key("M-p")
        assert mb.text == "b"
        mb.process_key("M-n")
        assert mb.text == "a"
        mb.process_key("M-n")  # back to position 0 → restore typed input
        assert mb.text == "x"
        mb.process_key("M-n")  # at the live input — no-op
        assert mb.text == "x"

    def test_no_history_makes_mp_mn_noops(self) -> None:
        mb = Minibuffer("> ", lambda t: None)  # history is None
        mb.process_key("M-p")
        mb.process_key("M-n")
        assert mb.text == ""


class TestMinibufferHistorySubmit:
    def test_submit_prepends_nonempty_input(self) -> None:
        hist: list[str] = []
        mb = Minibuffer("> ", lambda t: None, history=hist)
        for c in "ab":
            mb.process_key(c)
        assert mb.process_key("Enter") is False
        assert hist == ["ab"]

    def test_empty_submit_not_recorded(self) -> None:
        hist: list[str] = []
        mb = Minibuffer("> ", lambda t: None, history=hist)
        mb.process_key("Enter")
        assert hist == []

    def test_recall_then_submit_does_not_duplicate(self) -> None:
        """Submitting a recalled item must not duplicate the front entry.

        GNU Emacs's minibuffer read skips the history add when the result
        is ``equal`` to the most recent entry, so M-p then Enter keeps the
        list as-is rather than prepending a copy.
        """
        hist = ["alpha"]
        mb = Minibuffer("> ", lambda t: None, history=hist)
        mb.process_key("M-p")  # recall "alpha"
        assert mb.text == "alpha"
        mb.process_key("Enter")
        assert hist == ["alpha"]  # not ["alpha", "alpha"]

    def test_submit_differing_input_still_prepends(self) -> None:
        hist = ["alpha"]
        mb = Minibuffer("> ", lambda t: None, history=hist)
        for c in "beta":
            mb.process_key(c)
        mb.process_key("Enter")
        assert hist == ["beta", "alpha"]

    def test_newest_first(self) -> None:
        hist: list[str] = []
        for word in ("one", "two"):
            mb = Minibuffer("> ", lambda t: None, history=hist)
            for c in word:
                mb.process_key(c)
            mb.process_key("Enter")
        assert hist == ["two", "one"]


# ═══════════════════════════════════════════════════════════════════════
# End-to-end via the editor (M-x command history)
# ═══════════════════════════════════════════════════════════════════════


def _mx(ed: Editor, name: str) -> None:
    """Run M-x <name> RET."""
    ed.process_key("M-x")
    for c in name:
        ed.process_key(c)
    ed.process_key("Enter")


class TestCommandHistoryEndToEnd:
    def test_mx_recalls_previous_command(self) -> None:
        ed = make_editor("hello world")
        _mx(ed, "forward-char")
        ed.process_key("M-x")
        assert ed.minibuffer is not None
        ed.process_key("M-p")
        assert ed.minibuffer.text == "forward-char"
        # Prompt is preserved.
        assert ed.minibuffer.prompt == "M-x "

    def test_mx_walks_two_commands(self) -> None:
        ed = make_editor("hello world")
        _mx(ed, "forward-char")
        _mx(ed, "backward-char")
        ed.process_key("M-x")
        ed.process_key("M-p")
        assert ed.minibuffer.text == "backward-char"  # most recent
        ed.process_key("M-p")
        assert ed.minibuffer.text == "forward-char"  # older
        ed.process_key("M-n")
        assert ed.minibuffer.text == "backward-char"

    def test_histories_are_per_prompt(self) -> None:
        ed = make_editor("hello")
        _mx(ed, "forward-char")
        # C-x b <name> RET (records on the buffer-name history).
        ed.process_key("C-x")
        ed.process_key("b")
        for c in "scratch2":
            ed.process_key(c)
        ed.process_key("Enter")
        # M-x M-p sees the command history, not the buffer name.
        ed.process_key("M-x")
        ed.process_key("M-p")
        assert ed.minibuffer.text == "forward-char"
        ed.process_key("C-g")
        # C-x b M-p sees the buffer-name history.
        ed.process_key("C-x")
        ed.process_key("b")
        ed.process_key("M-p")
        assert ed.minibuffer.text == "scratch2"
