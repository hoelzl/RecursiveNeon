"""Scenario 01 — Startup state of a freshly-opened 3-line text file.

Captures one snapshot per target right after the editor has settled on a
small text file. The snapshot exposes:

  * buffer body (lines visible above the modeline)
  * modeline content
  * echo-area content
  * cursor (x, y) position

This is intentionally the simplest scenario: just opening a file. It is
already enough to surface several well-known divergences (empty-line
markers, modeline format, automatic major-mode detection, echo-area state).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from parity.harness import ScenarioResult, StepResult
from parity.targets import make_emacs_target, make_neon_target


NAME = "01-startup-3-line-file"
DESCRIPTION = "Open a 3-line text file; snapshot the editor's initial state."

FILE_TEXT = "line one\nline two\nline three\n"
FILE_BASENAME = "parity_hello.txt"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)

    with tempfile.TemporaryDirectory(prefix="parity-") as tmp:
        tmp_path = Path(tmp)
        emacs_file = tmp_path / FILE_BASENAME
        emacs_file.write_text(FILE_TEXT)

        emacs = make_emacs_target(str(emacs_file))
        neon = make_neon_target(
            setup_lines=[
                f"echo {_q('line one')} > {FILE_BASENAME}",
                f"echo {_q('line two')} >> {FILE_BASENAME}",
                f"echo {_q('line three')} >> {FILE_BASENAME}",
            ],
            edit_command=f"edit {FILE_BASENAME}",
            cwd=str(tmp_path),
        )

        step = StepResult(label="after-open")
        for target in (emacs, neon):
            with target.launch() as driver:
                step.snapshots[target.name] = driver.snapshot("after-open")
        result.steps.append(step)

    return result


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"
