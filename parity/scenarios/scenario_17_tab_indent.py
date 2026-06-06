"""Scenario 17 — TAB indentation (``indent-for-tab-command``).

Emacs binds TAB to ``indent-for-tab-command``; in text-mode that runs
``indent-relative`` — indent the current line to the next "indent point"
(word start) of the nearest previous non-blank line, falling back to
``tab-to-tab-stop`` past the last point (or on the first line).

Line 1 is ``  word1   word2`` (word starts — indent points — at col 2 and
col 10). Sitting on the empty line 2, three TABs walk: indent point 1,
indent point 2, then the tab-stop fallback. A final TAB on line 1 (no
previous line) exercises the pure ``tab-to-tab-stop`` case.

Four checkpoints:

  * ``after-TAB-indent1``   — TAB → col 2 (first word of line 1).
  * ``after-TAB-indent2``   — TAB → col 10 (second word).
  * ``after-TAB-tabstop``   — TAB → col 16 (next tab stop past col 10).
  * ``after-TAB-firstline`` — TAB at line 1 col 0 → col 8, pushing the
    text right (no previous line → tab-to-tab-stop).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "17-tab-indent"
DESCRIPTION = "TAB indent-relative + tab-to-tab-stop in text-mode."

CONTENT = "  word1   word2\n\nrest\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_tabindent.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-TAB-indent1",
            "after-TAB-indent2",
            "after-TAB-tabstop",
            "after-TAB-firstline",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send("C-n")  # → line 2 (empty)
                driver.settle(settle_ms=200)

                driver.send("TAB")
                driver.settle(settle_ms=300)
                taken.append(driver.snapshot("after-TAB-indent1"))

                driver.send("TAB")
                driver.settle(settle_ms=300)
                taken.append(driver.snapshot("after-TAB-indent2"))

                driver.send("TAB")
                driver.settle(settle_ms=300)
                taken.append(driver.snapshot("after-TAB-tabstop"))

                # Now the first-line (no-previous-line) tab-to-tab-stop case.
                driver.send("M-<")
                driver.settle(settle_ms=200)
                driver.send("TAB")
                driver.settle(settle_ms=300)
                taken.append(driver.snapshot("after-TAB-firstline"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
