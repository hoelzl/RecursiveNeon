"""Tests for Phase 6f commands: C-x u, describe-key-briefly, describe-mode,
where-is, save-some-buffers, and sentence command keybindings."""

from __future__ import annotations

from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# Sentence command keybindings
# ═══════════════════════════════════════════════════════════════════════


class TestSentenceKeybindings:
    def test_m_e_forward_sentence(self) -> None:
        h = make_harness("Hello world. Next.", width=40, height=10)
        h.send_keys("M-e")
        assert h.point() == (0, 12)

    def test_m_a_backward_sentence(self) -> None:
        h = make_harness("First. Second.", width=40, height=10)
        h.send_keys("C-e")  # end of line
        h.send_keys("M-a")
        assert h.point() == (0, 7)  # start of "Second"

    def test_m_k_kill_sentence(self) -> None:
        h = make_harness("Kill this. Keep.", width=40, height=10)
        h.send_keys("M-k")
        assert h.buffer_text() == " Keep."


# ═══════════════════════════════════════════════════════════════════════
# C-x u → undo
# ═══════════════════════════════════════════════════════════════════════


class TestCxUndo:
    def test_cx_u_undoes_insertion(self) -> None:
        h = make_harness("", width=40, height=10)
        h.type_string("hello")
        assert h.buffer_text() == "hello"
        h.send_keys("C-x", "u")
        assert h.buffer_text() == ""

    def test_cx_u_same_as_c_slash(self) -> None:
        h = make_harness("", width=40, height=10)
        h.type_string("abc")
        h.send_keys("C-x", "u")
        # Both should produce the same effect
        h2 = make_harness("", width=40, height=10)
        h2.type_string("abc")
        h2.send_keys("C-/")
        assert h.buffer_text() == h2.buffer_text()


# ═══════════════════════════════════════════════════════════════════════
# describe-key-briefly (C-h c)
# ═══════════════════════════════════════════════════════════════════════


class TestDescribeKeyBriefly:
    def test_shows_binding_in_message(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "c", "C-f")
        assert "forward-char" in h.message_line()

    def test_shows_in_message_not_help_buffer(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "c", "C-f")
        # Should NOT switch to *Help* buffer
        assert h.editor.buffer.name == "*scratch*"

    def test_prefix_key_sequence(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "c", "C-x", "C-s")
        assert "save-buffer" in h.message_line()

    def test_unbound_key(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "c", "C-q")
        assert "not bound" in h.message_line()

    def test_printable_char(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "c", "a")
        assert "self-insert-command" in h.message_line()


# ═══════════════════════════════════════════════════════════════════════
# describe-mode (C-h m)
# ═══════════════════════════════════════════════════════════════════════


class TestDescribeMode:
    def test_opens_help_buffer(self) -> None:
        h = make_harness("test", width=60, height=20)
        h.send_keys("C-h", "m")
        assert h.editor.buffer.name == "*Help*"

    def test_contains_bindings(self) -> None:
        h = make_harness("test", width=60, height=20)
        h.send_keys("C-h", "m")
        text = h.buffer_text()
        assert "forward-char" in text
        assert "C-f" in text

    def test_help_buffer_is_readonly(self) -> None:
        h = make_harness("test", width=60, height=20)
        h.send_keys("C-h", "m")
        assert h.editor.buffer.read_only is True


# ═══════════════════════════════════════════════════════════════════════
# where-is (C-h x)
# ═══════════════════════════════════════════════════════════════════════


class TestWhereIs:
    def test_finds_binding(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "x")
        h.type_string("forward-char")
        h.send_keys("Enter")
        msg = h.message_line()
        assert "forward-char" in msg
        assert "C-f" in msg

    def test_command_not_bound(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "x")
        h.type_string("nonexistent-cmd")
        h.send_keys("Enter")
        assert "not on any key" in h.message_line()

    def test_stays_in_original_buffer(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-h", "x")
        h.type_string("undo")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "*scratch*"


# ═══════════════════════════════════════════════════════════════════════
# save-some-buffers (C-x s)
# ═══════════════════════════════════════════════════════════════════════


class TestSaveSomeBuffers:
    def test_no_modified_buffers(self) -> None:
        h = make_harness("test", width=40, height=10)
        h.send_keys("C-x", "s")
        assert "No buffers need saving" in h.message_line()

    def test_saves_on_y(self) -> None:
        h = make_harness("test", width=40, height=10)
        saved: list[str] = []

        def save_cb(buf):
            saved.append(buf.name)
            return True

        h.editor.save_callback = save_cb
        h.editor.buffer.filepath = "/test.txt"
        h.editor.buffer.modified = True
        h.send_keys("C-x", "s")
        h.type_string("y")
        h.send_keys("Enter")
        assert len(saved) == 1
        assert not h.editor.buffer.modified

    def test_skips_on_n(self) -> None:
        h = make_harness("test", width=40, height=10)
        saved: list[str] = []

        def save_cb(buf):
            saved.append(buf.name)
            return True

        h.editor.save_callback = save_cb
        h.editor.buffer.filepath = "/test.txt"
        h.editor.buffer.modified = True
        h.send_keys("C-x", "s")
        h.type_string("n")
        h.send_keys("Enter")
        assert len(saved) == 0
        assert h.editor.buffer.modified  # still modified

    def test_multiple_buffers(self) -> None:
        h = make_harness("", width=40, height=10)
        saved: list[str] = []

        def save_cb(buf):
            saved.append(buf.name)
            return True

        h.editor.save_callback = save_cb
        # Set up first buffer
        h.editor.buffer.name = "a.txt"
        h.editor.buffer.filepath = "/a.txt"
        h.editor.buffer.modified = True
        # Create second modified buffer
        h.editor.create_buffer(name="b.txt", text="bb", filepath="/b.txt")
        h.editor.buffer.modified = True

        h.send_keys("C-x", "s")
        # First prompt: save a.txt? -> y
        h.type_string("y")
        h.send_keys("Enter")
        # Second prompt: save b.txt? -> y
        h.type_string("y")
        h.send_keys("Enter")
        assert sorted(saved) == ["a.txt", "b.txt"]

    def test_skips_buffers_without_filepath(self) -> None:
        h = make_harness("", width=40, height=10)
        h.editor.buffer.modified = True
        # No filepath — should not be prompted
        h.send_keys("C-x", "s")
        assert "No buffers need saving" in h.message_line()


# ═══════════════════════════════════════════════════════════════════════
# Reverse keymap lookup
# ═══════════════════════════════════════════════════════════════════════


class TestReverseKeymap:
    def test_finds_direct_binding(self) -> None:
        from recursive_neon.editor.default_commands import build_default_keymap

        km = build_default_keymap()
        keys = km.reverse_lookup("forward-char")
        assert "C-f" in keys
        assert "ArrowRight" in keys

    def test_finds_prefixed_binding(self) -> None:
        from recursive_neon.editor.default_commands import build_default_keymap

        km = build_default_keymap()
        keys = km.reverse_lookup("save-buffer")
        assert "C-x C-s" in keys

    def test_no_binding(self) -> None:
        from recursive_neon.editor.default_commands import build_default_keymap

        km = build_default_keymap()
        keys = km.reverse_lookup("nonexistent-command")
        assert keys == []

    def test_undo_has_cx_u(self) -> None:
        from recursive_neon.editor.default_commands import build_default_keymap

        km = build_default_keymap()
        keys = km.reverse_lookup("undo")
        assert "C-x u" in keys
        assert "C-/" in keys
