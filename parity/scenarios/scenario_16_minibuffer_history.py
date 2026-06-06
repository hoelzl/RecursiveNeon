"""Scenario 16 — minibuffer history (``M-p`` / ``M-n``).

Builds a two-entry M-x command history, then walks it with ``M-p``
(older) and ``M-n`` (newer), including the wrap back to the originally
typed (empty) input.

Setup runs two harmless commands so the ``M-x`` history (Emacs's
``extended-command-history``) holds ``["backward-char", "forward-char"]``
(newest first); ``forward-char`` then ``backward-char`` leave point where
it started, so the buffer behind the minibuffer is identical on both
sides.

Five checkpoints:

  * ``after-M-x-prompt``    — a fresh ``M-x`` prompt (empty input).
  * ``after-Mp-backward``   — ``M-p`` recalls the most recent command.
  * ``after-Mp-forward``    — a second ``M-p`` recalls the older command.
  * ``after-Mn-backward``   — ``M-n`` steps back toward the newer command.
  * ``after-Mn-restore``    — ``M-n`` to position 0 restores the typed
    (empty) input, leaving the bare ``M-x`` prompt.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "16-minibuffer-history"
DESCRIPTION = "M-x command history recall with M-p / M-n."

CONTENT = "hello world\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_history.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-M-x-prompt",
            "after-Mp-backward",
            "after-Mp-forward",
            "after-Mn-backward",
            "after-Mn-restore",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Build the command history with two harmless commands.
                driver.send("M-x")
                driver.settle(settle_ms=300)
                driver.send("forward-char")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=300)

                driver.send("M-x")
                driver.settle(settle_ms=300)
                driver.send("backward-char")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=300)

                # Fresh M-x prompt — empty input.
                driver.send("M-x")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-x-prompt"))

                # M-p recalls the most recent command, then the older one.
                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Mp-backward"))

                driver.send("M-p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Mp-forward"))

                # M-n steps back toward the newer command, then to the
                # originally typed (empty) input.
                driver.send("M-n")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Mn-backward"))

                driver.send("M-n")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-Mn-restore"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
