"""Scenario 20 — python-mode TAB indentation (``python-indent-line``).

Emacs python-mode binds TAB to ``python-indent-line``: it indents to the
syntactic level and CYCLES through the candidate levels on repeated TAB.
Line 3 (``z``) sits under ``    if y:`` (indent 4, a block header), so its
calculated indent is 8 and the candidate levels are ``[8, 4, 0]``.

Four checkpoints (point at column 0 of line 3 to start):

  * ``TAB1`` — indent to 8 (the calculated level).
  * ``TAB2`` — repeated TAB cycles to 4.
  * ``TAB3`` — to 0.
  * ``TAB4`` — wraps back to 8.

The buffer is a ``.py`` file, so the modeline reads ``(Python ElDoc)`` —
Emacs enables eldoc-mode in python-mode and neon-edit shows the matching
lighter (the echo-area docs themselves are not implemented).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "20-python-indent"
DESCRIPTION = "python-mode TAB: indent to syntactic level, cycle on repeat."

CONTENT = "def foo():\n    if y:\nz\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_pyindent.py", content=CONTENT) as f:
        emacs, neon = make_targets(f)
        labels = ["TAB1-col8", "TAB2-col4", "TAB3-col0", "TAB4-wrap8"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []
                # Move to line 3 ("z"), column 0.
                driver.send("C-n")
                driver.settle(settle_ms=150)
                driver.send("C-n")
                driver.settle(settle_ms=200)
                for label in labels:
                    driver.send("TAB")
                    driver.settle(settle_ms=350)
                    taken.append(driver.snapshot(label))
                snapshots[target.name] = taken
        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)
    return result
