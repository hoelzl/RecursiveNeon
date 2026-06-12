"""Scenario 25 — ``replace-string`` shares query-replace's defaults/history.

GNU Emacs reads the arguments of both ``query-replace`` and
``replace-string`` through ``query-replace-read-args``, so the two
commands share one ``query-replace-defaults`` pair and one
``query-replace-history``. neon-edit mirrors this with
``_replace_read_args`` (scenario 18 built the mechanism for M-%; this
scenario verifies the sharing and the replace-string entry points).

Checkpoints:

  * ``rs-from-prompt``   — ``M-x replace-string``: plain prompt (no
    defaults recorded yet).
  * ``rs-with-prompt``   — ``Replace string foo with: ``.
  * ``rs-done``          — replaces all three matches; the summary counts
    even on later zero-match runs (``Replaced 3 occurrences``).
  * ``qr-sees-default``  — ``M-%`` next shows
    ``Query replace (default foo → bar): `` — the pair recorded by
    replace-string.
  * ``rs-default-prompt``— and replace-string's own prompt shows it too.
  * ``rs-M-p-combined``  — ``M-p`` recalls the combined ``foo → bar``
    entry (point at the start of the recall).
  * ``rs-empty-reuse``   — quit, re-enter, empty RET reuses the pair; no
    ``foo`` remains so the echo is ``Replaced 0 occurrences`` (Emacs
    reports a zero count, not a "no matches" message).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "25-replace-string-defaults"
DESCRIPTION = "replace-string shares query-replace-defaults and its history."

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = "foo one\nfoo two\nfoo three\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_rsd.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "rs-from-prompt",
            "rs-with-prompt",
            "rs-done",
            "qr-sees-default",
            "rs-default-prompt",
            "rs-M-p-combined",
            "rs-empty-reuse",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                def run_mx(text: str) -> None:
                    driver.send("M-x")
                    driver.settle(settle_ms=300)
                    driver.send_text(text)
                    driver.settle(settle_ms=300)
                    driver.send("RET")
                    driver.settle(settle_ms=500)

                run_mx("replace-string")
                taken.append(driver.snapshot("rs-from-prompt"))

                driver.send_text("foo")
                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("rs-with-prompt"))

                driver.send_text("bar")
                driver.send("RET")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("rs-done"))

                driver.send("M-<")
                driver.settle(settle_ms=300)
                driver.send("M-%")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("qr-sees-default"))
                driver.send("C-g")
                driver.settle(settle_ms=300)

                run_mx("replace-string")
                taken.append(driver.snapshot("rs-default-prompt"))

                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("rs-M-p-combined"))
                driver.send("C-g")
                driver.settle(settle_ms=300)

                driver.send("M-<")
                driver.settle(settle_ms=300)
                run_mx("replace-string")
                driver.send("RET")  # empty from-input: reuse foo → bar
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("rs-empty-reuse"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
