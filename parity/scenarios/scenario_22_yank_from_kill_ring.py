"""Scenario 22 — ``yank-from-kill-ring`` (``M-y`` when not after a yank).

GNU Emacs ≥28 binds ``M-y`` (when the previous command was *not* a yank)
to ``yank-from-kill-ring``: a ``Yank from kill-ring: `` minibuffer whose
``M-p``/``M-n`` history and TAB completion candidates are the kill-ring
entries (most recent first). ``RET`` inserts the minibuffer content
literally at point and pushes a mark (``Mark set``); the accept is not
itself a yank, so an immediately following ``M-y`` re-opens the picker
rather than rotating like ``yank-pop``. Scenario 13 covers the rotate
path and the picker *opening*; this one drives the picker itself.

Checkpoints:

  * ``after-M-y-prompt``     — picker open, empty input, cursor after the
    prompt.
  * ``after-M-p``            — first recall: the newest ring entry
    (``three``) with point at the *start* of the recalled text (Emacs's
    completing-read history recall semantics, scenario 16).
  * ``after-M-p-M-p``        — second recall: the older entry ``two``.
  * ``after-RET``            — accepts ``two``: inserted at point, mark
    pushed (``Mark set``), point at the end of the insert.
  * ``after-immediate-M-y``  — the next ``M-y`` re-prompts (no rotation).
  * ``after-C-g``            — quit out: ``Quit`` echo, buffer untouched.

Behaviour pinned by probing Emacs 29 before implementation: typed text
not in the ring is inserted literally (``completing-read`` runs with
``require-match`` nil), empty ``RET`` inserts nothing but still pushes
the mark, and an empty ring short-circuits with ``Kill ring is empty``
before any prompt opens — those edges are covered by the unit tests in
``backend/tests/unit/editor/test_killring.py`` (TestYankFromKillRing).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "22-yank-from-kill-ring"
DESCRIPTION = "M-y not after a yank opens the Yank from kill-ring picker."

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = "one\ntwo\nthree\nrest\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_yfkr.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-M-y-prompt",
            "after-M-p",
            "after-M-p-M-p",
            "after-RET",
            "after-immediate-M-y",
            "after-C-g",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Ring ["three", "two", "one"] (C-n between kills breaks
                # the coalescing run), then end-of-buffer (M-> pushes a
                # mark and echoes "Mark set" in both editors).
                for keys in ("C-k", "C-n", "C-k", "C-n", "C-k", "M->"):
                    driver.send(keys)
                    driver.settle(settle_ms=300)

                driver.send("M-y")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-M-y-prompt"))

                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-p"))

                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-p-M-p"))

                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-RET"))

                driver.send("M-y")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-immediate-M-y"))

                driver.send("C-g")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-g"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
