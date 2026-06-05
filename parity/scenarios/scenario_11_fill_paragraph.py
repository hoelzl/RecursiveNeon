"""Scenario 11 — Fill paragraph (``M-q``).

Exercises ``fill-paragraph`` at the default ``fill-column`` (70 in both
editors): a long single-line paragraph is re-wrapped at word boundaries,
then ``M-q`` is pressed again on the now-filled paragraph.

Checkpoints (one launch per target, path-dependent):

  * ``after-M-q``        — re-wrap the long line to fill-column
  * ``after-M-q-again``  — M-q on an already-filled paragraph

Divergences this surfaced (now fixed):

  * **Echo area.** GNU Emacs's ``M-q`` is *silent* — on both a successful
    fill and a no-op re-fill; neon-edit echoed "Filled paragraph" /
    "Paragraph unchanged".
  * **Point.** Emacs leaves point at the *start* of the filled paragraph;
    neon-edit trailed point to the end of the re-inserted text.

Both are neon-edit bugs against the Emacs ground truth (CLAUDE.md rule 5),
fixed alongside this module: ``M-q`` is now silent on success and leaves
point at the paragraph start. After the fix both checkpoints are
pixel-perfect.

Note on sentence spacing: with single-spaced input the filled text is
*identical* in both editors. Emacs's ``sentence-end-double-space`` (default
``t``) only *preserves* an existing two-space sentence break — it does not
*create* one from single-spaced prose — verified empirically here, so no
double-space divergence arises. (neon-edit's word re-join would collapse
an existing double space; that edge case is left for a future scenario if
it proves worth testing.)

Scope note: this scenario covers ``M-q`` only. TAB / ``indent-for-tab-
command`` (the "indentation" half of the originally-proposed scenario 11)
is a large, mode-specific feature neon-edit does not yet bind in text
buffers, and ``auto-fill-mode`` insertion has its own mode-enable message
and modeline indicator — both get their own scenarios.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "11-fill-paragraph"
DESCRIPTION = "M-q fill-paragraph: re-wrap at fill-column, sentence spacing, silence."

CONTENT = (
    "The cat sat on the mat. The dog ran in the fog. "
    "The bird flew over the tall wall. The fish swam in the small bowl.\n"
)


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_fill.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = ["after-M-q", "after-M-q-again"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Point opens at L1 C0. Re-wrap the long line at fill-column.
                driver.send("M-q")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-M-q"))

                # M-q again on the now-filled paragraph (a no-op re-fill).
                driver.send("M-q")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-M-q-again"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
