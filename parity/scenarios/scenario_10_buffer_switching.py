"""Scenario 10 — Buffer switching with defaults (``C-x b``, ``C-x k``).

Both commands key off the "default buffer" idiom: Emacs shows the
most-recently-used *other* buffer as the default in the prompt and uses
it when you press RET on empty input. This scenario builds a second
buffer so the default is a shared, user-created buffer (avoiding Emacs's
``*scratch*``/``*Messages*``, which neon-edit has no equivalent of).

Checkpoints (one launch per target, path-dependent):

  * ``after-create-second``   — ``C-x b second RET`` creates+selects "second"
  * ``after-C-x-b-prompt``    — ``C-x b`` shows "Switch to buffer (default …)"
  * ``after-switch-default``  — RET on empty input switches to the default
  * ``after-C-x-k-prompt``    — ``C-x k`` shows "Kill buffer (default …)"
  * ``after-kill-second``     — type "second" RET kills it, back to the file

Headline divergence (now fixed): neon-edit's ``C-x b`` prompt was a bare
"Switch to buffer: " with no default, and RET on empty input did nothing;
``C-x k`` *pre-filled* the current buffer name into the input instead of
offering it as a default, and both creating a buffer ("(New buffer X)")
and killing one ("Killed buffer X") echoed messages Emacs does not. GNU
Emacs shows the MRU "other" buffer as a parenthesised default, acts on it
for empty input, and is silent on buffer create/kill. The fix adds
buffer-recency tracking (``Editor.other_buffer_name``) and the Emacs-style
"(default X)" prompts, switches to the default on empty input, and drops
the extra messages. After the fix the echo area, cursor, and switching
behaviour match Emacs at every checkpoint.

One residual divergence is a *documented, pre-existing* cosmetic: the
modeline of the no-file "second" buffer differs in the coding-system
mnemonic (``-UUU:`` vs ``-UU-:``) and right-pads short buffer names to a
min width (``%12b``) that neon-edit does not. These are the same
modeline-rendering gaps already noted for ``*Help*`` (PARITY_HARNESS.md
cosmetic items #1 and #3); they belong to the modeline work (proposed
scenario 12), not to buffer switching, so they are left as-is here. File
buffers (whose names exceed the min width) match exactly.

``C-x C-b`` (list-buffers) is intentionally *not* covered here: Emacs pops
``*Buffer List*`` in a split window with a "CRM Buffer Size Mode File"
table that lists ``*scratch*``/``*Messages*`` too, so its parity is a
distinct, larger piece of work (different window handling, table format,
and buffer model) — it gets its own scenario. Likewise ``C-x k``'s
confirm-if-modified flow ("Buffer X modified; kill anyway?") isn't
exercised here because the buffer killed ("second") is empty/unmodified.
"""

from __future__ import annotations

from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult


NAME = "10-buffer-switching"
DESCRIPTION = "C-x b / C-x k default-buffer prompts and empty-input behaviour."

CONTENT = "buffer one\n"


def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_buf.txt", content=CONTENT) as f:
        emacs, neon = make_targets(f)

        labels = [
            "after-create-second",
            "after-C-x-b-prompt",
            "after-switch-default",
            "after-C-x-k-prompt",
            "after-kill-second",
        ]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken: list = []

                # Create a second buffer "second" and select it.
                driver.send("C-x b")
                driver.settle(settle_ms=400)
                driver.send("second")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-create-second"))

                # C-x b again: the prompt should now offer the file buffer
                # (the MRU "other" buffer) as the default.
                driver.send("C-x b")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-x-b-prompt"))

                # RET on empty input → switch to the default (the file).
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-switch-default"))

                # C-x k: the kill prompt should offer the current buffer as
                # the default (not pre-fill it into the editable input).
                driver.send("C-x k")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-C-x-k-prompt"))

                # Kill "second" explicitly (it is empty → no modified prompt).
                driver.send("second")
                driver.settle(settle_ms=300)
                driver.send("RET")
                driver.settle(settle_ms=500)
                taken.append(driver.snapshot("after-kill-second"))

                snapshots[target.name] = taken

        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)

    return result
