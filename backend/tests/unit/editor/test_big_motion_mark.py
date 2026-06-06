"""``beginning-of-buffer`` / ``end-of-buffer`` push a mark (GNU Emacs).

M-< and M-> set the mark before jumping — so the user can return — unless
a prefix arg was given or the region is already active. ``push-mark``
echoes ``Mark set``. Surfaced by parity scenario 15.

(Deviation: neon-edit has no inactive-mark concept, so the pushed mark is
active. That is invisible to the text-only parity harness; these tests
pin the position + message, not the highlight.)
"""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


CONTENT = "line one\nline two\nline three\nline four\n"


class TestBigMotionPushesMark:
    def test_beginning_of_buffer_pushes_mark(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 5)
        ed.process_key("M-<")
        assert (ed.buffer.point.line, ed.buffer.point.col) == (0, 0)
        assert ed.message == "Mark set"
        assert ed.buffer.mark is not None
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (2, 5)

    def test_end_of_buffer_pushes_mark(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(0, 3)
        ed.process_key("M->")
        assert ed.message == "Mark set"
        assert ed.buffer.mark is not None
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (0, 3)

    def test_no_mark_pushed_when_region_already_active(self) -> None:
        """Emacs skips push-mark when the region is active (mark exists)."""
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 5)
        ed.buffer.set_mark(2, 0)  # region active
        ed.process_key("M-<")
        assert (ed.buffer.point.line, ed.buffer.point.col) == (0, 0)
        # The active mark is untouched and no "Mark set" was emitted.
        assert (ed.buffer.mark.line, ed.buffer.mark.col) == (2, 0)
        assert ed.message != "Mark set"

    def test_no_mark_pushed_with_prefix_arg(self) -> None:
        ed = make_editor(CONTENT)
        ed.buffer.point.move_to(2, 5)
        ed.execute_command("end-of-buffer", prefix=4)
        assert ed.buffer.mark is None
        assert ed.message != "Mark set"
