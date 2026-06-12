"""Scenario 09 — Undo / redo lifecycle (``C-/`` grouping, walk-back, redo).

Exercises the Emacs linear-undo model end to end and the small echo-area
feedback that accompanies each step. The keystroke script builds two
distinct undo groups, walks back through them one ``C-/`` at a time,
hits the bottom of the history, then breaks the undo run and redoes.

Checkpoints (one launch per target, path-dependent):

  * ``after-two-edits``       — type "AB", ``C-e``, type "CD"; two groups
  * ``after-undo-CD``         — first ``C-/`` reverts the *second* group
  * ``after-undo-AB``         — second ``C-/`` reverts the *first* group
  * ``after-undo-exhausted``  — third ``C-/`` with nothing left to undo
  * ``after-redo``            — ``C-f`` breaks the run, ``C-/`` redoes "AB"

Why this shape:

  * "AB" and "CD" are two-character self-insert runs, well under Emacs's
    ``amalgamating-undo-limit`` of 20, so both editors collapse each run
    into a single undo group. The intervening ``C-e`` is a non-editing
    command, which inserts an undo boundary in both editors, so the two
    groups stay separate and ``C-/`` peels them off one at a time.
  * Opening a file records no undo history, so the third ``C-/`` runs the
    history dry — both editors should report exhaustion.
  * ``C-f`` is a movement (non-undo) command: it breaks the consecutive-
    undo chain so the next ``C-/`` walks the reverse entries appended by
    the earlier undos — i.e. it redoes, re-inserting "AB".

Headline divergence (now fixed): GNU Emacs prints ``Undo`` in the echo
area on every successful undo and ``Redo`` when redoing (plain words, no
exclamation mark — the ``Undo!`` form is Emacs-20-era and was dropped by
modern Emacs). neon-edit used to be silent on a successful undo and only
spoke up ("No further undo information") on exhaustion. Per CLAUDE.md
rule 5 (Emacs is ground truth) neon-edit now echoes the same feedback:
``Buffer.undo()`` tracks whether each undo was actually a redo (via a
``redo`` flag on the boundary it inserts before its reverse entries) and
the ``undo`` command echoes ``Undo`` / ``Redo`` accordingly. After the
fix, the echo area matches Emacs at every checkpoint.

Two residual divergences are *documented deviations*, not regressions —
see ``docs/PARITY_HARNESS.md`` "Known intentional divergences":

  * ``after-undo-AB`` / ``after-undo-exhausted`` modeline: Emacs clears
    the modified mnemonic (``**`` → ``--``) once undo restores the buffer
    to its saved-on-disk content; neon-edit keeps it modified. That is
    save-state-through-undo tracking — the domain of the proposed
    ``scenario_12`` (modeline state flags), where it will be addressed
    alongside the other modified/read-only mnemonics rather than here.

  * ``after-redo`` cursor (Emacs col 0, neon col 2): Emacs's
    ``primitive-undo`` encodes, per operation, where point should land
    when a deletion record is reinserted (the sign of the recorded
    position), so a redone insertion leaves point at the *start* of the
    reinserted text. neon-edit's coarser undo-record model leaves point
    at the *end*. Matching exactly would require threading point intent
    through the reverse-entry construction and would churn scenario 06 +
    the undo test suite; the one-cell difference is not worth that.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "09-undo-redo"
DESCRIPTION = "Undo grouping, history walk-back, exhaustion, and redo."

# Documented deviation (see module docstring): the redone-insertion
# cursor landing (Emacs primitive-undo point-sign semantics). The
# modified-mnemonic-after-undo-to-saved divergence this scenario
# originally documented was fixed by UndoSavePoint tracking — see
# scenario 21 and test_undo_savepoint.py.
EXPECTED_DIVERGENCES = {
    "after-redo": {"cursor"},
}

CONTENT = "hello world\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_undo.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-two-edits",
            "after-undo-CD",
            "after-undo-AB",
            "after-undo-exhausted",
            "after-redo",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Point opens at L1 C0 of "hello world".
                # Group 1: insert "AB" at the start.
                driver.send("AB")
                driver.settle(settle_ms=500)
                # Break the self-insert run with a motion command, then
                # Group 2: insert "CD" at end of line.
                driver.send("C-e")
                driver.settle(settle_ms=400)
                driver.send("CD")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-two-edits"))

                # First undo: reverts the most recent group ("CD").
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-undo-CD"))

                # Second undo (chain continues): reverts "AB".
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-undo-AB"))

                # Third undo: history is dry -> exhaustion message.
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-undo-exhausted"))

                # Break the undo run with a motion, then redo: the next
                # C-/ re-applies the previously-undone "AB".
                driver.send("C-f")
                driver.settle(settle_ms=400)
                driver.send("C-/")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-redo"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
