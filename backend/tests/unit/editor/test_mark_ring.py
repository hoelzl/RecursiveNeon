"""Tests for the inactive mark, mark ring, and region rendering.

Semantics verified against GNU Emacs 29 via the parity probe and
scenarios 30/31: ``push_mark`` is inactive, C-SPC activates,
C-SPC C-SPC deactivates ("Mark deactivated"), C-u C-SPC pops/rotates
the ring ("Mark popped" only when point is already at the mark), C-g
and M-w deactivate without clearing, C-x C-x reactivates, and the
active region renders with the ``region`` face extending to the window
edge on rows where it spans the newline.
"""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor

from .harness import make_harness


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestBufferMarkModel:
    def test_set_mark_activates(self) -> None:
        b = Buffer.from_text("hello")
        b.set_mark(0, 2)
        assert b.mark_active
        assert b.region_active

    def test_push_mark_is_inactive(self) -> None:
        b = Buffer.from_text("hello")
        b.push_mark(0, 2)
        assert b.mark is not None
        assert not b.mark_active
        assert not b.region_active

    def test_push_mark_saves_old_mark_on_ring(self) -> None:
        b = Buffer.from_text("hello\nworld")
        b.set_mark(0, 1)
        b.push_mark(1, 2)
        assert [(m.line, m.col) for m in b.mark_ring] == [(0, 1)]
        assert (b.mark.line, b.mark.col) == (1, 2)

    def test_ring_caps_at_sixteen(self) -> None:
        b = Buffer.from_text("x" * 40)
        for col in range(20):
            b.push_mark(0, col)
        assert len(b.mark_ring) == 16

    def test_pop_mark_rotates(self) -> None:
        b = Buffer.from_text("aa\nbb\ncc")
        b.push_mark(0, 0)
        b.push_mark(1, 0)
        b.push_mark(2, 0)  # mark (2,0), ring [(1,0), (0,0)]
        b.pop_mark()  # mark <- (1,0), ring [(0,0), (2,0)]
        assert (b.mark.line, b.mark.col) == (1, 0)
        b.pop_mark()
        assert (b.mark.line, b.mark.col) == (0, 0)
        b.pop_mark()  # full rotation
        assert (b.mark.line, b.mark.col) == (2, 0)

    def test_region_commands_work_with_inactive_mark(self) -> None:
        """Emacs's mark-even-if-inactive: C-w kills via the inactive mark."""
        b = Buffer.from_text("hello world")
        b.push_mark(0, 5)
        assert not b.region_active
        assert b.kill_region() == "hello"

    def test_deactivate_keeps_position(self) -> None:
        b = Buffer.from_text("hello")
        b.set_mark(0, 3)
        b.deactivate_mark()
        assert (b.mark.line, b.mark.col) == (0, 3)
        assert not b.region_active


class TestSetMarkCommand:
    def test_c_spc_pushes_and_activates(self) -> None:
        ed = make_editor("hello world")
        ed.process_key("C-space")
        assert ed.message == "Mark set"
        assert ed.buffer.region_active

    def test_double_c_spc_deactivates(self) -> None:
        ed = make_editor("hello world")
        ed.process_key("C-space")
        ed.process_key("C-space")
        assert ed.message == "Mark deactivated"
        assert ed.buffer.mark is not None
        assert not ed.buffer.region_active

    def test_c_u_c_spc_jumps_to_mark(self) -> None:
        ed = make_editor("hello\nworld\nthird")
        ed.process_key("C-space")
        ed.process_key("C-space")  # mark at (0,0), inactive
        ed.buffer.point.move_to(2, 3)
        ed.process_key("C-u")
        ed.process_key("C-space")
        assert (ed.buffer.point.line, ed.buffer.point.col) == (0, 0)
        # Silent on a real jump (no "Mark popped").
        assert ed.message == ""

    def test_c_u_c_spc_at_mark_says_mark_popped(self) -> None:
        ed = make_editor("hello")
        ed.process_key("C-space")
        ed.process_key("C-space")
        ed.process_key("C-u")
        ed.process_key("C-space")  # point already at the mark
        assert ed.message == "Mark popped"

    def test_c_u_c_spc_rotates_the_ring(self) -> None:
        ed = make_editor("aa\nbb\ncc\ndd")
        for ln in range(3):
            ed.buffer.point.move_to(ln, 0)
            ed.process_key("C-space")
            ed.process_key("C-space")
        ed.buffer.point.move_to(3, 0)
        for expected_line in (2, 1, 0, 2):
            ed.process_key("C-u")
            ed.process_key("C-space")
            assert ed.buffer.point.line == expected_line

    def test_c_u_c_spc_without_mark_errors(self) -> None:
        ed = make_editor("hello")
        ed.process_key("C-u")
        ed.process_key("C-space")
        assert ed.message == "No mark set in this buffer"


class TestActivationLifecycle:
    def test_c_g_deactivates_without_clearing(self) -> None:
        ed = make_editor("hello world")
        ed.process_key("C-space")
        ed.process_key("M-f")
        assert ed.buffer.region_active
        ed.process_key("C-g")
        assert not ed.buffer.region_active
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (0, 0)

    def test_m_w_deactivates_and_keeps_mark(self) -> None:
        ed = make_editor("hello world")
        ed.process_key("C-space")
        ed.process_key("M-f")
        ed.process_key("M-w")
        assert not ed.buffer.region_active
        assert ed.buffer.mark is not None

    def test_c_x_c_x_reactivates(self) -> None:
        ed = make_editor("hello world")
        ed.process_key("C-space")
        ed.process_key("M-f")
        ed.process_key("C-g")  # deactivate
        ed.process_key("C-x")
        ed.process_key("C-x")
        assert ed.buffer.region_active
        assert (ed.buffer.point.line, ed.buffer.point.col) == (0, 0)
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (0, 5)

    def test_big_motion_push_is_inactive(self) -> None:
        ed = make_editor("hello\nworld")
        ed.process_key("M->")
        assert ed.message == "Mark set"
        assert ed.buffer.mark is not None
        assert not ed.buffer.region_active

    def test_yank_push_is_inactive(self) -> None:
        ed = make_editor("")
        ed.buffer.kill_ring.push("xy")
        ed.process_key("C-y")
        assert not ed.buffer.region_active
        assert ed.buffer.mark is not None


def _highlight_cols(h, row: int) -> list[int]:
    """Columns of *row* styled with the region face's background."""
    raw = h._screen.lines[row]
    cols: list[int] = []
    col = 0
    lit = False
    i = 0
    while i < len(raw):
        if raw[i] == "\033":
            j = raw.index("m", i)
            seq = raw[i : j + 1]
            if "48;5;" in seq:
                lit = True
            elif seq == "\033[0m":
                lit = False
            i = j + 1
            continue
        if lit:
            cols.append(col)
        col += 1
        i += 1
    return cols


class TestRegionRendering:
    def test_active_region_highlights_text(self) -> None:
        h = make_harness("alpha beta\ngamma\n", width=40, height=10)
        h.send_keys("C-space", "M-f")
        assert _highlight_cols(h, 0) == [0, 1, 2, 3, 4]

    def test_inactive_mark_renders_nothing(self) -> None:
        h = make_harness("alpha beta\ngamma\n", width=40, height=10)
        h.send_keys("C-space", "M-f", "C-g")
        assert _highlight_cols(h, 0) == []

    def test_multiline_region_extends_to_window_edge(self) -> None:
        """Rows whose region segment spans the newline highlight to the
        window edge (the Emacs region face's :extend)."""
        h = make_harness("alpha beta\ngamma\nzeta\n", width=40, height=10)
        h.send_keys(*["C-f"] * 5)  # point (0,5)
        h.send_keys("C-space")
        h.send_keys("C-n", "C-n", "C-a", "C-f", "C-f", "C-f")  # point (2,3)
        assert _highlight_cols(h, 0) == list(range(5, 40))
        assert _highlight_cols(h, 1) == list(range(0, 40))
        assert _highlight_cols(h, 2) == [0, 1, 2]
