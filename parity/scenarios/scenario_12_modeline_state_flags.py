"""Scenario 12 — Modeline state flags (modified / read-only / no-file).

Watches the modeline's left-edge mnemonics change as buffer state changes:

  * ``after-edit``      — first self-insert flips ``---`` → ``**-`` (modified)
  * ``after-cxb-notes`` — a fresh no-file buffer shows ``-UUU:`` and a
                          name padded to a 12-column minimum (``%12b``)
  * ``after-C-x-C-q``   — ``read-only-mode`` flips the buffer read-only,
                          so the mnemonic becomes ``%%-``

Divergences this targets:

  * **No-file coding mnemonic** ``-UUU:`` vs ``-UU-:``. Emacs widens the
    third mnemonic column to ``U`` for a buffer that is *not visiting a
    file* (``*scratch*``, ``*Help*``, a ``C-x b`` buffer); neon-edit
    hard-coded ``-UU-:``. (PARITY_HARNESS.md cosmetic #1; also clears the
    no-file modeline diff carried over from scenario 10.)
  * **Buffer-name padding** ``%12b``. Emacs right-pads short buffer names
    to a 12-column minimum so the position columns line up; neon-edit
    emitted the name verbatim. (cosmetic #3.) Every parity *file* buffer
    name already exceeds 12 columns, so this only affects short no-file
    names and does not disturb the file-buffer checkpoints.
  * **Read-only toggle** ``C-x C-q``. Emacs binds it to ``read-only-mode``;
    neon-edit had no such command or binding, so ``C-x C-q`` was
    "undefined" and the ``%%-`` mnemonic was unreachable interactively.

All three are fixed alongside this module. The modified mnemonic
(``---`` ↔ ``**-``) already matched Emacs and is included as a baseline.

Out of scope (their own follow-ups): ``column-number-mode`` position
format, and Emacs clearing the modified mnemonic when *undo* restores the
saved-on-disk content (an undo-system feature — the ``(t . TIME)`` undo
record — not modeline rendering; the carried-over note from scenario 09
stays open).
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "12-modeline-state-flags"
DESCRIPTION = "Modeline mnemonics: modified (**), no-file (-UUU:), read-only (%%)."

CONTENT = "hello world\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_state.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = ["after-edit", "after-cxb-notes", "after-C-x-C-q"]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # A single self-insert flips the modified mnemonic to **-.
                driver.send("X")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-edit"))

                # A fresh no-file buffer: -UUU: mnemonic + 12-col name pad.
                driver.send("C-x b")
                driver.settle(settle_ms=400)
                driver.send("notes")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-cxb-notes"))

                # Toggle read-only: the mnemonic becomes %%- (unmodified RO).
                driver.send("C-x C-q")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-x-C-q"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
