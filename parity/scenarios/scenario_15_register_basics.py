"""Scenario 15 — register basics (``C-x r SPC`` / ``C-x r j``).

Saves point in a register, moves away, and jumps back. Both register
commands read one more key — the register *name* — and show a prompt in
the echo area while they wait.

Five checkpoints:

  * ``after-Cxr-SPC``     — ``C-x r SPC`` shows ``Point to register: ``
    and waits for the register name (cursor stays at point).
  * ``after-save-a``      — naming the register (``a``) saves point; the
    prompt clears and point is unchanged.
  * ``after-move-to-top`` — ``M-<`` moves point to the buffer start.
  * ``after-Cxr-j``       — ``C-x r j`` shows ``Jump to register: `` and
    waits for the name.
  * ``after-jump-a``      — naming the register (``a``) restores point to
    the saved location.

The settle after each register prompt is kept under a second so Emacs's
``register-preview`` popup (which appears after ``register-preview-delay``)
does not fire — both sides just show the one-line prompt.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "15-register-basics"
DESCRIPTION = "Point registers: C-x r SPC saves point, C-x r j jumps back."

CONTENT = "line one\nline two\nline three\nline four\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_register.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-Cxr-SPC",
            "after-save-a",
            "after-move-to-top",
            "after-Cxr-j",
            "after-jump-a",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Move point to the end of line 3 ("line three", col 10).
                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-e")
                driver.settle(settle_ms=300)

                # C-x r SPC: prompt for a register name to save point in.
                driver.send("C-x r SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Cxr-SPC"))

                # Name the register → point saved, prompt clears.
                driver.send("a")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-save-a"))

                # Move to the top of the buffer.
                driver.send("M-<")
                driver.settle(settle_ms=300)
                taken.append(driver.snapshot("after-move-to-top"))

                # C-x r j: prompt for a register name to jump to.
                driver.send("C-x r j")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Cxr-j"))

                # Name the register → point restored to the saved location.
                driver.send("a")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-jump-a"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
