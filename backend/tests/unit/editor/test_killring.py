"""Tests for the KillRing and Buffer kill/yank commands."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.killring import KillRing
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# KillRing standalone
# ═══════════════════════════════════════════════════════════════════════


class TestKillRingBasic:
    def test_starts_empty(self):
        kr = KillRing()
        assert kr.empty
        assert kr.yank() is None
        assert kr.top is None

    def test_push_and_yank(self):
        kr = KillRing()
        kr.push("hello")
        assert kr.yank() == "hello"
        assert not kr.empty

    def test_push_empty_string_ignored(self):
        kr = KillRing()
        kr.push("")
        assert kr.empty

    def test_most_recent_first(self):
        kr = KillRing()
        kr.push("first")
        kr.push("second")
        assert kr.yank() == "second"

    def test_max_size(self):
        kr = KillRing(max_size=3)
        kr.push("a")
        kr.push("b")
        kr.push("c")
        kr.push("d")
        assert len(kr.entries) == 3
        assert kr.entries == ["d", "c", "b"]


class TestKillRingRotate:
    def test_rotate_cycles(self):
        kr = KillRing()
        kr.push("a")
        kr.push("b")
        kr.push("c")
        kr.yank()  # → "c" (index 0), entries = [c, b, a]
        assert kr.rotate() == "b"  # index 1
        assert kr.rotate() == "a"  # index 2
        assert kr.rotate() == "c"  # wraps to index 0

    def test_rotate_empty(self):
        kr = KillRing()
        assert kr.rotate() is None

    def test_yank_resets_index(self):
        kr = KillRing()
        kr.push("a")
        kr.push("b")
        kr.yank()  # index = 0
        kr.rotate()  # index = 1
        kr.yank()  # resets to 0
        assert kr.yank_index == 0


class TestKillRingAppend:
    def test_append_after(self):
        kr = KillRing()
        kr.push("hello")
        kr.append_to_top(" world")
        assert kr.top == "hello world"

    def test_append_before(self):
        kr = KillRing()
        kr.push("world")
        kr.append_to_top("hello ", before=True)
        assert kr.top == "hello world"

    def test_append_to_empty_ring(self):
        kr = KillRing()
        kr.append_to_top("hello")
        assert kr.top == "hello"

    def test_append_empty_string_ignored(self):
        kr = KillRing()
        kr.push("hello")
        kr.append_to_top("")
        assert kr.top == "hello"


# ═══════════════════════════════════════════════════════════════════════
# Buffer kill_line
# ═══════════════════════════════════════════════════════════════════════


class TestKillLine:
    def test_kill_to_end_of_line(self):
        b = Buffer.from_text("hello world")
        b.point.col = 5
        killed = b.kill_line()
        assert killed == " world"
        assert b.text == "hello"
        assert b.kill_ring.top == " world"

    def test_kill_from_beginning(self):
        b = Buffer.from_text("hello")
        killed = b.kill_line()
        assert killed == "hello"
        assert b.text == ""

    def test_kill_at_eol_joins_lines(self):
        b = Buffer.from_text("ab\ncd")
        b.point.col = 2
        killed = b.kill_line()
        assert killed == "\n"
        assert b.text == "abcd"

    def test_kill_at_end_of_buffer_returns_empty(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        killed = b.kill_line()
        assert killed == ""
        assert b.kill_ring.empty

    def test_consecutive_kills_merge(self):
        b = Buffer.from_text("hello\nworld")
        b.kill_line()  # kills "hello"
        b.kill_line()  # kills "\n"
        b.kill_line()  # kills "world"
        assert b.kill_ring.top == "hello\nworld"
        assert b.text == ""

    def test_non_consecutive_kills_separate(self):
        b = Buffer.from_text("aaa\nbbb")
        b.kill_line()  # "aaa"
        b.last_command_type = ""  # simulate intervening command
        b.point.col = 0
        b.kill_line()  # "\n"
        assert b.kill_ring.top == "\n"
        assert b.kill_ring.entries[1] == "aaa"


# ═══════════════════════════════════════════════════════════════════════
# Buffer kill_region
# ═══════════════════════════════════════════════════════════════════════


class TestKillRegion:
    def test_kill_region(self):
        b = Buffer.from_text("hello world")
        b.point.col = 0
        b.set_mark(0, 5)
        killed = b.kill_region()
        assert killed == "hello"
        assert b.text == " world"
        assert b.kill_ring.top == "hello"

    def test_kill_region_deactivates_mark(self):
        b = Buffer.from_text("hello")
        b.set_mark(0, 5)
        b.kill_region()
        # The kill deactivates the mark but keeps it (it now coincides
        # with point at the kill site; C-x C-x still works).
        assert b.mark is not None
        assert not b.region_active

    def test_kill_region_no_mark(self):
        b = Buffer.from_text("hello")
        killed = b.kill_region()
        assert killed == ""


# ═══════════════════════════════════════════════════════════════════════
# Buffer kill_word_forward
# ═══════════════════════════════════════════════════════════════════════


class TestKillWordForward:
    def test_kill_word(self):
        b = Buffer.from_text("hello world")
        killed = b.kill_word_forward()
        assert killed == "hello"
        assert b.text == " world"

    def test_kill_word_mid_word(self):
        b = Buffer.from_text("hello world")
        b.point.col = 2
        killed = b.kill_word_forward()
        assert killed == "llo"
        assert b.text == "he world"

    def test_kill_word_at_spaces(self):
        b = Buffer.from_text("   hello")
        killed = b.kill_word_forward()
        assert killed == "   hello"
        assert b.text == ""

    def test_kill_word_at_end_of_line(self):
        b = Buffer.from_text("hello\nworld")
        b.point.col = 5
        killed = b.kill_word_forward()
        # ``M-d`` follows ``forward-word``: skip the newline, then
        # consume the next word — matches GNU Emacs's ``kill-word``.
        assert killed == "\nworld"
        assert b.text == "hello"

    def test_kill_word_at_end_of_buffer(self):
        b = Buffer.from_text("hello")
        b.point.col = 5
        killed = b.kill_word_forward()
        assert killed == ""

    def test_consecutive_kill_words_merge(self):
        b = Buffer.from_text("aaa bbb ccc")
        b.kill_word_forward()  # "aaa"
        b.kill_word_forward()  # " bbb"
        assert b.kill_ring.top == "aaa bbb"


# ═══════════════════════════════════════════════════════════════════════
# Buffer yank / yank_pop
# ═══════════════════════════════════════════════════════════════════════


class TestYank:
    def test_yank(self):
        b = Buffer.from_text("world")
        b.kill_ring.push("hello ")
        text = b.yank()
        assert text == "hello "
        assert b.text == "hello world"

    def test_yank_empty_ring(self):
        b = Buffer()
        assert b.yank() is None

    def test_yank_sets_command_type(self):
        b = Buffer()
        b.kill_ring.push("x")
        b.yank()
        assert b.last_command_type == "yank"


class TestYankPop:
    def test_yank_pop_replaces(self):
        b = Buffer()
        b.kill_ring.push("first")
        b.kill_ring.push("second")
        b.yank()  # inserts "second"
        assert b.text == "second"
        b.yank_pop()  # replaces with "first"
        assert b.text == "first"

    def test_yank_pop_cycles(self):
        b = Buffer()
        b.kill_ring.push("a")
        b.kill_ring.push("b")
        b.kill_ring.push("c")
        b.yank()  # "c"
        b.yank_pop()  # "a"
        b.yank_pop()  # "b"
        b.yank_pop()  # "c" (wraps)
        assert b.text == "c"

    def test_yank_pop_without_yank(self):
        b = Buffer()
        b.kill_ring.push("hello")
        b.last_command_type = "other"
        assert b.yank_pop() is None

    def test_yank_pop_with_surrounding_text(self):
        b = Buffer.from_text("[]")
        b.kill_ring.push("first")
        b.kill_ring.push("second")
        b.point.col = 1
        b.yank()  # "[second]"
        assert b.text == "[second]"
        b.yank_pop()  # "[first]"
        assert b.text == "[first]"


# ═══════════════════════════════════════════════════════════════════════
# Kill + undo integration
# ═══════════════════════════════════════════════════════════════════════


class TestKillUndoIntegration:
    def test_undo_kill_line(self):
        b = Buffer.from_text("hello world")
        b.point.col = 5
        b.kill_line()
        assert b.text == "hello"
        b.undo()
        assert b.text == "hello world"

    def test_undo_kill_region(self):
        b = Buffer.from_text("hello world")
        b.set_mark(0, 5)
        b.point.col = 0
        b.kill_region()
        assert b.text == " world"
        b.undo()
        assert b.text == "hello world"

    def test_undo_yank(self):
        b = Buffer()
        b.kill_ring.push("hello")
        b.yank()
        assert b.text == "hello"
        b.undo()
        assert b.text == ""


# ═══════════════════════════════════════════════════════════════════════
# Kill coalescing + yank-pop through the editor dispatch
# ═══════════════════════════════════════════════════════════════════════
#
# The buffer-level tests above fake the "intervening command" by manually
# resetting ``last_command_type`` (see ``test_non_consecutive_kills_separate``).
# These editor-level tests drive the real dispatch path instead: the
# dispatcher is what must reset the marker when a non-kill command breaks a
# kill run. A regression here was that kills separated by a cursor move
# wrongly merged into a single kill-ring entry (parity scenario 13).


class TestKillCoalescingViaEditor:
    def test_kills_separated_by_move_do_not_merge(self) -> None:
        """C-k C-n C-k C-n C-k → three separate ring entries.

        GNU Emacs starts a new kill-ring entry once a non-kill command
        breaks the kill run; the C-n between kills is exactly such a
        break. neon-edit's dispatch clears ``last_command_type`` on any
        non-coalescing, non-undo command so the next kill pushes instead
        of appending.
        """
        h = make_harness("one\ntwo\nthree\nfour\n")
        h.send_keys("C-k", "C-n", "C-k", "C-n", "C-k")
        # Newest first — not the merged "onetwothree" the bug produced.
        assert h.editor.buffer.kill_ring.entries == ["three", "two", "one"]

    def test_consecutive_kills_still_merge(self) -> None:
        """Back-to-back C-k stay in one coalesce run and append.

        The reset must only fire on the run *break*, not between
        consecutive kills, or every kill would become its own entry.
        """
        h = make_harness("hello world\n")
        h.send_keys("C-k", "C-k")  # kill "hello world", then the "\n"
        assert h.editor.buffer.kill_ring.entries == ["hello world\n"]

    def test_yank_pop_cycles_via_editor(self) -> None:
        """C-y then repeated M-y walk the ring and wrap, in place."""
        h = make_harness("one\ntwo\nthree\nfour\n")
        h.send_keys("C-k", "C-n", "C-k", "C-n", "C-k")  # ring [three, two, one]
        # Point sits on the (now empty) third line; yank lands there.
        h.send_keys("C-y")
        assert h.buffer_text() == "\n\nthree\nfour\n"
        h.send_keys("M-y")
        assert h.buffer_text() == "\n\ntwo\nfour\n"
        h.send_keys("M-y")
        assert h.buffer_text() == "\n\none\nfour\n"
        h.send_keys("M-y")  # wraps back to the newest
        assert h.buffer_text() == "\n\nthree\nfour\n"

    def test_copy_after_move_pushes_new_entry_not_append(self) -> None:
        """M-w after an intervening move PUSHES, it does not append.

        kill-ring-save (M-w) inspects ``last_command_type`` to decide
        append-vs-push, but needs a region — which means a mark-set/move
        between the kill and the M-w. GNU Emacs breaks the kill-append
        chain across that move, so the copied region becomes its own ring
        entry. Verified pixel-perfect against Emacs via the parity harness
        (the kill→C-n→region→M-w probe). This guards the dispatch reset for
        the kill-ring-save path specifically, which has ``coalesce_key=None``
        rather than ``"kill"``.
        """
        h = make_harness("alpha\nbeta\ngamma\n")
        h.send_keys("C-k")  # kill "alpha"
        h.send_keys("C-n")  # move to line 2 — breaks the kill chain
        h.editor.buffer.set_mark(1, 0)
        h.send_keys("M-f")  # select "beta"
        h.send_keys("M-w")  # copy "beta"
        # Two separate entries, not the merged "betaalpha"/"alphabeta".
        assert h.editor.buffer.kill_ring.entries == ["beta", "alpha"]

    def test_yank_pop_does_not_rotate_when_not_after_yank(self) -> None:
        """M-y only rotates immediately after a yank.

        A C-b breaks the yank run, so the following M-y must not touch
        the buffer — it opens the ``yank-from-kill-ring`` minibuffer
        instead (GNU Emacs >= 28; see TestYankFromKillRing below).
        """
        h = make_harness("one\ntwo\nthree\nfour\n")
        h.send_keys("C-k", "C-n", "C-k", "C-n", "C-k")
        h.send_keys("C-y")  # yank "three"
        after_yank = h.buffer_text()
        h.send_keys("C-b")  # break the yank run
        h.send_keys("M-y")  # not after a yank → picker, no rotation
        assert h.buffer_text() == after_yank
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Yank from kill-ring: "


class TestYankFromKillRing:
    """M-y when the previous command was not a yank (GNU Emacs >= 28).

    Behaviour verified against Emacs 29 via the parity harness (scenario
    22): a ``Yank from kill-ring: `` minibuffer whose M-p/M-n history and
    TAB completion candidates are the ring entries; RET inserts the
    content literally at point and pushes a mark (``Mark set``), even for
    empty input; an immediately following M-y re-prompts rather than
    rotating; an empty ring short-circuits with ``Kill ring is empty``.
    """

    @staticmethod
    def _harness_with_ring() -> object:
        h = make_harness("one\ntwo\nthree\nrest\n")
        h.send_keys("C-k", "C-n", "C-k", "C-n", "C-k")  # ring [three, two, one]
        h.send_keys("M->")  # somewhere neutral; breaks the kill run
        return h

    def test_m_p_ret_inserts_newest_entry_and_pushes_mark(self) -> None:
        h = self._harness_with_ring()
        h.send_keys("M-y", "M-p", "Enter")
        assert h.buffer_text() == "\n\n\nrest\nthree"
        assert h.editor.message == "Mark set"
        # Mark at the insert start, point at the end of the insert.
        assert h.editor.buffer.mark is not None
        assert (h.editor.buffer.mark.line, h.editor.buffer.mark.col) == (4, 0)
        assert h.point() == (4, 5)

    def test_m_p_m_p_recalls_older_entry(self) -> None:
        h = self._harness_with_ring()
        h.send_keys("M-y", "M-p", "M-p", "Enter")
        assert h.buffer_text() == "\n\n\nrest\ntwo"

    def test_empty_ret_inserts_nothing_but_pushes_mark(self) -> None:
        h = self._harness_with_ring()
        before = h.buffer_text()
        h.send_keys("M-y", "Enter")
        assert h.buffer_text() == before
        assert h.editor.message == "Mark set"
        assert h.editor.buffer.mark is not None

    def test_typed_text_is_inserted_literally(self) -> None:
        """completing-read runs without require-match: any input goes in."""
        h = self._harness_with_ring()
        h.send_keys("M-y")
        h.type_string("xyz")
        h.send_keys("Enter")
        assert h.buffer_text() == "\n\n\nrest\nxyz"

    def test_immediate_m_y_after_accept_reprompts(self) -> None:
        """The accept is not a yank: the next M-y re-opens the picker."""
        h = self._harness_with_ring()
        h.send_keys("M-y", "M-p", "Enter")  # insert "three"
        h.send_keys("M-y")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Yank from kill-ring: "
        assert h.buffer_text() == "\n\n\nrest\nthree"  # no rotation happened

    def test_empty_ring_short_circuits(self) -> None:
        h = make_harness("rest\n")
        h.send_keys("M-y")
        assert h.editor.minibuffer is None
        assert h.editor.message == "Kill ring is empty"

    def test_c_g_cancels_without_touching_buffer(self) -> None:
        h = self._harness_with_ring()
        before = h.buffer_text()
        h.send_keys("M-y", "M-p", "C-g")
        assert h.editor.minibuffer is None
        assert h.buffer_text() == before

    def test_tab_completes_over_ring_entries(self) -> None:
        """TAB completion candidates are the ring entries (prefix match)."""
        h = self._harness_with_ring()
        h.send_keys("M-y")
        h.type_string("tw")
        h.send_keys("Tab")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.text == "two"

    def test_rotate_still_works_right_after_yank(self) -> None:
        """Regression guard: C-y M-y still rotates in place."""
        h = self._harness_with_ring()
        h.send_keys("C-y", "M-y")
        assert h.editor.minibuffer is None
        assert h.buffer_text() == "\n\n\nrest\ntwo"

    def test_multiline_entry_recall_renders_escaped_and_inserts_raw(self) -> None:
        """A recalled multi-line kill shows as ``^J`` in the one-row widget.

        GNU Emacs grows the minibuffer to multiple rows for a multi-line
        recall; neon-edit's minibuffer is a single-row widget (documented
        deviation in ``view.py``), so the embedded newline must render as
        the ``^J`` control-char notation rather than a raw "\\n" that
        would corrupt the screen rows. The *inserted* text keeps the real
        newline.
        """
        h = make_harness("one\ntwo\nthree\nrest\n")
        h.editor.buffer.set_mark(0, 0)
        h.send_keys("C-n", "C-n", "C-w")  # kill "one\ntwo\n" as one entry
        h.send_keys("M->", "M-y", "M-p")
        assert h.message_line() == "Yank from kill-ring: one^Jtwo^J"
        assert "\n" not in h.message_line()
        h.send_keys("Enter")
        assert h.buffer_text() == "three\nrest\none\ntwo\n"
