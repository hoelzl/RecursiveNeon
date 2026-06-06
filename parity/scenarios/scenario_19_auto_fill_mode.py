"""Scenario 19 — auto-fill-mode (``M-x auto-fill-mode``).

GNU Emacs's text-mode does NOT auto-fill by default; ``M-x auto-fill-mode``
turns the minor mode on (echoing ``Auto-Fill mode enabled in current
buffer`` and adding the ` Fill` modeline lighter), after which typing past
``fill-column`` (70) breaks the line at the preceding space. Toggling
again disables it.

Three checkpoints:

  * ``A-enable``   — ``M-x auto-fill-mode`` → ``(Text Fill)`` modeline and
    the enable message.
  * ``B-break``    — typing a long line breaks it at the fill column.
  * ``C-disable``  — ``M-x auto-fill-mode`` again → ``(Text)`` modeline and
    the disable message.

Uses a one-line seed file (with a trailing newline) so the buffer is not
empty — an empty file makes Emacs show a different EOL mnemonic in the
modeline mule field, which is an unrelated cosmetic quirk.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "19-auto-fill-mode"
DESCRIPTION = "M-x auto-fill-mode: enable echo + Fill lighter, break, disable echo."

CONTENT = "seed\n"

LONG = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_autofill.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)
        labels = ["A-enable", "B-break", "C-disable"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Type the long line on the empty second line.
                driver.send("C-n")
                driver.settle(settle_ms=200)

                # Enable auto-fill-mode.
                driver.send("M-x")
                driver.settle(settle_ms=300)
                driver.send("auto-fill-mode")
                driver.settle(settle_ms=150)
                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("A-enable"))

                # Type past fill-column; the line breaks at the last space.
                driver.send(LONG)
                driver.settle(settle_ms=200)
                driver.send("SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("B-break"))

                # Disable auto-fill-mode.
                driver.send("M-x")
                driver.settle(settle_ms=300)
                driver.send("auto-fill-mode")
                driver.settle(settle_ms=150)
                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("C-disable"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
