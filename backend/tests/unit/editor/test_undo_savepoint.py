"""Save-point tracking through undo/redo (Emacs ``(t . TIME)`` analogue).

GNU Emacs records, in the undo list itself, the moments at which the
buffer last matched its saved state (``record_first_change`` pushes a
``(t . TIME)`` entry on the first change while unmodified), and
``primitive-undo`` clears the buffer-modified flag when undo walks back
across such an entry — so undoing back to the saved-on-disk content
flips the modeline mnemonic from ``**`` back to ``--``.  Stale entries
(the file was saved again since) are ignored via a modtime comparison.

neon-edit mirrors this with :class:`UndoSavePoint` entries carrying a
*save generation* (``Buffer._save_tick``, bumped by ``mark_saved``):

- first change while unmodified pushes a marker (``_note_modification``)
- ``undo()`` clears ``modified`` when the walked group crosses a marker
  of the current generation
- ``undo()`` plants a marker in the reverse (redo) group when the
  pre-undo state was unmodified, so redoing back to the save point also
  restores the flag
- ``mark_saved()`` bumps the generation, staling markers recorded
  against earlier save states

Surfaced by parity scenario 09 (checkpoints ``after-undo-AB`` /
``after-undo-exhausted``), where GNU Emacs 29.3 shows ``--`` after undo
restores the visited file's content and neon-edit used to keep ``**``.
"""

from __future__ import annotations

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.undo import UndoSavePoint
from tests.unit.editor.harness import make_harness

# ═══════════════════════════════════════════════════════════════════════
# Buffer-level semantics
# ═══════════════════════════════════════════════════════════════════════


class TestUndoToSavedState:
    def test_undo_back_to_initial_content_clears_modified(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        assert buf.modified
        assert buf.undo()
        assert buf.text == "hello"
        assert not buf.modified

    def test_undo_partway_back_keeps_modified(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        buf.add_undo_boundary()
        buf.insert_string("CD")
        assert buf.undo()  # reverts CD only — still one edit away
        assert buf.modified

    def test_undo_exhausted_stays_unmodified(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        assert buf.undo()
        assert not buf.undo()  # nothing left
        assert not buf.modified

    def test_first_change_records_save_point_marker(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("A")
        buf.insert_string("B")  # second change: no second marker
        markers = [e for e in buf.undo_list if isinstance(e, UndoSavePoint)]
        assert len(markers) == 1
        assert markers[0].save_tick == 0

    def test_no_marker_when_undo_recording_disabled(self) -> None:
        buf = Buffer(text="hello")
        buf._undo_recording = False
        buf.insert_string("AB")
        assert buf.modified  # the flag still flips...
        assert buf.undo_list == []  # ...but nothing is recorded (Emacs too)


class TestRedoAndSavedState:
    def test_redo_away_from_save_point_sets_modified(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        buf.undo()
        assert not buf.modified
        buf.add_undo_boundary()  # break the chain, as a real command would
        assert buf.undo()  # redo: re-insert AB
        assert buf.text == "ABhello"
        assert buf.modified

    def test_redo_back_to_mid_session_save_clears_modified(self) -> None:
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        buf.add_undo_boundary()
        buf.mark_saved()  # C-x C-s: "ABhello" is now the saved content
        buf.insert_string("CD")
        buf.undo()  # back to the saved "ABhello"
        assert not buf.modified
        buf.add_undo_boundary()
        buf.undo()  # redo CD — away from the save point
        assert buf.modified
        buf.add_undo_boundary()
        buf.undo()  # undo CD again — back at the save point
        assert buf.text == "ABhello"
        assert not buf.modified


class TestSaveGenerationStaleness:
    def test_marker_from_before_a_save_goes_stale(self) -> None:
        """Undoing past a mid-session save must NOT clear modified.

        Emacs: the file on disk now holds the newer content, so arriving
        at the *older* content is a modified state; the old ``(t . TIME)``
        entry fails its modtime comparison and is ignored.
        """
        buf = Buffer(text="hello")
        buf.insert_string("AB")  # marker, generation 0
        buf.add_undo_boundary()
        buf.mark_saved()  # generation 1: disk now has "ABhello"
        buf.insert_string("CD")  # marker, generation 1
        buf.undo()  # back to "ABhello" = saved
        assert not buf.modified
        buf.undo()  # back to "hello" — older than the save
        assert buf.text == "hello"
        assert buf.modified  # generation-0 marker is stale

    def test_noop_save_keeps_existing_markers_valid(self) -> None:
        """Saving an unmodified buffer must not stale its markers.

        Emacs skips rewriting an unmodified buffer ("No changes need to
        be saved"), so its recorded modtimes stay valid.
        """
        buf = Buffer(text="hello")
        buf.insert_string("AB")
        buf.undo()
        assert not buf.modified
        buf.mark_saved()  # no-op: already unmodified
        buf.add_undo_boundary()
        buf.undo()  # redo AB
        assert buf.modified
        buf.add_undo_boundary()
        buf.undo()  # back to "hello" — still the saved content
        assert not buf.modified

    def test_mark_saved_bumps_generation_only_when_modified(self) -> None:
        buf = Buffer(text="hello")
        assert buf._save_tick == 0
        buf.mark_saved()
        assert buf._save_tick == 0
        buf.insert_string("A")
        buf.mark_saved()
        assert buf._save_tick == 1


# ═══════════════════════════════════════════════════════════════════════
# Editor-level flow (the parity scenario 09 keystroke script)
# ═══════════════════════════════════════════════════════════════════════


class TestScenario09Flow:
    def _setup(self):
        h = make_harness("hello world\n")
        h.type_string("AB")
        h.send_keys("C-e")
        h.type_string("CD")
        return h

    def test_undo_to_visited_content_clears_modified(self) -> None:
        h = self._setup()
        h.send_keys("C-/")  # undo CD
        assert h.editor.buffer.modified
        h.send_keys("C-/")  # undo AB — back to the visited file content
        assert h.editor.buffer.text == "hello world\n"
        assert not h.editor.buffer.modified

    def test_exhausted_undo_stays_unmodified(self) -> None:
        h = self._setup()
        h.send_keys("C-/", "C-/", "C-/")  # third: history exhausted
        assert not h.editor.buffer.modified
        assert "No further undo" in h.editor.message

    def test_redo_after_exhaustion_sets_modified(self) -> None:
        h = self._setup()
        h.send_keys("C-/", "C-/", "C-/")
        h.send_keys("C-f")  # break the undo chain
        h.send_keys("C-/")  # redo: re-insert AB
        assert "AB" in h.editor.buffer.text
        assert h.editor.buffer.modified
