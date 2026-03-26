"""Tests for the help system (C-h k, C-h a)."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestDescribeKey:
    def test_c_h_k_then_key_shows_help(self):
        ed = make_editor("hello")
        ed.process_key("C-h")
        ed.process_key("k")
        # Now in describe-key mode
        assert ed._describing_key
        ed.process_key("C-f")
        # Should have opened *Help* with forward-char info
        assert ed.buffer.name == "*Help*"
        assert "forward-char" in ed.buffer.text

    def test_describe_prefix_key_sequence(self):
        ed = make_editor("hello")
        ed.process_key("C-h")
        ed.process_key("k")
        ed.process_key("C-x")  # prefix key — wait for second key
        assert ed._describing_key
        ed.process_key("C-s")
        assert ed.buffer.name == "*Help*"
        assert "save-buffer" in ed.buffer.text

    def test_describe_unbound_key(self):
        ed = make_editor("hello")
        ed.process_key("C-h")
        ed.process_key("k")
        ed.process_key("C-z")
        assert "not bound" in ed.message

    def test_describe_printable_key(self):
        ed = make_editor("hello")
        ed.process_key("C-h")
        ed.process_key("k")
        ed.process_key("a")
        assert "self-insert" in ed.message

    def test_help_buffer_is_read_only(self):
        ed = make_editor("hello")
        ed.process_key("C-h")
        ed.process_key("k")
        ed.process_key("C-f")
        assert ed.buffer.name == "*Help*"
        assert ed.buffer.read_only


class TestCommandApropos:
    def test_c_h_a_opens_minibuffer(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("a")
        assert ed.minibuffer is not None
        assert "apropos" in ed.minibuffer.prompt.lower()

    def test_apropos_finds_commands(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("a")
        for ch in "forward":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "*Help*"
        assert "forward-char" in ed.buffer.text
        assert "forward-word" in ed.buffer.text

    def test_apropos_no_match(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("a")
        for ch in "zzzzz":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert "No commands" in ed.message

    def test_apropos_searches_docs(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("a")
        for ch in "kill":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "*Help*"
        # Should find kill-line, kill-region, kill-word, etc.
        assert "kill-line" in ed.buffer.text
