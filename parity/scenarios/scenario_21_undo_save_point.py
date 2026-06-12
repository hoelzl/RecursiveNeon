"""Scenario 21 — Buffer-modified state through undo/redo across a save.

Exercises the save-point tracking that GNU Emacs implements via
``(t . TIME)`` undo entries (``record_first_change`` / ``primitive-undo``)
and neon-edit via ``UndoSavePoint`` markers with a save generation
(see ``backend/.../editor/undo.py`` and ``test_undo_savepoint.py``):

  * ``after-typing-AB``  — first edits: modeline shows modified ``**``
  * ``after-save``       — ``C-x C-s``: modeline back to ``--``
  * ``after-typing-CD``  — new edits on top of the save: ``**``
  * ``after-undo-CD``    — undo returns to the *saved* content: ``--``
    (this is the behaviour scenario 09 documented as missing; it now
    works through a mid-session save as well)
  * ``after-undo-AB``    — undo continues past the save to the original
    visited content: stays ``**`` — the disk file holds the newer saved
    content, so this *older* state is modified. Emacs gets this from the
    modtime comparison on its ``(t . TIME)`` entries; neon-edit from the
    marker's stale save generation.
  * ``after-redo-AB``    — ``C-f`` breaks the chain, ``C-/`` redoes back
    to the saved content: ``--`` again (the redo group carries its own
    save-point marker).

Documented divergences:

  * ``after-save`` echo area: Emacs reports the real OS path
    (``Wrote /tmp/parity-XXXX/parity_sp.txt``), neon-edit the
    virtual-filesystem path — same intentional sandboxing divergence as
    scenario 04's find-file prompt.
  * ``after-redo-AB`` cursor: the redone insertion leaves point at the
    match start in Emacs (col 0) but at the end in neon-edit (col 2) —
    the same ``primitive-undo`` point-sign deviation documented at
    scenario 09's ``after-redo`` checkpoint.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "21-undo-save-point"
DESCRIPTION = "Modified flag tracks the save point through undo/redo (C-x C-s)."

EXPECTED_DIVERGENCES = {
    "after-save": {"echo_area"},
    "after-redo-AB": {"cursor"},
}

CONTENT = "hello world\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_sp.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-typing-AB",
            "after-save",
            "after-typing-CD",
            "after-undo-CD",
            "after-undo-AB",
            "after-redo-AB",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Group 1: insert "AB" at the start of "hello world".
                driver.send("AB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-typing-AB"))

                # Save: "ABhello world" becomes the on-disk content.
                driver.send("C-x C-s")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-save"))

                # Group 2: insert "CD" at end of line.
                driver.send("C-e")
                driver.settle(settle_ms=400)
                driver.send("CD")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-typing-CD"))

                # Undo CD -> back at the saved content: unmodified.
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-undo-CD"))

                # Undo AB -> older than the save: modified again.
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-undo-AB"))

                # Break the chain, redo AB -> saved content: unmodified.
                driver.send("C-f")
                driver.settle(settle_ms=400)
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-redo-AB"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
