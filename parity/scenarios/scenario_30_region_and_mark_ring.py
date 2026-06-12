"""Scenario 30 — Inactive mark, region rendering, and the mark ring.

The first scenario to opt into attribute-aware comparison
(``COMPARE_HIGHLIGHTS = True``): snapshots also compare the runs of
reverse-video / non-default-background cells, which is exactly how the
active region (and the modelines) render on a TTY. This is the
verification half of PARITY_HARNESS item 11; the editor half decouples
mark *existence* from mark *activation*:

  * ``active-region``     — ``C-SPC M-f``: the region face covers
    ``alpha`` (run r0:0-5) in both editors.
  * ``after-C-g``         — C-g *deactivates* (echo ``Quit``): highlight
    gone, but the mark survives (later checkpoints prove it).
  * ``after-M->``         — a big motion pushes an *inactive* mark
    (``Mark set``, no highlight).
  * ``after-C-x-C-x``     — exchange-point-and-mark *reactivates*: the
    region from (0,5) to buffer end renders with the face **extending
    to the window edge** on every row whose segment spans the newline
    (the region face's ``:extend``) — runs r0:5-80, r1..r3:0-80.
  * ``after-C-SPC-C-SPC`` — an immediately repeated C-SPC deactivates
    the just-set mark: ``Mark deactivated``, no highlight.
  * ``after-pop-at-mark`` — ``C-u C-SPC`` with point already at the
    mark echoes ``Mark popped`` and rotates the ring.
  * ``after-pop-jump``    — the next ``C-u C-SPC`` jumps silently to
    the rotated-in mark (buffer end).

Every mark/activation rule here was probed against GNU Emacs 29.3
before implementation; the unit contract lives in ``test_mark_ring.py``.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "30-region-and-mark-ring"
DESCRIPTION = "Transient-mark lifecycle + mark ring, with highlight comparison."

COMPARE_HIGHLIGHTS = True

EXPECTED_DIVERGENCES: dict[str, set[str]] = {}

CONTENT = "alpha beta\ngamma delta\nepsilon\nzeta\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_rmr.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "active-region",
            "after-C-g",
            "after-M->",
            "after-C-x-C-x",
            "after-C-SPC-C-SPC",
            "after-pop-at-mark",
            "after-pop-jump",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                driver.send("C-SPC")
                driver.settle(settle_ms=300)
                driver.send("M-f")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("active-region"))

                driver.send("C-g")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-g"))

                driver.send("M->")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M->"))

                driver.send("C-x C-x")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-x-C-x"))

                driver.send("C-SPC")
                driver.settle(settle_ms=300)
                driver.send("C-SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-SPC-C-SPC"))

                driver.send("C-u C-SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-pop-at-mark"))

                driver.send("C-u C-SPC")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-pop-jump"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
