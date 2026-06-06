"""Tests that the common prompts are wired to the right history list.

Verifies that submitting input through each command accumulates the
expected per-prompt history (and that prompts sharing a history variable
in Emacs share one here too).

The plain string-history prompts are wired: M-x (``command``), C-x b /
C-x k (``buffer-name``), and find-file / write-file (``file-name``).
query-replace uses the ``query-replace-defaults`` mechanism (combined
``from → to`` entries) — see ``test_query_replace_defaults.py``; here we
only confirm it now populates the ``query-replace`` history.
replace-string remains unwired (it would share that special history).
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


def _type(ed: Editor, s: str) -> None:
    for c in s:
        ed.process_key(c)


class TestPromptHistoryWiring:
    def test_buffer_name_history_shared_by_switch_and_kill(self) -> None:
        """C-x b and C-x k both use Emacs's buffer-name-history."""
        ed = make_editor("x")
        ed.process_key("C-x")
        ed.process_key("b")
        _type(ed, "alpha")
        ed.process_key("Enter")  # creates/switches to "alpha"
        # C-x k offers a default; M-p should recall the buffer name.
        ed.process_key("C-x")
        ed.process_key("k")
        ed.process_key("M-p")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "alpha"
        assert ed._minibuffer_histories["buffer-name"] == ["alpha"]

    def test_file_name_history_for_find_file(self) -> None:
        ed = make_editor("x")
        # find-file pre-fills the cwd; type a name and submit.
        ed.process_key("C-x")
        ed.process_key("C-f")
        assert ed.minibuffer is not None
        _type(ed, "notes.txt")
        ed.process_key("Enter")
        assert ed._minibuffer_histories["file-name"][0].endswith("notes.txt")

    def test_query_replace_records_history(self) -> None:
        """query-replace now records its from/to on the ``query-replace``
        history (newest first), via the query-replace-defaults mechanism."""
        ed = make_editor("foo and foo")
        ed.process_key("M-%")
        _type(ed, "foo")
        ed.process_key("Enter")
        _type(ed, "bar")
        ed.process_key("Enter")  # session starts on the first match
        assert ed._minibuffer_histories["query-replace"] == ["bar", "foo"]
