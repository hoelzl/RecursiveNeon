"""Scenario 14 — query-replace (``M-%``).

Drives the full interactive replace flow and checks the minibuffer
prompts, the per-match prompt, the y/n decisions, and the closing
summary against GNU Emacs.

Six checkpoints:

  * ``after-M-%``               — entry prompt (``Query replace: ``).
  * ``after-from-foo``          — second prompt once FROM is submitted
    (``Query replace foo with: ``).
  * ``after-to-X-first-match``  — TO submitted; the first match is on
    deck and the per-match prompt is shown.
  * ``after-y-replace-1``       — ``y`` replaces match 1, advances to
    match 2.
  * ``after-n-skip``            — ``n`` skips match 2, advances to match 3.
  * ``after-y-replace-2-done``  — ``y`` replaces match 3; no matches
    remain, so the session ends with the ``Replaced N`` summary.

The document has three ``foo`` occurrences (one per line); the run
replaces the 1st and 3rd and skips the 2nd, leaving ``X bar`` / ``foo
baz`` / ``X qux``.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "14-query-replace"
DESCRIPTION = "Interactive M-% replace: prompts, per-match y/n, closing summary."

CONTENT = "foo bar\nfoo baz\nfoo qux\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_qreplace.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-M-%",
            "after-from-foo",
            "after-to-X-first-match",
            "after-y-replace-1",
            "after-n-skip",
            "after-y-replace-2-done",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # M-% opens the "from" prompt.
                driver.send("M-%")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-%"))

                # Type the search string, submit → "with" prompt.
                driver.send("foo")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-from-foo"))

                # Type the replacement, submit → first match on deck.
                driver.send("X")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-to-X-first-match"))

                # y: replace match 1, advance to match 2.
                driver.send("y")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-y-replace-1"))

                # n: skip match 2, advance to match 3.
                driver.send("n")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-n-skip"))

                # y: replace match 3, exhaust matches → closing summary.
                driver.send("y")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-y-replace-2-done"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
