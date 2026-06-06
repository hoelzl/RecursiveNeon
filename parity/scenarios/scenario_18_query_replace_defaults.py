"""Scenario 18 — query-replace defaults (``query-replace-defaults``).

After one ``M-% foo RET bar RET``, GNU Emacs remembers ``(foo . bar)`` as
the default. A later ``M-%`` then:

  * ``A-default-prompt``  — shows ``Query replace (default foo → bar): ``.
  * ``B-RET-reuse``       — submitting the from-input *empty* reuses the
    pair (skipping the with-prompt) and starts the session on the next
    match (``Query replacing foo with bar: (? for help)``).
  * ``C-Mp-combined``     — ``M-p`` recalls the combined ``foo → bar``
    entry (offered ahead of the individual history).
  * ``D-Mp-individual``   — a second ``M-p`` recalls the individual ``bar``.

Setup runs one ``M-% foo RET bar RET`` then ``q`` (exit without
replacing) so the buffer is untouched but the default is recorded.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "18-query-replace-defaults"
DESCRIPTION = "M-% default pair prompt, RET-reuse, and combined M-p history."

CONTENT = "foo foo foo\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_qrdefaults.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)
        labels = [
            "A-default-prompt",
            "B-RET-reuse",
            "C-Mp-combined",
            "D-Mp-individual",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Establish the default: M-% foo RET bar RET, then q.
                driver.send("M-%")
                driver.settle(settle_ms=400)
                driver.send("foo")
                driver.settle(settle_ms=150)
                driver.send("RET")
                driver.settle(settle_ms=300)
                driver.send("bar")
                driver.settle(settle_ms=150)
                driver.send("RET")
                driver.settle(settle_ms=400)
                driver.send("q")  # exit without replacing
                driver.settle(settle_ms=300)

                # A: a fresh M-% shows the default pair.
                driver.send("M-%")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("A-default-prompt"))

                # B: RET on empty reuses the default → session starts.
                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("B-RET-reuse"))
                driver.send("q")  # exit the reused session
                driver.settle(settle_ms=300)

                # C / D: M-% then M-p recalls combined, then individual.
                driver.send("M-%")
                driver.settle(settle_ms=400)
                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("C-Mp-combined"))
                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("D-Mp-individual"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
