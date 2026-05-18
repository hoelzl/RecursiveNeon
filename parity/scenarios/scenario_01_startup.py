"""Scenario 01 — Startup state of a freshly-opened 3-line text file."""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "01-startup-3-line-file"
DESCRIPTION = "Open a 3-line text file; snapshot the editor's initial state."


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(
        basename="parity_hello.txt", content="line one\nline two\nline three\n"
    ) as f:
        emacs, neon = make_targets(f)
        step = StepResult(label="after-open")
        for target in (emacs, neon):
            with target.launch() as driver:
                step.snapshots[target.name] = driver.snapshot("after-open")
        result.steps.append(step)
    return result
