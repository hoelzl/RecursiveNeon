"""Scenario 02 — Echo-area message when moving past end of buffer.

GNU Emacs prints ``End of buffer`` in the echo area when the user presses
``C-n`` (or any other downward motion) while point is on the last line and
cannot move further. We expect neon-edit to do the same.

The test file deliberately has *no* trailing newline so the last visible
line has no successor; the C-n that tries to leave it should fail and
trigger the message in both editors.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "02-end-of-buffer-message"
DESCRIPTION = "Press C-n past the last line; both editors should say 'End of buffer'."


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    # No trailing newline — last line is "line three" and there is no
    # empty line beyond it.
    content = "line one\nline two\nline three"

    with staged_file(basename="parity_eob.txt", content=content) as f:
        emacs, neon = make_targets(f)

        # First snapshot the state after walking C-n three times: we should
        # be on the last line in both editors. The third C-n is the one
        # that triggers "End of buffer".
        step_a = StepResult(label="after-3x-C-n")
        for target in (emacs, neon):
            with target.launch() as driver:
                # Move cursor to last line and attempt one more step down.
                driver.send("C-n C-n C-n")
                driver.settle(settle_ms=600)
                step_a.snapshots[target.name] = driver.snapshot("after-3x-C-n")
        result.steps.append(step_a)

    return result
