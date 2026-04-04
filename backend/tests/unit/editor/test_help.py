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


class TestHelpTutorial:
    def test_opens_tutorial_buffer(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("t")
        assert ed.buffer.name == "TUTORIAL.txt"

    def test_tutorial_is_read_only(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("t")
        assert ed.buffer.read_only

    def test_tutorial_not_modified(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("t")
        assert not ed.buffer.modified

    def test_tutorial_contains_expected_text(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("t")
        assert "NEON-EDIT TUTORIAL" in ed.buffer.text
        assert "C-f" in ed.buffer.text

    def test_reopening_switches_to_existing_buffer(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("t")
        # Switch away
        ed.switch_to_buffer("*scratch*")
        assert ed.buffer.name == "*scratch*"
        # Open tutorial again
        ed.process_key("C-h")
        ed.process_key("t")
        assert ed.buffer.name == "TUTORIAL.txt"
        # Should still be only one TUTORIAL.txt buffer
        tutorial_bufs = [b for b in ed.buffers if b.name == "TUTORIAL.txt"]
        assert len(tutorial_bufs) == 1


class TestDescribeBindings:
    def test_c_h_b_opens_help_buffer(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        assert ed.buffer.name == "*Help*"

    def test_help_buffer_is_read_only(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        assert ed.buffer.read_only

    def test_lists_global_bindings(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "forward-char" in text
        assert "C-f" in text
        assert "backward-char" in text
        assert "next-line" in text

    def test_lists_prefix_key_bindings(self):
        """Prefix keys like C-x, C-h should be expanded recursively."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        # C-x C-s -> save-buffer
        assert "C-x C-s" in text
        assert "save-buffer" in text
        # C-h k -> describe-key
        assert "C-h k" in text
        assert "describe-key" in text
        # Window bindings (C-x 2, C-x 3, C-x o)
        assert "split-window-below" in text
        assert "split-window-right" in text

    def test_lists_nested_prefix_bindings(self):
        """C-x 4 C-f should appear as a nested prefix sequence."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "C-x 4 C-f" in text
        assert "find-file-other-window" in text

    def test_includes_self_reference(self):
        """describe-bindings itself should be listed."""
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "C-h b" in text
        assert "describe-bindings" in text

    def test_shows_global_section_header(self):
        ed = make_editor()
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "Global bindings" in text

    def test_shows_buffer_local_bindings(self):
        """Buffer-local keymaps should be listed with a header."""
        from recursive_neon.editor.keymap import Keymap

        ed = make_editor()
        # Attach a buffer-local keymap
        local = Keymap("test-local", parent=ed.global_keymap)
        local.bind("C-c x", "forward-char")  # silly demo binding
        ed.buffer.keymap = local
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "Buffer-local bindings" in text
        assert "test-local" in text

    def test_shows_major_mode_bindings(self):
        """Major-mode bindings section appears when the mode has a keymap."""
        from recursive_neon.editor.keymap import Keymap
        from recursive_neon.editor.modes import Mode

        ed = make_editor()
        # Attach a test major mode with its own keymap.  parent=global so
        # the standard bindings (C-h b etc.) remain reachable.
        mode_keymap = Keymap("demo-mode-map", parent=ed.global_keymap)
        mode_keymap.bind("C-c d", "forward-char")
        demo = Mode(name="demo-mode", is_major=True, keymap=mode_keymap)
        ed.buffer.major_mode = demo
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        assert "Major mode bindings (demo-mode)" in text
        assert "C-c d" in text

    def test_no_parent_chain_duplication_in_layers(self):
        """Buffer-local layer should NOT re-list every global binding.

        A buffer-local keymap with parent=global would otherwise walk
        the parent chain and duplicate all globals under the local
        header.
        """
        from recursive_neon.editor.keymap import Keymap

        ed = make_editor()
        local = Keymap("scoped", parent=ed.global_keymap)
        local.bind("C-c a", "forward-char")  # single local binding
        ed.buffer.keymap = local
        ed.process_key("C-h")
        ed.process_key("b")
        text = ed.buffer.text
        # Split into the buffer-local and global sections
        local_header = "Buffer-local bindings (scoped):"
        global_header = "Global bindings"
        assert local_header in text
        assert global_header in text
        local_start = text.index(local_header)
        global_start = text.index(global_header)
        local_section = text[local_start:global_start]
        # Only the single local binding should appear in the local section
        assert "C-c a" in local_section
        # forward-char appears in both sections, but "C-f" binding is global only
        assert "C-f" not in local_section
