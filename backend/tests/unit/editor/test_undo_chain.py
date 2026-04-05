"""Regression tests for the undo-chain granularity bug (Phase 6l-5).

Observed in Phase 6k: pressing ``C-/`` repeatedly after editing did not
continue walking back through history.  The second ``C-/`` after a
``Backspace`` reverted the undo itself (i.e. behaved like redo) instead
of undoing the previous command group.

Root cause:

1. ``_execute_command_by_name`` unconditionally called
   ``buf.add_undo_boundary()`` before every command — including ``undo``.
2. ``add_undo_boundary`` has a chain-break side effect: when it actually
   appends a boundary, it also clears ``last_command_type == "undo"``
   and resets ``_undo_cursor``.
3. The result was that on the *second* consecutive ``C-/``, the
   ``Buffer.undo()`` call saw ``last_command_type != "undo"`` and reset
   the cursor to the end of the undo list, so it walked the reverse
   entries that the first ``C-/`` had just appended — which redoes the
   last operation.

Secondary cause (surfaced after fix 1):

4. ``Buffer.undo()`` extended its reverse entries onto the tail of the
   undo list without inserting a boundary between the original group
   and the reverse group.  If the chain was later broken by an
   intervening command, subsequent undos would walk both groups as a
   single run, collapsing two user-visible states into one keystroke.

Fix:

- Skip ``add_undo_boundary`` in the dispatcher when the command is
  ``undo`` (preserves the chain).
- In ``Buffer.undo()``, append an ``UndoBoundary`` before the reverse
  entries (no-op if the previous entry is already a boundary) so each
  undo's reverse entries form their own group.

Tests below cover both the buffer-level invariant and the
editor-level flow exactly as the tutorial user would experience it.
"""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.undo import UndoBoundary
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# Editor-level reproducers (the user-facing bug)
# ═══════════════════════════════════════════════════════════════════════


class TestConsecutiveUndoViaEditor:
    def test_two_undos_after_backspace_walks_history(self) -> None:
        """First C-/ reverts Backspace; second C-/ reverts the typing.

        This is the exact scenario from the Phase 6k walkthrough:
        type 'abc', press Backspace, then C-/ twice.  The second C-/
        used to redo the Backspace instead of continuing to undo.
        """
        h = make_harness()
        h.type_string("abc")
        assert h.buffer_text() == "abc"
        h.send_keys("Backspace")
        assert h.buffer_text() == "ab"

        h.send_keys("C-/")
        assert h.buffer_text() == "abc"  # first undo reverts the Backspace

        h.send_keys("C-/")
        assert h.buffer_text() == ""  # second undo reverts the typing

    def test_third_undo_is_noop_at_history_start(self) -> None:
        """A third C-/ at the start of history stops cleanly."""
        h = make_harness()
        h.type_string("abc")
        h.send_keys("Backspace")
        h.send_keys("C-/")
        h.send_keys("C-/")
        assert h.buffer_text() == ""
        h.send_keys("C-/")
        # Still empty; no flipping back to a later state.
        assert h.buffer_text() == ""

    def test_many_consecutive_undos_walk_back_all_groups(self) -> None:
        """Four distinct command groups → four undos reach the start."""
        h = make_harness()
        h.type_string("aaa")  # group 1
        h.send_keys("C-e")  # movement — no-op on undo list but bumps last_command_name
        h.type_string("bbb")  # group 2
        h.send_keys("C-e")
        h.type_string("ccc")  # group 3
        h.send_keys("Backspace")  # group 4
        assert h.buffer_text() == "aaabbbcc"

        # Four undos, each walks one group back.
        h.send_keys("C-/")
        assert h.buffer_text() == "aaabbbccc"
        h.send_keys("C-/")
        assert h.buffer_text() == "aaabbb"
        h.send_keys("C-/")
        assert h.buffer_text() == "aaa"
        h.send_keys("C-/")
        assert h.buffer_text() == ""

    def test_undo_then_edit_then_undo_redoes_via_linear_history(self) -> None:
        """Linear undo: type → C-/ → type → C-/ → C-/ walks the full timeline.

        Emacs's linear-undo model: after typing 'X' on top of an undo,
        the next C-/ reverts 'X', and the one after that reapplies
        'abc' (because it walks the reverse entries of the first undo
        as a separate group).
        """
        h = make_harness()
        h.type_string("abc")
        h.send_keys("C-/")
        assert h.buffer_text() == ""  # abc reverted

        h.type_string("X")
        assert h.buffer_text() == "X"

        h.send_keys("C-/")
        assert h.buffer_text() == ""  # X reverted

        h.send_keys("C-/")
        # The reverse entries from the first undo are walked here, which
        # *reapplies* the abc insertion.
        assert h.buffer_text() == "abc"

        h.send_keys("C-/")
        # Back to empty: the original abc typing group is walked.
        assert h.buffer_text() == ""


# ═══════════════════════════════════════════════════════════════════════
# Buffer-level invariant: undo() inserts a boundary before its reverse entries
# ═══════════════════════════════════════════════════════════════════════


class TestUndoBoundaryBeforeReverseEntries:
    def test_reverse_entries_are_preceded_by_boundary(self) -> None:
        """After undo(), the reverse entries form their own group.

        There must be an UndoBoundary immediately before the first
        reverse entry, so that a later chain-break + undo walks the
        reverse group and the source group as two distinct groups
        instead of one merged run.
        """
        b = Buffer()
        b.insert_string("hello")
        # Sanity: no trailing boundary yet
        assert not isinstance(b.undo_list[-1], UndoBoundary)

        before_len = len(b.undo_list)
        b.undo()
        assert b.text == ""

        # A boundary was inserted between the original entries and the
        # reverse entries.  The reverse of one UndoInsert is one
        # UndoDelete, so we expect exactly one reverse entry + one
        # boundary to have been appended.
        assert isinstance(b.undo_list[before_len], UndoBoundary)

    def test_no_duplicate_boundary_when_group_already_bounded(self) -> None:
        """If the source group is already boundary-terminated, undo()
        does not insert a second boundary (collapses consecutive Bs).
        """
        b = Buffer()
        b.insert_string("hello")
        b.add_undo_boundary()  # trailing boundary already present
        count_before = sum(1 for e in b.undo_list if isinstance(e, UndoBoundary))
        b.undo()
        count_after = sum(1 for e in b.undo_list if isinstance(e, UndoBoundary))
        # Only the pre-existing boundary; no new one added by undo().
        assert count_after == count_before


# ═══════════════════════════════════════════════════════════════════════
# Buffer-level reproducer: consecutive buf.undo() calls walk the chain
# ═══════════════════════════════════════════════════════════════════════


class TestBufferLevelUndoChain:
    def test_consecutive_undos_without_intervening_boundary(self) -> None:
        """Two consecutive buf.undo() calls walk two groups back.

        The Editor dispatcher used to break this by inserting a
        boundary before every undo (which cleared the chain state).
        Buffer.undo() on its own must chain correctly when called
        back-to-back.
        """
        b = Buffer()
        b.insert_char("a")
        b.add_undo_boundary()
        b.insert_char("b")
        b.add_undo_boundary()
        b.insert_char("c")
        assert b.text == "abc"

        b.undo()
        assert b.text == "ab"
        b.undo()
        assert b.text == "a"
        b.undo()
        assert b.text == ""
