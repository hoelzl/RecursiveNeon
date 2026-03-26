"""Tests for the command registry and Editor dispatch."""

from __future__ import annotations

from recursive_neon.editor.commands import COMMANDS, get_command
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.keymap import Keymap


# ═══════════════════════════════════════════════════════════════════════
# Command registry
# ═══════════════════════════════════════════════════════════════════════


class TestCommandRegistry:
    def test_default_commands_registered(self):
        # Importing default_commands populates COMMANDS
        assert "forward-char" in COMMANDS
        assert "backward-char" in COMMANDS
        assert "self-insert-command" in COMMANDS
        assert "kill-line" in COMMANDS
        assert "undo" in COMMANDS
        assert "quit-editor" in COMMANDS

    def test_get_command(self):
        cmd = get_command("forward-char")
        assert cmd is not None
        assert cmd.name == "forward-char"
        assert cmd.doc != ""

    def test_get_nonexistent_command(self):
        assert get_command("nonexistent-command") is None

    def test_command_count(self):
        # Sanity check: we should have a reasonable number of commands
        assert len(COMMANDS) >= 20


# ═══════════════════════════════════════════════════════════════════════
# Editor creation
# ═══════════════════════════════════════════════════════════════════════


def make_editor(text: str = "") -> Editor:
    """Helper to create an editor with a default keymap and buffer."""
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestEditorCreation:
    def test_default_buffer_created_on_access(self):
        ed = Editor()
        buf = ed.buffer
        assert buf.name == "*scratch*"

    def test_create_buffer(self):
        ed = Editor()
        buf = ed.create_buffer(name="test", text="hello")
        assert buf.name == "test"
        assert buf.text == "hello"
        assert ed.buffer is buf

    def test_buffers_share_kill_ring(self):
        ed = Editor()
        b1 = ed.create_buffer(name="a")
        b2 = ed.create_buffer(name="b")
        assert b1.kill_ring is b2.kill_ring
        assert b1.kill_ring is ed.kill_ring

    def test_switch_buffer(self):
        ed = Editor()
        ed.create_buffer(name="a", text="aaa")
        ed.create_buffer(name="b", text="bbb")
        assert ed.buffer.name == "b"
        assert ed.switch_to_buffer("a")
        assert ed.buffer.name == "a"

    def test_switch_nonexistent_buffer(self):
        ed = Editor()
        ed.create_buffer(name="a")
        assert not ed.switch_to_buffer("nonexistent")


# ═══════════════════════════════════════════════════════════════════════
# Key dispatch — movement
# ═══════════════════════════════════════════════════════════════════════


class TestEditorMovement:
    def test_forward_char(self):
        ed = make_editor("hello")
        ed.process_key("C-f")
        assert ed.buffer.point.col == 1

    def test_backward_char(self):
        ed = make_editor("hello")
        ed.buffer.point.col = 3
        ed.process_key("C-b")
        assert ed.buffer.point.col == 2

    def test_next_line(self):
        ed = make_editor("aaa\nbbb")
        ed.process_key("C-n")
        assert ed.buffer.point.line == 1

    def test_previous_line(self):
        ed = make_editor("aaa\nbbb")
        ed.buffer.point.line = 1
        ed.process_key("C-p")
        assert ed.buffer.point.line == 0

    def test_beginning_of_line(self):
        ed = make_editor("hello")
        ed.buffer.point.col = 3
        ed.process_key("C-a")
        assert ed.buffer.point.col == 0

    def test_end_of_line(self):
        ed = make_editor("hello")
        ed.process_key("C-e")
        assert ed.buffer.point.col == 5

    def test_arrow_keys(self):
        ed = make_editor("hello\nworld")
        ed.process_key("ArrowRight")
        assert ed.buffer.point.col == 1
        ed.process_key("ArrowDown")
        assert ed.buffer.point.line == 1
        ed.process_key("ArrowLeft")
        assert ed.buffer.point.col == 0
        ed.process_key("ArrowUp")
        assert ed.buffer.point.line == 0


# ═══════════════════════════════════════════════════════════════════════
# Key dispatch — self insert
# ═══════════════════════════════════════════════════════════════════════


class TestEditorSelfInsert:
    def test_printable_char(self):
        ed = make_editor()
        ed.process_key("h")
        ed.process_key("i")
        assert ed.buffer.text == "hi"

    def test_space(self):
        ed = make_editor("ab")
        ed.buffer.point.col = 1
        ed.process_key(" ")
        assert ed.buffer.text == "a b"

    def test_enter_inserts_newline(self):
        ed = make_editor("ab")
        ed.buffer.point.col = 1
        ed.process_key("Enter")
        assert ed.buffer.lines == ["a", "b"]


# ═══════════════════════════════════════════════════════════════════════
# Key dispatch — editing
# ═══════════════════════════════════════════════════════════════════════


class TestEditorEditing:
    def test_delete_forward(self):
        ed = make_editor("hello")
        ed.process_key("C-d")
        assert ed.buffer.text == "ello"

    def test_backspace(self):
        ed = make_editor("hello")
        ed.buffer.point.col = 5
        ed.process_key("Backspace")
        assert ed.buffer.text == "hell"

    def test_kill_line(self):
        ed = make_editor("hello world")
        ed.buffer.point.col = 5
        ed.process_key("C-k")
        assert ed.buffer.text == "hello"
        assert ed.buffer.kill_ring.top == " world"

    def test_kill_region(self):
        ed = make_editor("hello world")
        ed.process_key("C-space")  # set mark
        ed.buffer.point.col = 5
        ed.process_key("C-w")
        assert ed.buffer.text == " world"

    def test_yank(self):
        ed = make_editor("hello")
        ed.buffer.kill_ring.push("XY")
        ed.process_key("C-y")
        assert ed.buffer.text == "XYhello"


# ═══════════════════════════════════════════════════════════════════════
# Key dispatch — undo
# ═══════════════════════════════════════════════════════════════════════


class TestEditorUndo:
    def test_undo_insert(self):
        ed = make_editor()
        ed.process_key("a")
        ed.process_key("b")
        assert ed.buffer.text == "ab"
        ed.process_key("C-/")
        # Self-insert same command name → no boundary between a and b
        assert ed.buffer.text == ""

    def test_undo_after_different_commands(self):
        ed = make_editor("hello")
        # Forward char, then delete — different commands → boundary
        ed.process_key("C-f")
        ed.process_key("C-d")
        assert ed.buffer.text == "hllo"
        ed.process_key("C-/")  # undo delete
        assert ed.buffer.text == "hello"


# ═══════════════════════════════════════════════════════════════════════
# Prefix keys
# ═══════════════════════════════════════════════════════════════════════


class TestEditorPrefixKeys:
    def test_c_x_c_c_quits(self):
        ed = make_editor()
        assert ed.running
        ed.process_key("C-x")
        assert ed._pending_keymap is not None  # waiting for second key
        ed.process_key("C-c")
        assert not ed.running

    def test_c_x_shows_message(self):
        ed = make_editor()
        ed.process_key("C-x")
        assert "C-x" in ed.message

    def test_unknown_after_prefix(self):
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("z")  # unbound in C-x map
        assert "undefined" in ed.message

    def test_c_g_cancels(self):
        ed = make_editor()
        ed.process_key("C-space")
        assert ed.buffer.mark is not None
        ed.process_key("C-g")
        assert ed.buffer.mark is None
        assert ed.message == "Quit"


# ═══════════════════════════════════════════════════════════════════════
# Prefix argument (C-u)
# ═══════════════════════════════════════════════════════════════════════


class TestEditorPrefixArg:
    def test_c_u_default_is_4(self):
        ed = make_editor("hello world")
        ed.process_key("C-u")
        ed.process_key("C-f")
        assert ed.buffer.point.col == 4

    def test_c_u_c_u_is_16(self):
        ed = make_editor("a" * 20)
        ed.process_key("C-u")
        ed.process_key("C-u")
        ed.process_key("C-f")
        assert ed.buffer.point.col == 16

    def test_c_u_with_digits(self):
        ed = make_editor("hello world")
        ed.process_key("C-u")
        ed.process_key("3")
        ed.process_key("C-f")
        assert ed.buffer.point.col == 3

    def test_c_u_with_multi_digit(self):
        ed = make_editor("a" * 20)
        ed.process_key("C-u")
        ed.process_key("1")
        ed.process_key("2")
        ed.process_key("C-f")
        assert ed.buffer.point.col == 12

    def test_c_u_self_insert(self):
        ed = make_editor()
        ed.process_key("C-u")
        ed.process_key("x")
        assert ed.buffer.text == "xxxx"

    def test_prefix_cleared_after_command(self):
        ed = make_editor("hello")
        ed.process_key("C-u")
        ed.process_key("C-f")
        # Now prefix should be cleared
        ed.process_key("C-f")
        assert ed.buffer.point.col == 5  # 4 + 1


# ═══════════════════════════════════════════════════════════════════════
# Unknown keys
# ═══════════════════════════════════════════════════════════════════════


class TestEditorUnknownKeys:
    def test_unknown_control_key(self):
        ed = make_editor()
        ed.process_key("C-z")
        assert "undefined" in ed.message

    def test_unknown_key_clears_prefix_arg(self):
        ed = make_editor("hello")
        ed.process_key("C-u")
        ed.process_key("C-z")  # unknown
        # Prefix should be cleared
        ed.process_key("C-f")
        assert ed.buffer.point.col == 1  # not 4


# ═══════════════════════════════════════════════════════════════════════
# execute_command (programmatic)
# ═══════════════════════════════════════════════════════════════════════


class TestEditorExecuteCommand:
    def test_execute_known_command(self):
        ed = make_editor("hello")
        assert ed.execute_command("forward-char", prefix=3)
        assert ed.buffer.point.col == 3

    def test_execute_unknown_command(self):
        ed = make_editor()
        assert not ed.execute_command("nonexistent")
