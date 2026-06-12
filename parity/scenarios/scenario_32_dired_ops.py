"""Scenario 32 — dired operations: flag/delete, create, rename, copy.

Drives the mutation battery over a two-file staged tree:

* ``d`` flags the entry (modeline flips to ``%*`` — flagging modifies
  the buffer) and moves point down.
* ``x`` prompts ``Delete alpha.txt (yes or no) `` — that echo line and
  cursor are *compared*, the prompt carries no host paths. ``yes RET``
  deletes, echoes ``Deleting...done`` and leaves point on the same file
  one line up.
* ``+`` (create directory), ``R`` (rename) and ``C`` (copy) — the
  prompts embed the staged absolute path, so those checkpoints baseline
  the echo area; the result checkpoints compare the ``Move: 1 file
  done`` / ``Copy: 1 file done`` messages and the point line.

Body and cursor column are baselined throughout (host paths + real
vs. synthesized metadata — see scenario 31); the exact listing rewrite
behaviour (in-place rename, insert-at-point with ``C`` mark, alignment)
is pinned by ``tests/unit/editor/test_dired.py``.
"""

from __future__ import annotations

from parity.fixtures import make_tree_targets, staged_tree
from parity.harness import ScenarioResult, StepResult

NAME = "32-dired-ops"
DESCRIPTION = "dired d/x/+/R/C operations: prompts, messages, point."

FILES = {
    "alpha.txt": "alpha line\n",
    "beta.py": "print('beta')\n",
}

EXPECTED_DIVERGENCES = {
    "after-flag": {"body", "cursor"},
    "after-x-prompt": {"body"},
    "after-delete": {"body", "cursor"},
    "after-create-prompt": {"body", "cursor", "echo_area"},
    "after-create": {"body", "cursor"},
    "after-rename-prompt": {"body", "cursor", "echo_area"},
    "after-rename": {"body", "cursor"},
    "after-copy": {"body", "cursor"},
}


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_tree(dirname="tree", files=FILES) as f:
        emacs, neon = make_tree_targets(f, FILES)

        labels = [
            "after-flag",
            "after-x-prompt",
            "after-delete",
            "after-create-prompt",
            "after-create",
            "after-rename-prompt",
            "after-rename",
            "after-copy",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Point opens on alpha.txt (L4); flag it.
                driver.send("d")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-flag"))

                driver.send("x")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-x-prompt"))

                driver.send_text("yes")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-delete"))

                driver.send("+")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-create-prompt"))

                driver.send_text("newdir")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-create"))

                # Point sits on the new newdir line; move down to
                # beta.py and rename it.
                driver.send("n")
                driver.settle(settle_ms=200)
                driver.send("R")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-rename-prompt"))

                driver.send_text("mid.txt")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-rename"))

                driver.send("C")
                driver.settle(settle_ms=600)
                driver.send_text("copy2.txt")
                driver.settle(settle_ms=200)
                driver.send("RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-copy"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
