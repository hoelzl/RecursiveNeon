"""Scenario 13 — Kill-ring browse (``M-y`` cycling across multiple kills).

Scenario 06 already checks a single ``C-y`` followed by one ``M-y``. This
one builds a *multi-entry* kill ring and walks the whole ring with
repeated ``M-y``, then probes the precondition that ``yank-pop`` only runs
right after a yank.

Six checkpoints:

  * ``after-three-kills``        — three separated kills push three ring
    entries (an intervening ``C-n`` breaks the kill run so the texts do
    not coalesce into one entry).
  * ``after-C-y-three``          — ``C-y`` yanks the newest kill (``three``)
    and pushes a mark (``Mark set``).
  * ``after-M-y-two``            — first ``M-y`` rotates to the previous
    kill (``two``), replacing the yanked text in place.
  * ``after-M-y-one``            — second ``M-y`` rotates to ``one``.
  * ``after-M-y-wrap-three``     — third ``M-y`` wraps back to ``three``.
  * ``after-M-y-not-after-yank`` — a ``C-b`` breaks the yank run, so the
    next ``M-y`` is *not* immediately after a yank. **Documented
    divergence** (the buffer body matches — only the minibuffer differs):
    GNU Emacs 29 binds ``M-y`` to ``yank-from-kill-ring`` in this state,
    which opens a ``Yank from kill-ring:`` minibuffer to pick an entry
    interactively (this *replaced* the old pre-28 ``Previous command was
    not a yank`` error). neon-edit has no such picker, so its ``yank-pop``
    is a silent no-op — the buffer is left untouched (same as Emacs) but no
    minibuffer opens. See ``docs/PARITY_HARNESS.md`` for the deferred
    ``yank-from-kill-ring`` follow-up.

The first five checkpoints exercise the ring-rotation mechanics and the
in-place replacement and are pixel-perfect; the sixth records the
``yank-from-kill-ring`` feature gap.

Surfaced (and fixed) a real bug on the first run: kills separated by a
non-kill command (here ``C-n``) wrongly *coalesced* into one kill-ring
entry, so ``C-y`` yanked ``onetwothree`` instead of ``three``. neon-edit's
``last_command_type`` marker was only ever reset for the undo chain, never
when an ordinary command broke a kill run, so the next kill appended
instead of pushing. The dispatch now clears it on any non-coalescing,
non-undo command (``editor.py``), matching GNU Emacs resetting
``last-command`` every command.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "13-kill-ring-browse"
DESCRIPTION = "Multi-entry kill ring: build 3 kills, walk with M-y, wrap, precondition."

CONTENT = "one\ntwo\nthree\nfour\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_ringbrowse.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-three-kills",
            "after-C-y-three",
            "after-M-y-two",
            "after-M-y-one",
            "after-M-y-wrap-three",
            "after-M-y-not-after-yank",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Build a three-entry ring. Each C-k kills the line text;
                # the C-n between kills breaks the kill run so the three
                # texts land as *separate* ring entries (newest first:
                # ["three", "two", "one"]).
                driver.send("C-k")  # kill "one"
                driver.settle(settle_ms=300)
                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-k")  # kill "two"
                driver.settle(settle_ms=300)
                driver.send("C-n")
                driver.settle(settle_ms=200)
                driver.send("C-k")  # kill "three"
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-three-kills"))

                # Yank the newest kill at end of buffer.
                driver.send("M->")
                driver.settle(settle_ms=200)
                driver.send("C-y")  # yanks "three"
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-C-y-three"))

                # Walk the ring: each M-y replaces the just-yanked text
                # with the next-older entry, wrapping at the end.
                driver.send("M-y")  # → "two"
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-y-two"))

                driver.send("M-y")  # → "one"
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-y-one"))

                driver.send("M-y")  # wraps → "three"
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-y-wrap-three"))

                # Break the yank run, then M-y: yank-pop's precondition
                # ("previous command was a yank") now fails.
                driver.send("C-b")
                driver.settle(settle_ms=200)
                driver.send("M-y")
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-M-y-not-after-yank"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
