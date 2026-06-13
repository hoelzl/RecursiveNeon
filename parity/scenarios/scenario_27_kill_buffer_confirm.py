"""Scenario 27 — ``kill-buffer`` confirm-if-modified (``C-x k``).

GNU Emacs's ``kill-buffer--possibly-save``: killing a *modified
file-visiting* buffer asks ``Buffer NAME modified; kill anyway?
(yes/no/save and then kill)`` — a long-form ``read-multiple-choice``
read through the minibuffer with completion, so RET on a unique prefix
completes (``y`` → ``yes``, probed before implementation). Modified
buffers without a file (``*scratch*``) are killed silently.

Checkpoints:

  * ``kill-prompt``     — ``C-x k`` on the modified file buffer:
    ``Kill buffer (default parity_kc.txt): `` (scenario 10's prompt).
  * ``confirm-prompt``  — empty RET picks the default; the confirm
    question appears.
  * ``after-no``        — ``no`` RET: buffer survives, prompt closes.
  * ``after-y-kill``    — re-enter, ``y`` RET (unique prefix → yes):
    buffer killed, the frame falls back to ``*scratch*``. **Documented
    divergence (modeline)**: Emacs's ``*scratch*`` runs Lisp Interaction
    mode with ElDoc; neon-edit's is Fundamental — there is no Lisp in
    the game, an intentional content gap, same class as scenario 05's
    *Help* doc text.
  * ``after-save-kill`` — reopen the file (``C-x C-f``), modify, ``C-x
    k`` RET, ``s`` RET (→ "save and then kill"): saves (``Wrote …`` —
    path text differs by the usual virtual-FS sandboxing) then kills,
    falling back to ``*scratch*`` again (same modeline divergence).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "27-kill-buffer-confirm"
DESCRIPTION = "C-x k on a modified file buffer: yes/no/save-and-then-kill confirm."

EXPECTED_DIVERGENCES = {
    "after-y-kill": {"modeline"},
    "after-save-kill": {"modeline", "echo_area"},
}

CONTENT = "alpha\nbeta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_kc.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "kill-prompt",
            "confirm-prompt",
            "after-no",
            "after-y-kill",
            "after-save-kill",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send_text("zz")
                driver.settle(settle_ms=400)

                driver.send("C-x k")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("kill-prompt"))

                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("confirm-prompt"))

                driver.send_text("no")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-no"))

                driver.send("C-x k")
                driver.settle(settle_ms=400)
                driver.send("RET")
                driver.settle(settle_ms=400)
                driver.send_text("y")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-y-kill"))

                # Reopen, modify, save-and-then-kill.
                driver.send("C-x C-f")
                driver.settle(settle_ms=500)
                driver.send_text("parity_kc.txt")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=600)
                driver.send_text("yy")
                driver.settle(settle_ms=400)
                driver.send("C-x k")
                driver.settle(settle_ms=400)
                driver.send("RET")
                driver.settle(settle_ms=400)
                driver.send_text("s")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=700)
                taken.append(driver.snapshot("after-save-kill"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
