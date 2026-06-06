"""Tests for point registers (C-x r SPC / C-x r j).

The register commands read one more key — the register name — the way
describe-key (C-h k) reads a key. These drive the flow end-to-end through
``Editor.process_key`` (C-x, then r, then SPC/j, then the name).
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


CONTENT = "line one\nline two\nline three\nline four\n"


class TestRegisterBindings:
    def test_cxr_is_a_prefix(self) -> None:
        ed = make_editor("hi")
        assert ed.global_keymap.lookup("C-x") is not None
        cx = ed.global_keymap.lookup("C-x")
        cxr = cx.lookup("r")  # type: ignore[union-attr]
        assert cxr is not None
        assert cxr.lookup(" ") == "point-to-register"  # type: ignore[union-attr]
        assert cxr.lookup("j") == "jump-to-register"  # type: ignore[union-attr]


class TestPointToRegister:
    def test_prompt_shown_and_session_armed(self) -> None:
        ed = make_editor(CONTENT)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        assert ed.message == "Point to register: "
        assert ed._register_session is not None
        assert ed._register_session.action == "point"

    def test_name_key_saves_point_and_clears_session(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 4)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("a")  # register name
        assert ed._register_session is None
        assert ed._registers["a"] == (2, 4)
        # The name key is consumed, not self-inserted.
        assert ed.buffer.text == CONTENT
        assert ed.message == ""


class TestJumpToRegister:
    def test_round_trip_restores_point(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 10)  # end of "line three"
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("a")
        # Move away, then jump back.
        ed.buffer.point.move_to(0, 0)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key("j")
        assert ed.message == "Jump to register: "
        assert ed._register_session is not None
        assert ed._register_session.action == "jump"
        ed.process_key("a")
        assert (ed.buffer.point.line, ed.buffer.point.col) == (2, 10)
        assert ed._register_session is None

    def test_jump_pushes_mark_at_old_point(self) -> None:
        """GNU Emacs's C-x r j pushes a mark at the old point (so you can
        return) and echoes "Mark set"."""
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 10)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("a")
        ed.buffer.point.move_to(0, 0)  # the point we jump *from*
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key("j")
        ed.process_key("a")
        assert ed.message == "Mark set"
        assert ed.buffer.mark is not None
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (0, 0)

    def test_jump_to_unset_register_reports_empty(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(1, 2)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key("j")
        ed.process_key("z")  # never saved
        assert "Register z is empty" in ed.message
        # Point unchanged, and no mark was pushed (we bail before the jump).
        assert (ed.buffer.point.line, ed.buffer.point.col) == (1, 2)
        assert ed.buffer.mark is None


class TestRegisterCancel:
    def test_cg_cancels_the_name_read(self) -> None:
        ed = make_editor(CONTENT)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("C-g")  # cancel before naming
        assert ed._register_session is None
        assert ed.message == "Quit"
        assert ed._registers == {}

    def test_reset_transient_state_clears_session(self) -> None:
        ed = make_editor(CONTENT)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        assert ed._register_session is not None
        ed._reset_transient_state()
        assert ed._register_session is None


class TestRegisterIndependence:
    def test_two_registers_are_independent(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(0, 3)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("a")
        ed.buffer.point.move_to(3, 5)
        ed.process_key("C-x")
        ed.process_key("r")
        ed.process_key(" ")
        ed.process_key("b")
        assert ed._registers["a"] == (0, 3)
        assert ed._registers["b"] == (3, 5)
