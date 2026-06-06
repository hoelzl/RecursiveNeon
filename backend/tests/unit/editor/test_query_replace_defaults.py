"""Tests for query-replace defaults (GNU Emacs's query-replace-defaults).

After one M-% the (from, to) pair becomes the default: the next prompt
shows it, an empty from-input reuses it, and M-p offers the combined
``from → to`` entry ahead of the individual history.
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import _QR_SEP, build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


def do_qr(ed: Editor, frm: str, to: str) -> None:
    """Run M-% <frm> RET <to> RET, leaving the session on the first match."""
    ed.process_key("M-%")
    for c in frm:
        ed.process_key(c)
    ed.process_key("Enter")
    for c in to:
        ed.process_key(c)
    ed.process_key("Enter")


class TestQueryReplaceDefaults:
    def test_default_recorded(self) -> None:
        ed = make_editor("foo foo")
        do_qr(ed, "foo", "bar")
        assert ed._query_replace_defaults == ("foo", "bar")

    def test_first_prompt_has_no_default(self) -> None:
        ed = make_editor("foo")
        ed.process_key("M-%")
        assert ed.minibuffer is not None
        assert ed.minibuffer.prompt == "Query replace: "

    def test_second_prompt_shows_default(self) -> None:
        ed = make_editor("foo foo")
        do_qr(ed, "foo", "bar")
        ed.process_key("q")  # exit the session
        ed.process_key("M-%")
        assert ed.minibuffer is not None
        assert ed.minibuffer.prompt == f"Query replace (default foo{_QR_SEP}bar): "

    def test_empty_input_reuses_default(self) -> None:
        ed = make_editor("foo foo foo")
        do_qr(ed, "foo", "bar")
        ed.process_key("q")
        ed.process_key("M-%")
        ed.process_key("Enter")  # empty from-input
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.from_text == "foo"
        assert ed._query_replace_session.to_text == "bar"
        # No with-prompt was opened.
        assert ed.minibuffer is None

    def test_empty_input_without_default_does_nothing(self) -> None:
        ed = make_editor("foo")
        ed.process_key("M-%")
        ed.process_key("Enter")
        assert ed._query_replace_session is None
        assert ed.minibuffer is None

    def test_mp_recalls_combined_then_individual(self) -> None:
        ed = make_editor("foo foo")
        do_qr(ed, "foo", "bar")
        ed.process_key("q")
        ed.process_key("M-%")
        ed.process_key("M-p")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == f"foo{_QR_SEP}bar"  # combined pair
        ed.process_key("M-p")
        assert ed.minibuffer.text == "bar"  # newest individual (the "to")
        ed.process_key("M-p")
        assert ed.minibuffer.text == "foo"  # older individual (the "from")

    def test_submitting_combined_entry_splits_it(self) -> None:
        ed = make_editor("hello world")
        do_qr(ed, "hello", "HI")
        ed.process_key("q")
        ed.buffer.point.move_to(0, 0)  # so "hello" is reachable again
        ed.process_key("M-%")
        ed.process_key("M-p")  # → "hello → HI"
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == f"hello{_QR_SEP}HI"
        ed.process_key("Enter")  # submit the combined entry
        assert ed._query_replace_session is not None
        assert ed._query_replace_session.from_text == "hello"
        assert ed._query_replace_session.to_text == "HI"

    def test_submitting_combined_entry_does_not_duplicate_history(self) -> None:
        """Splitting a recalled combined entry must not re-push its parts —
        they are already on the history, so it would create duplicates."""
        ed = make_editor("foo foo")
        do_qr(ed, "foo", "bar")  # history == ["bar", "foo"]
        ed.process_key("q")
        ed.buffer.point.move_to(0, 0)
        ed.process_key("M-%")
        ed.process_key("M-p")  # recall combined "foo → bar"
        ed.process_key("Enter")  # submit it
        assert ed._minibuffer_histories["query-replace"] == ["bar", "foo"]
