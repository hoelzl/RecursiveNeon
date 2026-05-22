"""Scenario 07 — ``C-s`` (isearch-forward) incremental search.

GNU Emacs's incremental search is famously its own little mode: every
keystroke either narrows the match (visible highlight) or fails over
to ``Failing I-search:`` / ``Wrapped I-search:`` prompts. Five
checkpoints cover the lifecycle:

  * ``after-C-s``       — bare ``I-search:`` prompt
  * ``after-typing-e``  — first incremental match (cursor moves to it)
  * ``after-typing-X``  — failing search (no match for ``eX``)
  * ``after-Backspace`` — return to the last successful state
  * ``after-RET``       — exit isearch at the current match
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "07-isearch-forward"
DESCRIPTION = (
    "C-s incremental search: prompt, match, failing, backspace, RET."
)

CONTENT = "first line\nsecond line\nthird line\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_isearch.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-C-s",
            "after-typing-e",
            "after-typing-X",
            "after-Backspace",
            "after-RET",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send("C-s")
                driver.settle(settle_ms=1200, max_wait=4.0)
                taken.append(driver.snapshot("after-C-s"))

                driver.send("e")
                driver.settle(settle_ms=1000, max_wait=4.0)
                taken.append(driver.snapshot("after-typing-e"))

                driver.send("X")  # uppercase to defeat smart-case fold
                driver.settle(settle_ms=1000, max_wait=4.0)
                taken.append(driver.snapshot("after-typing-X"))

                driver.send("DEL")  # erase the X — back to last good state
                driver.settle(settle_ms=1000, max_wait=4.0)
                taken.append(driver.snapshot("after-Backspace"))

                driver.send("RET")  # exit at current match
                driver.settle(settle_ms=1000, max_wait=4.0)
                taken.append(driver.snapshot("after-RET"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
