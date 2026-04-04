"""Tests for sentence motion and kill (Phase 6f)."""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer

# ═══════════════════════════════════════════════════════════════════════
# forward_sentence
# ═══════════════════════════════════════════════════════════════════════


class TestForwardSentence:
    def test_basic_sentence(self) -> None:
        buf = Buffer.from_text("Hello world. Next sentence.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 12  # after "."

    def test_stops_at_period_followed_by_space(self) -> None:
        buf = Buffer.from_text("First. Second.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 6  # after "."

    def test_question_mark_ends_sentence(self) -> None:
        buf = Buffer.from_text("What? Yes.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 5  # after "?"

    def test_exclamation_ends_sentence(self) -> None:
        buf = Buffer.from_text("Wow! Nice.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 4  # after "!"

    def test_period_at_end_of_line(self) -> None:
        buf = Buffer.from_text("End of line.\nNext line.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 12  # after "."

    def test_period_at_end_of_buffer(self) -> None:
        buf = Buffer.from_text("Last sentence.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 14  # after "."

    def test_no_sentence_ending_goes_to_end(self) -> None:
        buf = Buffer.from_text("No punctuation here")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 19  # end of buffer

    def test_multiple_sentences(self) -> None:
        buf = Buffer.from_text("One. Two. Three.")
        buf.point.move_to(0, 0)
        buf.forward_sentence(2)
        assert buf.point.col == 9  # after second "."

    def test_across_lines(self) -> None:
        buf = Buffer.from_text("First sentence.\nSecond sentence.")
        buf.point.move_to(0, 0)
        buf.forward_sentence(2)
        assert buf.point.line == 1
        assert buf.point.col == 16  # after second "."

    def test_returns_false_at_end(self) -> None:
        buf = Buffer.from_text("Done.")
        buf.point.move_to(0, 5)  # already at end
        assert not buf.forward_sentence()

    def test_period_not_followed_by_space_skipped(self) -> None:
        """Period in 'e.g.' is not a sentence end (no trailing space)."""
        buf = Buffer.from_text("Use e.g.this notation. Done.")
        buf.point.move_to(0, 0)
        buf.forward_sentence()
        assert buf.point.col == 22  # after the "." in "notation." (col 21 is ".")


# ═══════════════════════════════════════════════════════════════════════
# backward_sentence
# ═══════════════════════════════════════════════════════════════════════


class TestBackwardSentence:
    def test_basic_backward(self) -> None:
        buf = Buffer.from_text("First. Second.")
        buf.point.move_to(0, 14)
        buf.backward_sentence()
        assert buf.point.col == 7  # start of "Second"

    def test_to_beginning_of_buffer(self) -> None:
        buf = Buffer.from_text("Only sentence here.")
        buf.point.move_to(0, 19)
        buf.backward_sentence()
        assert buf.point.col == 0

    def test_multiple_backward(self) -> None:
        buf = Buffer.from_text("One. Two. Three.")
        buf.point.move_to(0, 16)
        buf.backward_sentence(2)
        assert buf.point.col == 5  # start of "Two"

    def test_across_lines_backward(self) -> None:
        buf = Buffer.from_text("First.\nSecond.\nThird.")
        buf.point.move_to(2, 6)
        buf.backward_sentence()
        # Should land at start of "Third" line
        assert buf.point.line == 2
        assert buf.point.col == 0

    def test_returns_false_at_beginning(self) -> None:
        buf = Buffer.from_text("Hello.")
        buf.point.move_to(0, 0)
        assert not buf.backward_sentence()

    def test_from_middle_of_sentence(self) -> None:
        buf = Buffer.from_text("First sentence. Second sentence.")
        buf.point.move_to(0, 25)  # middle of "Second sentence"
        buf.backward_sentence()
        assert buf.point.col == 16  # start of "Second"


# ═══════════════════════════════════════════════════════════════════════
# kill_sentence
# ═══════════════════════════════════════════════════════════════════════


class TestKillSentence:
    def test_kill_to_sentence_end(self) -> None:
        buf = Buffer.from_text("Kill this. Keep this.")
        buf.point.move_to(0, 0)
        killed = buf.kill_sentence()
        assert killed == "Kill this."
        assert buf.text == " Keep this."

    def test_kill_puts_on_kill_ring(self) -> None:
        buf = Buffer.from_text("Kill me. Stay.")
        buf.point.move_to(0, 0)
        buf.kill_sentence()
        assert buf.kill_ring.yank() == "Kill me."

    def test_consecutive_kills_merge(self) -> None:
        buf = Buffer.from_text("One. Two. Three.")
        buf.point.move_to(0, 0)
        buf.kill_sentence()
        buf.kill_sentence()
        assert buf.kill_ring.yank() == "One. Two."

    def test_kill_from_middle(self) -> None:
        buf = Buffer.from_text("Hello world. Bye.")
        buf.point.move_to(0, 6)  # at "world"
        killed = buf.kill_sentence()
        assert killed == "world."
        assert buf.text == "Hello  Bye."

    def test_returns_empty_at_end(self) -> None:
        buf = Buffer.from_text("Done.")
        buf.point.move_to(0, 5)
        killed = buf.kill_sentence()
        assert killed == ""
