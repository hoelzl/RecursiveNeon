"""Scenario 26 — Empty-file EOL mnemonic (``-UUU:`` for the buffer's life).

The 4th mule char of the modeline prefix is the end-of-line type: ``-``
once decided, ``U`` while undecided. GNU Emacs samples the EOL only when
the file is *visited* — an empty file (or one with no newline at all)
stays undecided — and it then *remains* undecided for the buffer's
lifetime: neither typing newlines nor saving the newline-containing
content decides it. (The first implementation guessed that the save
would decide it; this scenario's ``after-save`` checkpoint proved
otherwise — the assert-mode harness earning its keep.) neon-edit mirrors
this with ``Buffer.eol_decided`` (sampled once at construction), fixing
cosmetic item 4 from docs/PARITY_HARNESS.md.

An empty buffer is also where ``C-f`` / ``C-b`` hit both buffer
boundaries at once, so this scenario doubles as coverage for their
boundary errors: Emacs echoes ``End of buffer`` / ``Beginning of
buffer`` (neon-edit's forward-char/backward-char used to be silent —
surfaced by this scenario via the old ``C-f C-b`` launch kick, fixed in
``_char_move``).

Checkpoints:

  * ``on-open``     — empty visited file: ``-UUU:---``, blank echo.
  * ``after-C-f``   — can't move forward: ``End of buffer``.
  * ``after-C-b``   — can't move back: ``Beginning of buffer``.
  * ``after-typing``— type ``ab``: modified, ``-UUU:**-``.
  * ``after-RET``   — newline in the buffer: mnemonic unchanged.
  * ``after-save``  — ``C-x C-s``: still ``-UUU:---`` (only the modified
    flag clears).

The ``after-save`` echo area differs by design (real OS path vs
virtual-filesystem path — the scenario 04/21 sandboxing divergence).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "26-empty-file-eol"
DESCRIPTION = "Empty file: EOL mnemonic undecided (-UUU:) until a save decides it."

EXPECTED_DIVERGENCES = {
    "after-save": {"echo_area"},
}

CONTENT = ""


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_eol.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "on-open",
            "after-C-f",
            "after-C-b",
            "after-typing",
            "after-RET",
            "after-save",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                taken.append(driver.snapshot("on-open"))

                driver.send("C-f")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-f"))

                driver.send("C-b")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-b"))

                driver.send_text("ab")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-typing"))

                driver.send("RET")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-RET"))

                driver.send("C-x C-s")
                driver.settle(settle_ms=700)
                taken.append(driver.snapshot("after-save"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
