"""Tests for registers (C-x r SPC / j / s / i).

The register commands read one more key — the register name — the way
describe-key (C-h k) reads a key. These drive the flow end-to-end through
``Editor.process_key`` (C-x, then r, then SPC/j/s/i, then the name).
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
        assert cxr.lookup("s") == "copy-to-register"  # type: ignore[union-attr]
        assert cxr.lookup("i") == "insert-register"  # type: ignore[union-attr]


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


def _send(ed: Editor, *keys: str) -> None:
    for k in keys:
        ed.process_key(k)


class TestCopyToRegister:
    """C-x r s — copy the region into a register.

    Behaviour verified against Emacs 29 via the parity harness (scenario
    23): prompt ``Copy to register: ``, silent on success (echo cleared),
    region deactivated; with no mark the error comes *after* the name is
    read (Emacs's interactive spec reads the register before evaluating
    the region).
    """

    def test_prompt_and_copy(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.set_mark(0, 0)
        ed.buffer.point.move_to(0, 4)  # region "line"
        _send(ed, "C-x", "r", "s")
        assert ed.message == "Copy to register: "
        _send(ed, "a")
        assert ed._registers["a"] == "line"
        assert ed.message == ""
        # Region deactivated (mark cleared in the always-active model).
        assert ed.buffer.mark is None
        # Buffer untouched.
        assert ed.buffer.text == CONTENT

    def test_no_mark_errors_after_name_read(self) -> None:
        ed = make_editor(CONTENT)
        _send(ed, "C-x", "r", "s", "a")
        assert ed.message == "The mark is not set now, so there is no region"
        assert "a" not in ed._registers


class TestInsertRegister:
    """C-x r i — insert a register's contents at point.

    Emacs >=28 (interactively) leaves point *after* the inserted text and
    the mark before it, echoing ``Mark set``. A point register inserts
    its buffer position as a number; an unset register reports
    ``Register does not contain text``.
    """

    def test_insert_text_register(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.set_mark(0, 0)
        ed.buffer.point.move_to(0, 4)
        _send(ed, "C-x", "r", "s", "a")  # register a := "line"
        ed.buffer.point.move_to(1, 8)  # end of "line two"
        _send(ed, "C-x", "r", "i")
        assert ed.message == "Insert register: "
        _send(ed, "a")
        assert ed.buffer.lines[1] == "line twoline"
        # Point after the insert, mark before it, "Mark set" echoed.
        assert (ed.buffer.point.line, ed.buffer.point.col) == (1, 12)
        assert ed.buffer.mark is not None
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (1, 8)
        assert ed.message == "Mark set"

    def test_insert_unset_register_errors(self) -> None:
        ed = make_editor(CONTENT)
        _send(ed, "C-x", "r", "i", "z")
        assert ed.message == "Register does not contain text"
        assert ed.buffer.text == CONTENT

    def test_insert_point_register_inserts_position_number(self) -> None:
        """Emacs's register-val-insert on a marker inserts the position.

        Point (1, 2) in "line one\\nline two\\n…" is char offset
        9 + 2 + 1 = 12 (1-based, newlines counted).
        """
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(1, 2)
        _send(ed, "C-x", "r", " ", "p")  # save point register
        ed.buffer.point.move_to(0, 0)
        _send(ed, "C-x", "r", "i", "p")
        assert ed.buffer.lines[0] == "12line one"
        assert ed.message == "Mark set"

    def test_insert_is_undoable(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.set_mark(0, 0)
        ed.buffer.point.move_to(0, 4)
        _send(ed, "C-x", "r", "s", "a")
        _send(ed, "C-x", "r", "i", "a")
        _send(ed, "C-/")
        assert ed.buffer.text == CONTENT


class TestJumpToTextRegister:
    def test_jump_to_text_register_reports_type_error(self) -> None:
        """Emacs's message — curly apostrophe included (text-quoting-style)."""
        ed = make_editor(CONTENT)
        ed.buffer.set_mark(0, 0)
        ed.buffer.point.move_to(0, 4)
        _send(ed, "C-x", "r", "s", "a")
        before = (ed.buffer.point.line, ed.buffer.point.col)
        _send(ed, "C-x", "r", "j", "a")
        assert (
            ed.message == "Register doesn’t contain a buffer position or configuration"
        )
        assert (ed.buffer.point.line, ed.buffer.point.col) == before


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
