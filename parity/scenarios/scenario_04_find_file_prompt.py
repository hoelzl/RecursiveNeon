"""Scenario 04 — ``C-x C-f`` (find-file) minibuffer prompt and cancel.

Emacs's ``find-file`` opens the minibuffer with prompt ``Find file: <dir>/``
pre-filled with the current directory. neon-edit now does the same — the
shell's ``edit`` program hands the editor its current working directory
as ``editor.default_directory``.

We snapshot three checkpoints:

  * after ``C-x C-f`` — the bare prompt, with cwd pre-filled
  * after typing ``zzz`` — the prompt with extra text appended
  * after ``C-g`` — the cancel state (echo area should say ``Quit``)

Expected residual divergence: the *path string* itself. Emacs reports the
real OS path (``/tmp/parity-XXXX/``); neon-edit reports the virtual-
filesystem path (``/``). That's intentional — the in-game editor operates
on a sandboxed virtual filesystem, not the host's. What's compared here
is *shape*: prompt wording, trailing slash, and that something resembling
a path is pre-filled.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "04-find-file-prompt-and-cancel"
DESCRIPTION = "C-x C-f opens the find-file prompt; C-g cancels it."

# Documented divergence (see module docstring): Emacs pre-fills the real
# OS cwd, neon-edit the virtual-FS root, so the prompt text and the
# cursor column (end of the pre-filled path) differ while the prompt is
# open. The post-C-g checkpoint must match exactly.
EXPECTED_DIVERGENCES = {
    "after-C-x-C-f": {"cursor", "echo_area"},
    "after-typing-zzz": {"cursor", "echo_area"},
}


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(
        basename="parity_ff.txt", content="placeholder\n"
    ) as f:
        emacs, neon = make_targets(f)

        labels = ["after-C-x-C-f", "after-typing-zzz", "after-C-g"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []
                driver.send("C-x C-f")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-C-x-C-f"))
                driver.send("zzz")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-typing-zzz"))
                driver.send("C-g")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-g"))
                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
