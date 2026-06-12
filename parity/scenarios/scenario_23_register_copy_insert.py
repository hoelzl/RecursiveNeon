"""Scenario 23 — Text registers: ``copy-to-register`` / ``insert-register``.

Scenario 15 covered the point registers (``C-x r SPC`` / ``C-x r j``);
this one adds the text-register pair GNU Emacs binds at ``C-x r s``
(copy the region into a register) and ``C-x r i`` (insert a register's
contents at point), plus the type-mismatch errors between the two
register kinds.

Checkpoints:

  * ``after-C-x-r-s``         — ``Copy to register: `` prompt (region
    "alpha" active from ``C-SPC M-f``).
  * ``after-copy-a``          — name key ``a``: silent success, the echo
    area is cleared and the region deactivated; buffer untouched.
  * ``after-C-x-r-i``         — ``Insert register: `` prompt (point moved
    to end of line 2 first).
  * ``after-insert-a``        — inserts ``alpha`` at point; Emacs ≥28
    leaves point *after* the inserted text with the mark before it
    (``Mark set``).
  * ``insert-empty-register`` — ``C-x r i z`` on a never-set register:
    ``Register does not contain text``.
  * ``jump-to-text-register`` — ``C-x r j a`` on a *text* register:
    ``Register doesn’t contain a buffer position or configuration``
    (curly apostrophe — Emacs's default text-quoting-style).
  * ``insert-point-register`` — a *point* register inserted with
    ``C-x r i`` produces the buffer position as a number (Emacs's
    ``register-val-insert`` on a marker).

Behaviour pinned by probing Emacs 29 before implementation. Note the
copy error path (``C-x r s`` with no region) is unit-tested rather than
checkpointed: in Emacs an earlier ``C-g`` merely *deactivates* the
mark, so the copy silently uses the inactive region. (neon-edit gained
the same inactive-mark model in scenario 30 — ``mark-even-if-inactive``
now holds here too — but the checkpoint set predates it and the unit
test still covers the true no-mark error.)
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "23-register-copy-insert"
DESCRIPTION = "C-x r s / C-x r i text registers and register type errors."

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = "alpha beta\ngamma delta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_reg2.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-C-x-r-s",
            "after-copy-a",
            "after-C-x-r-i",
            "after-insert-a",
            "insert-empty-register",
            "jump-to-text-register",
            "insert-point-register",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Region over "alpha" at buffer start.
                driver.send("C-SPC")
                driver.settle(settle_ms=300)
                driver.send("M-f")
                driver.settle(settle_ms=300)

                driver.send("C-x r s")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-x-r-s"))

                driver.send("a")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-copy-a"))

                # Insert it at end of line 2.
                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-e")
                driver.settle(settle_ms=300)
                driver.send("C-x r i")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-x-r-i"))

                driver.send("a")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-insert-a"))

                # Never-set register: text error.
                driver.send("C-x r i")
                driver.settle(settle_ms=300)
                driver.send("z")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("insert-empty-register"))

                # Jump to a text register: position error.
                driver.send("C-x r j")
                driver.settle(settle_ms=300)
                driver.send("a")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("jump-to-text-register"))

                # Point register inserted as text -> the position number.
                driver.send("C-x r SPC")
                driver.settle(settle_ms=300)
                driver.send("p")
                driver.settle(settle_ms=300)
                driver.send("C-x r i")
                driver.settle(settle_ms=300)
                driver.send("p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("insert-point-register"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
