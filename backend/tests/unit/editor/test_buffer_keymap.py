"""Tests for buffer-local keymaps and callable keymap targets."""

from __future__ import annotations

import pytest

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.keymap import Keymap


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


@pytest.mark.unit
class TestBufferLocalKeymap:
    def test_global_keymap_used_by_default(self):
        """Without a buffer keymap, the global keymap is used."""
        ed = make_editor("hello")
        # C-e (end-of-line) should work via global keymap
        ed.process_key("C-e")
        assert ed.buffer.point.col == 5

    def test_buffer_keymap_overrides_global(self):
        """A buffer keymap takes priority over the global keymap."""
        ed = make_editor("hello")
        km = Keymap("test", parent=ed.global_keymap)

        called = {}
        km.bind("C-e", lambda editor, prefix: called.update(hit=True))

        ed.buffer.keymap = km
        ed.process_key("C-e")
        assert called.get("hit") is True
        # Point should NOT have moved (our lambda doesn't call end-of-line)
        assert ed.buffer.point.col == 0

    def test_buffer_keymap_falls_through_to_global(self):
        """Unbound keys in buffer keymap fall through to global via parent."""
        ed = make_editor("hello")
        km = Keymap("test", parent=ed.global_keymap)
        km.bind("x", lambda editor, prefix: None)  # only override "x"

        ed.buffer.keymap = km
        # C-e is NOT in the buffer keymap but IS in the global
        ed.process_key("C-e")
        assert ed.buffer.point.col == 5

    def test_switching_buffers_changes_keymap(self):
        """Different buffers can have different keymaps."""
        ed = make_editor("aaa")
        ed.buffer.name = "buf-a"

        ed.create_buffer(name="buf-b", text="bbb")
        km = Keymap("buf-b-map", parent=ed.global_keymap)
        called = {}
        km.bind("x", lambda editor, prefix: called.update(hit=True))
        ed.buffer.keymap = km

        # Press x in buf-b — should call the lambda
        ed.process_key("x")
        assert called.get("hit") is True

        # Switch to buf-a — x should self-insert
        ed.switch_to_buffer("buf-a")
        ed.process_key("x")
        assert ed.buffer.text == "xaaa"


@pytest.mark.unit
class TestCallableKeyTarget:
    def test_callable_receives_editor_and_prefix(self):
        ed = make_editor("hello")
        km = Keymap("test", parent=ed.global_keymap)

        received = {}

        def my_action(editor, prefix):
            received["editor"] = editor
            received["prefix"] = prefix

        km.bind("a", my_action)
        ed.buffer.keymap = km
        ed.process_key("a")

        assert received["editor"] is ed
        assert received["prefix"] is None

    def test_callable_with_prefix_arg(self):
        ed = make_editor("hello")
        km = Keymap("test", parent=ed.global_keymap)

        received = {}
        km.bind("a", lambda editor, prefix: received.update(prefix=prefix))

        ed.buffer.keymap = km
        ed.process_key("C-u")
        ed.process_key("a")
        assert received["prefix"] == 4

    def test_callable_in_read_only_buffer(self):
        """Callables work in read-only buffers (unlike self-insert)."""
        ed = make_editor("hello")
        ed.buffer.read_only = True
        km = Keymap("test", parent=ed.global_keymap)

        called = {}
        km.bind("d", lambda editor, prefix: called.update(hit=True))

        ed.buffer.keymap = km
        ed.process_key("d")
        assert called.get("hit") is True
