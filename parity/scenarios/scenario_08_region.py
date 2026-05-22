"""Scenario 08 — Region operations (mark, transient highlighting, exchange).

Walks through the small mark/region commands that every Emacs user
relies on, and that are easy to break in subtle ways:

  * ``after-C-SPC``        — set-mark; echo area should read ``Mark set``
  * ``after-M-f``          — region grew by one word; same mark, point moved
  * ``after-C-x-C-x``      — ``exchange-point-and-mark`` swaps the two
  * ``after-M->``          — large motion; the region now spans most of buf
  * ``after-C-x-C-x-twice``— second swap restores the original state

The cursor coordinates capture the "where is point relative to the
mark" question that determines what subsequent kill/copy commands
operate on. Echo-area parity around mark commands is what makes the
editor feel responsive — the ``Mark set`` / ``Mark saved...`` messages
are the only sign the user has that the mark moved.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "08-mark-and-region"
DESCRIPTION = "Mark / exchange-point-and-mark / region echo-area messages."

CONTENT = "alpha beta gamma\ndelta epsilon\nzeta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_region.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-C-SPC",
            "after-M-f",
            "after-C-x-C-x",
            "after-M->",
            "after-C-x-C-x-twice",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Point at L1 C0 after open. Set the mark.
                driver.send("C-SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-SPC"))

                # Grow the region by a word — point at end of "alpha".
                driver.send("M-f")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-f"))

                # Swap point and mark: cursor jumps back to L1 C0, mark
                # moves to end of "alpha".
                driver.send("C-x C-x")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-x-C-x"))

                # Jump to end of buffer with the mark left somewhere.
                driver.send("M->")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M->"))

                # Swap again — should restore prior cursor/mark roles.
                driver.send("C-x C-x")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-x-C-x-twice"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
