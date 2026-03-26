"""Tests for the Keymap class."""

from __future__ import annotations

from recursive_neon.editor.keymap import Keymap


class TestKeymapBind:
    def test_bind_and_lookup(self):
        km = Keymap()
        km.bind("C-f", "forward-char")
        assert km.lookup("C-f") == "forward-char"

    def test_lookup_unbound_returns_none(self):
        km = Keymap()
        assert km.lookup("C-f") is None

    def test_bind_overwrites(self):
        km = Keymap()
        km.bind("C-f", "forward-char")
        km.bind("C-f", "other-command")
        assert km.lookup("C-f") == "other-command"

    def test_unbind(self):
        km = Keymap()
        km.bind("C-f", "forward-char")
        km.unbind("C-f")
        assert km.lookup("C-f") is None

    def test_unbind_nonexistent_is_safe(self):
        km = Keymap()
        km.unbind("C-f")  # no error


class TestKeymapParent:
    def test_inherits_from_parent(self):
        parent = Keymap("parent")
        parent.bind("C-f", "forward-char")
        child = Keymap("child", parent=parent)
        assert child.lookup("C-f") == "forward-char"

    def test_child_overrides_parent(self):
        parent = Keymap("parent")
        parent.bind("C-f", "forward-char")
        child = Keymap("child", parent=parent)
        child.bind("C-f", "my-forward")
        assert child.lookup("C-f") == "my-forward"
        # Parent unchanged
        assert parent.lookup("C-f") == "forward-char"

    def test_child_local_bindings_dont_include_parent(self):
        parent = Keymap("parent")
        parent.bind("C-f", "forward-char")
        child = Keymap("child", parent=parent)
        child.bind("C-b", "backward-char")
        local = child.bindings()
        assert "C-b" in local
        assert "C-f" not in local

    def test_all_bindings_merges_parent(self):
        parent = Keymap("parent")
        parent.bind("C-f", "forward-char")
        child = Keymap("child", parent=parent)
        child.bind("C-b", "backward-char")
        all_b = child.all_bindings()
        assert all_b["C-f"] == "forward-char"
        assert all_b["C-b"] == "backward-char"

    def test_deep_inheritance(self):
        gp = Keymap("grandparent")
        gp.bind("C-a", "beginning-of-line")
        p = Keymap("parent", parent=gp)
        c = Keymap("child", parent=p)
        assert c.lookup("C-a") == "beginning-of-line"


class TestKeymapPrefixKeys:
    def test_bind_sub_keymap(self):
        km = Keymap("global")
        cx = Keymap("C-x prefix")
        cx.bind("C-s", "save-buffer")
        km.bind("C-x", cx)

        result = km.lookup("C-x")
        assert isinstance(result, Keymap)
        assert result.lookup("C-s") == "save-buffer"

    def test_prefix_key_second_level(self):
        km = Keymap("global")
        cx = Keymap("C-x prefix")
        cx.bind("C-c", "quit-editor")
        cx.bind("C-s", "save-buffer")
        km.bind("C-x", cx)

        prefix = km.lookup("C-x")
        assert isinstance(prefix, Keymap)
        assert prefix.lookup("C-c") == "quit-editor"
        assert prefix.lookup("C-s") == "save-buffer"

    def test_unknown_key_in_prefix_returns_none(self):
        km = Keymap("global")
        cx = Keymap("C-x prefix")
        cx.bind("C-c", "quit-editor")
        km.bind("C-x", cx)

        prefix = km.lookup("C-x")
        assert isinstance(prefix, Keymap)
        assert prefix.lookup("z") is None
