"""Scenario 28 — ``C-x C-b`` (*Buffer List* in another window).

GNU Emacs's ``list-buffers``: a read-only Buffer-menu table displayed in
the *other* window (splitting if there is only one) **without selecting
it** — focus and cursor stay in the current window, no echo message.
neon-edit used to replace the current window with a V1-style table; it
now mirrors Emacs's display, columns and flags (see
``_format_buffer_list``).

The table *content* is necessarily divergent and the ``body`` field is
baselined at both checkpoints: Emacs ``-Q`` always carries
``*scratch*`` (Lisp Interaction), ``*Messages*`` and
``*Async-native-compile-log*`` (which also widen the dynamic name
column) where neon-edit's edit session holds only the visited file
buffer, and the File column shows real OS paths. The *shape* is what the harness
verifies — the ``*Buffer List*`` window's modeline (``-UUU:%%-``,
``(Buffer Menu)``, ``L1``), the cursor staying put, and the silent echo
area. neon-edit's own column layout, flags, MRU ordering, name
truncation and self-exclusion are pinned by the unit tests in
``test_list_buffers.py``.

Checkpoints:

  * ``after-C-x-C-b``  — list popped up in the bottom window.
  * ``after-modify-relist`` — back to one window, modify the file, list
    again: same shape, table now carries the ``*`` modified flag (in the
    baselined body).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "28-list-buffers"
DESCRIPTION = "C-x C-b pops *Buffer List* in the other window without selecting."

EXPECTED_DIVERGENCES = {
    "after-C-x-C-b": {"body"},
    "after-modify-relist": {"body"},
}

CONTENT = "alpha\nbeta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_bl.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-C-x-C-b",
            "after-modify-relist",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send("C-x C-b")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-C-x-C-b"))

                driver.send("C-x 1")
                driver.settle(settle_ms=400)
                driver.send_text("zz")
                driver.settle(settle_ms=400)
                driver.send("C-x C-b")
                driver.settle(settle_ms=800)
                taken.append(driver.snapshot("after-modify-relist"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
