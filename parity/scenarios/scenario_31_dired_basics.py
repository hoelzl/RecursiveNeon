"""Scenario 31 — dired basics: layout, point motion, visiting, ^.

Opens a staged directory tree in both editors (Emacs from the command
line, neon-edit via ``edit <dir>``) and walks the navigation battery:
``n``/``p`` motion onto the filename column, ``RET`` on a file (visits
it — that checkpoint is *fully* compared: same content, same point, same
``(Python)`` modeline), ``C-x b RET`` back to the listing with point
preserved, ``RET`` on a subdirectory (descends), and ``^`` (up, with
point left on the child's line).

The listing body and cursor column are baselined at every dired
checkpoint: the header shows the staged absolute path, and the
owner/group/link counts are real on the Emacs side but synthesized
(``neon neon``) over the VFS, which also shifts the filename column.
The *structure* — point line (modeline ``L<n>``), buffer name padding
(dired's ``%17b``), ``(Dired by name)``, read-only ``%%`` flags, silent
echo area — is what this scenario verifies; the exact listing format is
pinned by ``tests/unit/editor/test_dired.py``.
"""

from __future__ import annotations

from parity.fixtures import make_tree_targets, staged_tree
from parity.harness import ScenarioResult, StepResult

NAME = "31-dired-basics"
DESCRIPTION = "dired layout + n/p/RET/^ navigation over a staged tree."

FILES = {
    "alpha.txt": "alpha line\n",
    "beta.py": "print('beta')\n",
    "sub/gamma.txt": "gamma\n",
}

EXPECTED_DIVERGENCES = {
    "after-open": {"body", "cursor"},
    "after-n-n": {"body", "cursor"},
    "after-p": {"body", "cursor"},
    # after-visit-beta is fully compared — identical file, point, modeline.
    "after-switch-back": {"body", "cursor"},
    "after-descend-sub": {"body", "cursor"},
    "after-up": {"body", "cursor"},
}


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_tree(dirname="tree", files=FILES) as f:
        emacs, neon = make_tree_targets(f, FILES)

        labels = [
            "after-open",
            "after-n-n",
            "after-p",
            "after-visit-beta",
            "after-switch-back",
            "after-descend-sub",
            "after-up",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []
                taken.append(driver.snapshot("after-open"))

                driver.send("n n")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-n-n"))

                driver.send("p")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-p"))

                # Point is on beta.py (L5) — visit it.
                driver.send("RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-visit-beta"))

                # Back to the dired buffer (the C-x b default).
                driver.send("C-x b RET")
                driver.settle(settle_ms=600)
                taken.append(driver.snapshot("after-switch-back"))

                # Down to sub (L6) and descend into it.
                driver.send("n RET")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-descend-sub"))

                driver.send("^")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-up"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
