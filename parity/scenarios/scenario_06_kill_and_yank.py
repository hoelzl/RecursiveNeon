"""Scenario 06 — Kill and yank (``C-k``, ``C-w``, ``M-w``, ``C-y``, ``M-y``).

Covers the basic kill-ring lifecycle and the small messages that Emacs
puts in the echo area along the way. Five checkpoints:

  * ``after-C-k``    — kill from point to end of line
  * ``after-C-y``    — yank back at end of buffer
  * ``after-M-w``    — kill-ring-save (region copy, no buffer mutation)
  * ``after-C-w``    — kill region (buffer mutation, point at region start)
  * ``after-M-y``    — yank-pop after a C-y (cycles through earlier kills)

Each step exercises one of:
  * cursor position after the operation
  * buffer content after the operation
  * echo-area feedback ("Mark set", "Kill ring is empty", etc.)
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "06-kill-and-yank"
DESCRIPTION = "Kill ring lifecycle: C-k, M-w, C-w, C-y, M-y."

CONTENT = "alpha beta gamma\ndelta epsilon\nzeta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_kill.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-C-k",
            "after-C-y",
            "after-M-w-region-saved",
            "after-C-w-region-killed",
            "after-M-y-yank-pop",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Point is at L1 C0 after open. C-k kills "alpha beta gamma"
                # but leaves the trailing newline (matches Emacs's default).
                driver.send("C-k")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-k"))

                # Move to end of buffer and yank — the last line's text
                # should come back. ``M-> `` is end-of-buffer.
                driver.send("M->")
                driver.settle(settle_ms=300)
                driver.send("C-y")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-y"))

                # Region copy: go to start, set mark, advance one word,
                # M-w to copy without mutating.
                driver.send("M-<")
                driver.settle(settle_ms=200)
                driver.send("C-SPC")
                driver.settle(settle_ms=200)
                driver.send("M-f")  # forward-word: select "alpha"
                driver.settle(settle_ms=200)
                driver.send("M-w")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-w-region-saved"))

                # Region kill: re-select first word and C-w to remove it.
                driver.send("M-<")
                driver.settle(settle_ms=200)
                driver.send("C-SPC")
                driver.settle(settle_ms=200)
                driver.send("M-f")
                driver.settle(settle_ms=200)
                driver.send("C-w")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-w-region-killed"))

                # M-y after a C-y cycles to the previous kill on the ring.
                # We need a fresh C-y first so that the immediate-previous
                # command is "yank" (yank-pop is only valid right after
                # yank in Emacs).
                driver.send("M->")
                driver.settle(settle_ms=200)
                driver.send("C-y")
                driver.settle(settle_ms=300)
                driver.send("M-y")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-y-yank-pop"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
