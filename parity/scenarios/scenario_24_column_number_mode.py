"""Scenario 24 — ``column-number-mode`` and odd-height window splits.

Two modeline-geometry behaviours pinned against GNU Emacs 29:

* ``column-number-mode`` is a *global* minor mode: ``M-x
  column-number-mode`` echoes ``Column-Number mode enabled`` (no "in
  current buffer" suffix — contrast auto-fill-mode) and switches the
  modeline position readout from the padded ``L<line>`` field (`` L%l``
  right-padded to 6) to ``(<line>,<col>)`` (`` (%l,%c)`` right-padded to
  10, column zero-based). No lighter is added to the mode list.

* ``C-x 2`` with an odd usable height (24 rows - 1 echo row = 23) gives
  the *top* window the extra row: top = 11 text rows + modeline at row
  11, bottom = 10 text rows + modeline at row 22. neon-edit used to give
  the bottom window the extra row (cosmetic item 2 in
  docs/PARITY_HARNESS.md). Snapshotting the split while
  column-number-mode is on also proves the mode is global-per-frame
  (both modelines show the paren readout).

Checkpoints:

  * ``after-enable``   — toggle on: echo + ``(1,0)`` readout.
  * ``after-move``     — ``C-n C-f C-f C-f``: ``(2,3)``.
  * ``after-C-x-2``    — odd split: modelines at rows 11 and 22, both
    with the paren readout.
  * ``after-disable``  — ``C-x 1`` then toggle off: echo + ``L2``.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "24-column-number-mode"
DESCRIPTION = "Global column-number-mode toggle + odd-height C-x 2 split."

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = "alpha beta\ngamma delta\nthird\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_cnm.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-enable",
            "after-move",
            "after-C-x-2",
            "after-disable",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send("M-x")
                driver.settle(settle_ms=400)
                driver.send_text("column-number-mode")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-enable"))

                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-f C-f C-f")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-move"))

                driver.send("C-x 2")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-C-x-2"))

                driver.send("C-x 1")
                driver.settle(settle_ms=400)
                driver.send("M-x")
                driver.settle(settle_ms=300)
                driver.send_text("column-number-mode")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-disable"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
