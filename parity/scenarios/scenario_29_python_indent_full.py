"""Scenario 29 — Full python-mode indentation contexts.

Scenario 20 verified the basic ``:``-header indent + TAB cycling; this
one drives the rest of the ported ``python-indent-calculate-indentation``
against real Emacs in a single buffer:

  * **bracket alignment** — a continuation line inside ``x = f(a,``
    aligns with the first char after the bracket (column 6);
  * **dedenter candidates** — an ``else:`` under ``try:/if c:`` offers
    only the matching ``if`` column (4): ``try`` is not in else's
    pairing set but still shadows lower candidates;
  * **backslash continuation** — the line after ``y = 1 + \\`` indents
    to the statement's indent + 4;
  * **def-paren newline** — the line after ``def g(`` indents + 8
    (python-indent-def-block-scale) and cycles down the offset chain.

The full context battery (closing brackets, nested brackets, strings,
comments, block-statement continuations, dedenter shadowing and
non-contiguous candidate cycling) was probed case-by-case against GNU
Emacs 29.3 before implementation and is pinned unit-side in
``test_python_indent_full.py`` — this scenario keeps the end-to-end
representative set small so the suite stays fast.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "29-python-indent-full"
DESCRIPTION = "python-mode TAB: brackets, dedenters, backslash, def-paren scale."

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = (
    "x = f(a,\n"
    "b)\n"
    "try:\n"
    "    if c:\n"
    "        pass\n"
    "else:\n"
    "y = 1 + \\\n"
    "z\n"
    "def g(\n"
    "w\n"
)


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_pyi.py", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "paren-align",
            "dedenter-else",
            "backslash-cont",
            "def-paren-8",
            "def-paren-cycle-4",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                def goto_line(n: int) -> None:
                    driver.send("M-<")
                    driver.settle(settle_ms=200)
                    for _ in range(n):
                        driver.send("C-n")
                        driver.settle(settle_ms=120)
                    driver.send("C-a")
                    driver.settle(settle_ms=200)

                goto_line(1)  # "b)" inside f(a,
                driver.send("TAB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("paren-align"))

                goto_line(5)  # "else:"
                driver.send("TAB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("dedenter-else"))

                goto_line(7)  # "z" after the backslash line
                driver.send("TAB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("backslash-cont"))

                goto_line(9)  # "w" after "def g("
                driver.send("TAB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("def-paren-8"))

                driver.send("TAB")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("def-paren-cycle-4"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
