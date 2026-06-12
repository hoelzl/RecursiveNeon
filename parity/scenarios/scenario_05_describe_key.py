"""Scenario 05 — ``C-h k C-f`` (describe-key for forward-char).

In Emacs, pressing ``C-h k`` prompts ``Describe key:`` in the echo area
and waits for a keystroke. Pressing ``C-f`` then pops up a ``*Help*``
buffer documenting ``forward-char`` (key binding, command name, doc
string, source location). The echo area itself stays at ``Describe key:``.

We snapshot two checkpoints:

  * after ``C-h k``: the prompt
  * after the follow-up ``C-f``: the resulting help display

Both editors should show identical prompts at checkpoint 1. The
``*Help*`` buffer content at checkpoint 2 will diverge — Emacs has its
own docs, neon-edit will produce something based on the registered
``defcommand`` entries — but the *shape* (a Help buffer popped up,
modeline reading ``*Help*``, echo area unchanged) is what we care about.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "05-describe-key-forward-char"
DESCRIPTION = "C-h k C-f should pop up a *Help* buffer documenting forward-char."

# Documented divergence (see module docstring): the *Help* text itself
# is content-dependent (Emacs's forward-char doc is longer than
# neon-edit's defcommand docstring), which also flips the *Help*
# modeline position indicator (Top vs All). The prompt checkpoint must
# match exactly.
EXPECTED_DIVERGENCES = {
    "after-follow-up-C-f": {"body", "modeline"},
}


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(
        basename="parity_dk.txt", content="placeholder\n"
    ) as f:
        emacs, neon = make_targets(f)

        labels = ["after-C-h-k", "after-follow-up-C-f"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []
                driver.send("C-h k")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-C-h-k"))
                driver.send("C-f")
                driver.settle(settle_ms=1500, max_wait=6.0)
                taken.append(driver.snapshot("after-follow-up-C-f"))
                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
