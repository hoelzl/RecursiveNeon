"""Scenario 03 — ``M-x`` minibuffer prompt and after-typing state.

Captures three checkpoints:

  * after pressing ``M-x``: minibuffer prompt visible (``M-x``-style)
  * after typing ``for``: prompt followed by the typed text
  * after pressing ``TAB``: completion behaviour (``*Completions*`` popup
    in Emacs; whatever neon-edit does)

This scenario is intentionally less likely to match pixel-perfectly than
01/02 — the goal is to surface the divergence in completion display so
we can decide what's worth porting.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "03-mx-minibuffer-prompt-and-completion"
DESCRIPTION = "Press M-x, type 'for', then TAB; observe minibuffer + completions."


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(
        basename="parity_mx.txt", content="hello world\n"
    ) as f:
        emacs, neon = make_targets(f)

        # We launch both targets once and snapshot at four checkpoints in
        # the same session — completion state is path-dependent.
        #
        # Note on the two TAB checkpoints: Emacs and neon-edit have very
        # different command sets (Emacs ships hundreds of commands; neon-
        # edit's ``forward-*`` family is just three commands). After one
        # TAB neon-edit's input extends to ``forward-`` (longest common
        # prefix of its own matches) while Emacs's stays at ``for`` (no
        # further common prefix). The popup therefore appears after the
        # *second* TAB in neon-edit but the *first* TAB in Emacs. The
        # ``after-TAB-TAB`` step lets both editors converge on the
        # "popup is visible" state for a meaningful comparison.
        labels = [
            "after-M-x",
            "after-typing-for",
            "after-TAB",
            "after-TAB-TAB",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []
                driver.send("M-x")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-M-x"))
                driver.send("for")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-typing-for"))
                driver.send("TAB")
                driver.settle(settle_ms=900)
                taken.append(driver.snapshot("after-TAB"))
                driver.send("TAB")
                driver.settle(settle_ms=900)
                taken.append(driver.snapshot("after-TAB-TAB"))
                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
