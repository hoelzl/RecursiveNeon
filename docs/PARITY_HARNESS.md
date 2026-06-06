# Parity Harness — Handover

A pty-driven harness under `parity/` runs GNU Emacs and `neon-edit`
side-by-side on identical scripted input and diffs the resulting screen
state. Use it to find Emacs/neon-edit divergences, fix them in
neon-edit, and prevent regressions by treating each scenario as a
living checkpoint.

CLAUDE.md says **Emacs is the ground truth** for the editor: if a
divergence is surfaced, the default action is to fix neon-edit. Deviate
only when matching Emacs is disproportionately complex for our
synchronous TUI model (and document the deviation next to the diverging
code).

## Where things live

```
parity/
  keys.py                    Emacs-style key descriptions → pty bytes
                             (e.g. "C-x C-s", "M-x", "RET", "<up>")
  harness.py                 Driver (pexpect + pyte), Snapshot, TargetSpec;
                             Driver.wait_for (wait for a readiness condition
                             on screen, not just an output-silence window)
  targets.py                 make_emacs_target / make_neon_target builders;
                             NEON_PARITY_PYTHON env override for the neon venv
  fixtures.py                staged_file context manager + make_targets pair
  report.py                  side-by-side diff renderer
  run.py                     python -m parity.run [--list] [pattern]
  scenarios/
    scenario_01_startup.py
    scenario_02_end_of_buffer.py
    scenario_03_mx_minibuffer.py
    scenario_04_find_file_prompt.py
    scenario_05_describe_key.py
    scenario_06_kill_and_yank.py
    scenario_07_isearch.py
    scenario_08_region.py
    scenario_09_undo_redo.py
    scenario_10_buffer_switching.py
    scenario_11_fill_paragraph.py
    scenario_12_modeline_state_flags.py
    scenario_13_kill_ring_browse.py
    scenario_14_query_replace.py
    scenario_15_register_basics.py
```

Every scenario module exposes `NAME`, `DESCRIPTION`, and `run() -> ScenarioResult`.

## Environment setup

```bash
# emacs-nox + Python deps the harness needs on top of the project deps.
sudo apt-get install -y emacs-nox
uv venv --python 3.13 .venv
uv pip install -e "./backend[dev]" pyte pexpect
```

**Python version note.** The project targets 3.14 long-term, but
CPython 3.14.0rc2 dropped the `prefer_fwd_module` kwarg that the pinned
pydantic 2.13.4 still passes to `typing._eval_type`. Use 3.13 until
pydantic ships a 3.14-compatible release. The CLAUDE.md and the
`.venv` bootstrap already note this.

### Running the harness from a Windows checkout via WSL

The harness is pty-based (pexpect/pyte) and Unix-only, but it runs fine
against a Windows checkout driven through WSL (emacs-nox + a Linux Python
live in WSL; the repo lives on `/mnt/c/...`). Two host-specific wrinkles:

1. **Separate Linux venv.** On a Windows checkout, `<repo>/.venv` is a
   *Windows* venv (`Scripts/python.exe`, no `bin/python`), so it can't run
   the pty harness. Create a Linux venv outside the repo and point the
   harness at it with `NEON_PARITY_PYTHON`:

   ```bash
   uv venv --python 3.13 ~/parity-venv
   uv pip install --python ~/parity-venv/bin/python \
       -e /mnt/c/.../RecursiveNeon/backend[dev] pexpect pyte
   export NEON_PARITY_PYTHON=~/parity-venv/bin/python   # read by parity/targets.py
   cd /mnt/c/.../RecursiveNeon && ~/parity-venv/bin/python -m parity.run 09
   ```

   `parity/targets.py` falls back to `<repo>/.venv/bin/python` when the env
   var is unset, so a native Linux checkout needs no change.

2. **Slow cold start.** Importing neon-edit's source over `/mnt/c` takes
   several seconds of *silence*. A pure-silence `settle()` would return
   before the shell prompt (or editor) has painted, so the neon launch now
   waits for a readiness *condition* via `Driver.wait_for` (the shell
   prompt `neon-proxy:`, then the editor modeline) instead of a fixed
   silence window. This is host-independent and harmless on fast hosts.

   Driving `wsl bash` from Windows git-bash has two traps worth knowing:
   git-bash path-mangles a bare `/mnt/...` *argument* (e.g. `wsl bash
   /mnt/c/x.sh` → `C:/Program Files/Git/mnt/c/x.sh`), and `$VAR` inside
   `wsl bash -lc '...'` gets double-evaluated. Both are avoided by putting
   the work in a **script file** and invoking it with the path *inside*
   quotes: `wsl bash -lc 'bash /mnt/c/.../run.sh 09'`.

## Running scenarios

```bash
.venv/bin/python -m parity.run            # all scenarios
.venv/bin/python -m parity.run 03         # scenarios matching '03'
.venv/bin/python -m parity.run --list     # just list available scenarios
```

Reports go to stdout. For a compact pass/fail-by-field view:

```bash
.venv/bin/python -m parity.run | grep -E "^## Step:|^- (modeline|echo_area|cursor):"
```

For the full diff with body rows and structured fields, redirect to a
file and scroll:

```bash
.venv/bin/python -m parity.run 07 > /tmp/p07.txt
less /tmp/p07.txt
```

## The workflow

### Adding a scenario

1. Copy an existing scenario as a template (06 is a good moderately-
   complex starting point, 02 if you want the simplest possible).
2. Update `NAME`, `DESCRIPTION`, file content, and the keystroke
   sequence.
3. Run it. Expect divergences on the first run — that's the point.

A scenario is just:

```python
from parity.fixtures import make_targets, staged_file
from parity.harness import ScenarioResult, StepResult

NAME = "NN-short-name"
DESCRIPTION = "One-line summary."

def run() -> ScenarioResult:
    result = ScenarioResult(name=NAME, description=DESCRIPTION)
    with staged_file(basename="parity_NN.txt", content="...") as f:
        emacs, neon = make_targets(f)
        labels = ["after-X", "after-Y", ...]
        snapshots: dict[str, list] = {}
        for target in (emacs, neon):
            with target.launch() as driver:
                taken = []
                driver.send("C-x C-s")          # any Emacs-style chord
                driver.settle(settle_ms=400)
                taken.append(driver.snapshot("after-X"))
                ...
                snapshots[target.name] = taken
        for i, label in enumerate(labels):
            step = StepResult(label=label)
            for name, snaps in snapshots.items():
                step.snapshots[name] = snaps[i]
            result.steps.append(step)
    return result
```

Key conventions:

- One launch per target per scenario when checkpoints are
  path-dependent (the editor's state at checkpoint N depends on
  checkpoint N-1). Use a separate launch per target only if the
  scenario is genuinely "open and observe" with no follow-up keys.
- `settle_ms=400-1200`. Bump up for slow-rendering operations
  (popup buffers, isearch). Emacs needs ~1000-1500ms for `*Help*`
  or `*Completions*` to fully paint.
- The first keystroke after launch may need extra settle — Emacs
  sometimes lags on the first input.
- Backspace is `"DEL"` (or `"BACKSPACE"`); RET is `"RET"`.
- `"C-SPC"` (set-mark) is translated to NUL — supported.

### When a scenario surfaces a divergence

Three flavours:

1. **neon-edit is wrong** → fix neon-edit (most common). Track down
   the offending code in `backend/src/recursive_neon/editor/`, fix
   it to match Emacs, update any tests that asserted the divergent
   behaviour, rerun the scenario.

2. **neon-edit is "right" for game semantics** (e.g. virtual filesystem
   path in find-file prompt — see scenario 04) → document the
   intentional deviation in the scenario's module docstring and in
   the diverging code's comments.

3. **Emacs and neon-edit have legitimately different content** (e.g.
   different command sets, different docstring length) → leave the
   scenario as-is. The diff is informative even when it's "expected
   to differ". If a step has only content differences (not behaviour
   differences), call that out in the scenario doc.

### When you fix a divergence

- Run the affected scenario and verify it now matches.
- Run the **full** test suite (`cd backend && ../.venv/bin/pytest tests/ -q --no-cov`).
  Some Emacs-style fixes break tests that codified the prior
  divergent behaviour. Update those tests — they were wrong, the new
  behaviour is the ground truth. Add a comment to the updated test
  noting the Emacs convention so the next reader doesn't think you
  loosened it.
- Run **all** scenarios to make sure no other scenario regressed.
- Commit per logical group (one scenario + the fixes its
  divergences forced is a fine commit boundary), then push and open a
  PR right away — see "Branch and PR workflow" below. No need to ask
  first.

## Current scenario coverage

(15 scenarios, 58 checkpoints. 49 are pixel-perfect; the 9 remaining
diffs are content/semantic differences explained below.)

| # | Scenario | Coverage |
|---|----------|----------|
| 01 | startup | file opens, modeline, blank rows past EOB, .txt auto-mode |
| 02 | end-of-buffer | `C-n` past last line → `End of buffer`, point at point-max |
| 03 | M-x completion | minibuffer prompt, common-prefix TAB, `*Completions*` popup |
| 04 | find-file | prompt text, cwd pre-fill, `C-g` cancel → `Quit` |
| 05 | describe-key | `C-h k`, `*Help*` split + help-mode, q-to-dismiss hint |
| 06 | kill / yank | `C-k`, `C-y` (sets mark), `M-w`, `C-w`, `M-y` |
| 07 | isearch | `C-s` prompt + match cursor + case-sensitive + Mark saved |
| 08 | region | `C-SPC`, `M-f` extension, `C-x C-x` swap |
| 09 | undo / redo | `C-/` grouping, history walk-back, exhaustion, `C-f`+`C-/` redo, `Undo`/`Redo` echo |
| 10 | buffer switching | `C-x b` MRU default + empty-RET-to-default, `C-x k` `(default …)` prompt, silent create/kill |
| 11 | fill paragraph | `M-q` re-wrap at fill-column, silent on success/no-op, point left at paragraph start |
| 12 | modeline state flags | modified `**`, no-file `-UUU:`, `%12b` name padding, `C-x C-q` read-only `%%-` |
| 13 | kill-ring browse | multi-entry ring, `C-y`+repeated `M-y` cycle/wrap, kills split by a move don't coalesce, `M-y`-not-after-yank gap |
| 14 | query-replace | `M-%` two-prompt entry, per-match `y`/`n`, point at match end on deck, `Replaced N occurrence(s)` plural summary |
| 15 | register basics | `C-x r SPC`/`C-x r j` point save/jump + name-read prompts; `M-<`/`M->`/jump push a mark (`Mark set`) |

## Known intentional divergences

These are the diffs that are *not* bugs — don't try to "fix" them:

- **04 path text** (`Find file: /tmp/parity-XXXX/` vs `Find file: /`).
  Emacs reports the real OS cwd; neon-edit reports the virtual-FS root.
  The in-game editor is sandboxed to the virtual filesystem; that
  semantic mismatch is by design.

- **03 after-TAB** (`M-x for` + 1 TAB shows different things).
  Emacs has ~30 commands matching `for*`; neon-edit has 3
  (`forward-char`/`-word`/`-sentence`), all sharing the prefix
  `forward-`. One TAB therefore extends to `forward-` in neon-edit
  but stays at `for` in Emacs (which can't extend further and pops up
  `*Completions*` instead). The popup behaviour itself matches once
  both sides reach the "common prefix can't extend" state (see
  scenario 03's `after-TAB-TAB` checkpoint).

- **05 modeline `Top` vs `All`**. Emacs's `*Help*` doc for
  `forward-char` is several lines longer than neon-edit's auto-
  generated `defcommand` docstring, so it scrolls past the window
  height. Content-dependent; behaviour matches. (The `-UUU:` prefix and
  `*Help*` name padding that used to differ here were fixed in scenario
  12; only this `Top`/`All` position indicator now differs.)

- **09 modeline `--` vs `**` after undo-to-saved** (checkpoints
  `after-undo-AB`, `after-undo-exhausted`). Emacs clears the modified
  mnemonic once undo brings the buffer back to its saved-on-disk content;
  neon-edit keeps it modified. This was *expected* to land in scenario 12,
  but it is **not** a modeline-rendering issue — it is save-state-through-
  undo tracking (Emacs records the buffer-modified state in `(t . TIME)`
  undo entries and `primitive-undo` restores it). Scenario 12 fixed the
  pure-rendering mnemonics (`-UUU:`, padding, `C-x C-q`) but left this for
  its own follow-up: neon-edit would need to record the undo-list position
  at save time and clear `modified` when undo/redo returns to it.

- **09 redo cursor `col 0` vs `col 2`** (checkpoint `after-redo`). Emacs's
  `primitive-undo` encodes per operation where point should land when a
  deletion record is reinserted (via the sign of the recorded position),
  so a *redone* insertion leaves point at the start of the reinserted
  text; neon-edit's coarser undo-record model leaves point at the end.
  Matching exactly would mean threading point intent through
  `Buffer.undo`'s reverse-entry construction and would churn scenario 06 +
  the undo test suite — disproportionate for a one-cell difference. The
  echo-area feedback (`Undo`/`Redo`), buffer content, and the cursor on
  every *forward* undo all match.

- **13 `M-y` not after a yank → `yank-from-kill-ring`** (checkpoint
  `after-M-y-not-after-yank`). The buffer body matches (both leave it
  untouched); only the minibuffer differs. GNU Emacs ≥28 rebinds `M-y` so
  that, when the previous command was *not* a yank, it runs
  `yank-from-kill-ring` — an interactive `Yank from kill-ring:` minibuffer
  that lets you pick any ring entry (this *replaced* the pre-28 `Previous
  command was not a yank` error). neon-edit has no such picker, so its
  `yank-pop` is a silent no-op in that state. Implementing the picker
  (minibuffer completion over the ring, multi-line entry display, M-n/M-p
  navigation) is a feature in its own right — deferred to a future
  `scenario_NN_yank_from_kill_ring` (see "Proposed next scenarios"). The
  normal cycle (`C-y` then repeated `M-y`) is pixel-perfect.

## Cosmetic items not yet polished

These are real divergences but low-impact:

1. ~~**Modeline prefix `-UUU:` vs `-UU-:`** for buffers not visiting a
   file.~~ **FIXED in scenario 12.** `view.py::_render_modeline` now keys
   the third `U` off "buffer has no filepath". Cleared the no-file modeline
   diffs in scenarios 10 (`second`, now pixel-perfect) and shrank 05
   (`*Help*`) / 03 (`*Completions*`) to their content-only diffs.

2. **Split-window proportion when odd**. Emacs gives the *top* window
   the extra row when total height is odd; neon-edit gives it to the
   bottom. Fix is in the view's region computation for split nodes.

3. ~~**Buffer-name padding in modeline** (`%12b`).~~ **FIXED in scenario
   12.** `_render_modeline` now right-pads the name to a 12-column minimum.
   Every parity *file* buffer name already exceeds 12 columns, so only the
   short no-file names (`*Help*`, `second`, …) changed — no file-buffer
   checkpoint was disturbed.

## Proposed next scenarios

Each is sized for one session if the divergences turn out moderate.

1. ~~**`scenario_09_undo_redo`**~~ **DONE.** `C-/` grouping, history
   walk-back, exhaustion, and `C-f`+`C-/` redo. Surfaced that neon-edit
   was silent on a successful undo whereas Emacs echoes `Undo`/`Redo`;
   fixed by tracking redo-ness on the undo boundary and echoing the same
   words. Two residual diffs are documented deviations (modified mnemonic
   after undo-to-saved → owned by scenario 12 below; redo cursor landing →
   Emacs `primitive-undo` point-sign semantics). See "Known intentional
   divergences".

2. ~~**`scenario_10_buffer_switching`**~~ **DONE (switch-to-buffer +
   kill-buffer defaults).** `C-x b` now offers the MRU "other" buffer as
   the `(default …)` and switches to it on empty RET; `C-x k` offers the
   current buffer as a prompt default instead of pre-filling it; buffer
   create/kill are now silent like Emacs. Added `Editor.other_buffer_name`
   + recency tracking. (The residual no-file-buffer modeline cosmetics were
   since fixed in scenario 12, so scenario 10 is now fully pixel-perfect.)
   **Still TODO in a follow-up scenario:** `C-x C-b`
   (list-buffers) — Emacs pops `*Buffer List*` in a *split* window with a
   "CRM Buffer Size Mode File" table that also lists `*scratch*`/
   `*Messages*` (neon-edit replaces the current window and has a different
   table + buffer model); and `C-x k`'s confirm-if-modified flow ("Buffer
   X modified; kill anyway? (yes or no)"), which neon-edit lacks.

3. ~~**`scenario_11_indentation_and_auto_fill`**~~ → split. **DONE:
   `scenario_11_fill_paragraph`** — `M-q` re-wraps to fill-column (70),
   is now *silent* on success and on a no-op re-fill (was "Filled
   paragraph" / "Paragraph unchanged"), and leaves point at the paragraph
   start (was trailing to the end of the insert). Both checkpoints
   pixel-perfect. Note: with single-spaced input Emacs does *not* create
   two-space sentence breaks (it only preserves existing ones), so no
   double-space divergence arose. **Still TODO in their own scenarios:**
   - **TAB / `indent-for-tab-command`** — neon-edit binds no TAB in text
     buffers (TAB is "undefined" everywhere); Emacs runs `indent-relative`
     / `tab-to-tab-stop` in fundamental/text-mode (TAB on the empty first
     line inserts a real tab → column 8) and syntactic, cycling indent in
     `python-mode`. A large, mode-specific feature.
   - **`auto-fill-mode` insertion** — break-on-space past fill-column; has
     its own mode-enable echo and ` Fill` modeline indicator to diff.

4. ~~**`scenario_12_modeline_state_flags`**~~ **DONE.** Modified mnemonic
   `---`↔`**-` (already matched); added the no-file `-UUU:` mnemonic and
   `%12b` name padding to `_render_modeline`; added a `read-only-mode`
   command bound to `C-x C-q` (echoes `Read-Only mode enabled in current
   buffer`, flips the mnemonic to `%%-`). All 3 checkpoints pixel-perfect,
   and the fix resolved scenario 10's residual cosmetics and shrank 03/05.
   **Still TODO in their own follow-ups:** `column-number-mode` position
   format; and the undo-to-saved modified-flag carry-over from scenario 09
   (an undo-system feature, not modeline rendering — see "Known intentional
   divergences").

5. ~~**`scenario_13_kill_ring_browse`**~~ **DONE.** Built a three-entry
   ring (`C-k C-n C-k C-n C-k`), then walked it with `C-y` + repeated
   `M-y`, including the wrap-around. Surfaced a real bug: kills separated
   by a non-kill command (the `C-n`) *coalesced* into one ring entry, so
   `C-y` yanked `onetwothree` instead of `three`. Root cause: the dispatch
   reset `last_command_type` only for the undo chain, so the marker stayed
   `"kill"` across the move and the next kill appended. Fixed by clearing
   it on any non-coalescing, non-undo command in `editor.py` (mirrors GNU
   Emacs resetting `last-command` every command); checkpoints 1–5 are
   pixel-perfect. The 6th checkpoint documents the Emacs-29
   `yank-from-kill-ring` gap (see item 9 and "Known intentional
   divergences").

6. ~~**`scenario_14_query_replace`**~~ **DONE.** Drove the full `M-%`
   flow — both entry prompts, the per-match prompt, `y`/`n` decisions, and
   the closing summary. The prompts already matched Emacs exactly
   (including `(? for help)`); two real divergences were fixed: (a) on
   deck, neon-edit left point at the match *start* whereas Emacs leaves it
   at the match *end* — the session now tracks the match start explicitly
   and parks point at the end (the highlight already accepts point at
   either boundary, so the current-match emphasis still renders); and (b)
   the summary said `Replaced N occurrence(s)` instead of Emacs's
   pluralised `Replaced N occurrence` / `occurrences` (now shared with the
   `replace-string` formula). All 6 checkpoints pixel-perfect; the
   singular/plural forms were both verified against Emacs via the harness.

7. ~~**`scenario_15_register_basics`**~~ **DONE.** neon-edit had *no*
   register support, so this added point registers from scratch:
   `point-to-register` (`C-x r SPC`) and `jump-to-register` (`C-x r j`),
   each reading the next key as the register name (the describe-key
   capture pattern), plus a `C-x r` prefix map. The prompts (`Point to
   register: ` / `Jump to register: `) and the save/jump round-trip match
   Emacs exactly. The scenario also surfaced that **`M-<` / `M->` and
   `jump-to-register` push a mark** (`Mark set`) in Emacs — neon-edit
   didn't — fixed by `_push_mark_for_big_motion` (push unless prefix arg /
   active region) and an unconditional push in the jump. All 5 checkpoints
   pixel-perfect. **Documented deviation:** neon-edit has no inactive-mark
   concept, so a pushed mark is *active* (the region renders highlighted)
   whereas Emacs's push-mark is inactive — invisible to the text-only
   harness, noted next to the code. **Still TODO** (own scenarios): the
   rest of the `C-x r` family — `copy-to-register` (`s`), `insert-register`
   (`i`), number / rectangle / window registers, and the register preview.

8. **`scenario_16_minibuffer_history`**: `M-p` / `M-n` in any
   minibuffer prompt to recall previous input. Common Emacs feature
   that's easy to overlook.

9. **`scenario_NN_yank_from_kill_ring`** (deferred from scenario 13):
   implement and verify `yank-from-kill-ring` — the command GNU Emacs ≥28
   binds to `M-y` when the previous command was *not* a yank. It opens a
   `Yank from kill-ring:` minibuffer with the ring entries as completion
   candidates (multi-line entries shown with a separator), `M-n`/`M-p` to
   navigate, `RET` to insert the chosen entry at point (and push a mark,
   like yank). neon-edit currently no-ops `M-y` in that state. This is a
   real feature, not a one-line fix, which is why scenario 13 left it as a
   documented divergence rather than expanding scope.

## Tips and gotchas

- **The "is undefined" canary.** When you write a scenario using a
  key that isn't bound in neon-edit, the editor surfaces
  `<key> is undefined` in the echo area instead of doing nothing.
  Treat that as a flag that you've found a missing binding.

- **`'str' object is not callable` came up once.** It was from
  calling `Buffer.region_text` as a method — but it's a `@property`.
  Watch for properties masquerading as methods if you add Buffer-level
  helpers.

- **C-SPC handling.** On Unix, NUL bytes (`\x00`) from `C-SPC` go
  through `backend/src/recursive_neon/shell/keys.py::CTRL_KEYS`.
  We've already added the `"\x00": "C-space"` mapping; just be
  aware that the keymap binding is `"C-space"` (with a hyphen),
  not `"C-SPC"`.

- **Emacs needs a kick after `-Q`.** The first render after launch
  shows `*scratch*` even when a file was passed on the command line;
  the file buffer only paints after the first input event. Our
  harness sends `C-f C-b` (no-op forward + back) to flush this.
  Don't remove it.

- **Some emacs renders are slow.** `*Help*` and `*Completions*`
  pop-ups take 800-1500ms to fully render. If a scenario flaps,
  bump that step's `settle_ms`.

- **The harness's `make_targets` returns an (emacs, neon) pair from
  one `FileFixture`.** It handles writing the file to disk *and*
  generating the matching neon-edit shell `echo` commands so the
  virtual filesystem ends up byte-identical to the host file. Use it
  rather than re-inventing setup per scenario.

- **Don't compare attrs.** Snapshots are text-only by design. ANSI
  colour comparison is noisier than it's worth at the parity level we
  care about. If you need attribute-level checks, scope them to a
  dedicated rendering test, not the parity scenarios.

- **Run all scenarios after editor changes.** Fixes in shared code
  (`_resolve_keymap`, `_render_modeline`, etc.) can ripple. The full
  parity run is fast (~minutes).

## Commit conventions

Past parity commits all follow a similar template:

```
<type>: <scenario or area> + <Emacs-shaped fix>

<bullet list of behavioural fixes>

Test pressure: <which tests changed and why, in one paragraph>.
Suite: <N> passing.
Scenario NN: <K>/<K> checkpoints pixel-perfect parity.
```

That format is easy to grep for and tells the next reader exactly what
changed in editor semantics vs. what's just test bookkeeping.

## Branch and PR workflow

Each scenario lands on its **own branch** named `claude/parity-scenario-NN`
and gets its **own PR**. Both are created as soon as the scenario is done —
**push and open the PR without pausing to ask for confirmation.**

**Always branch off `origin/master`; never stack one scenario branch on
another.** This repo merges PRs with *rebase-and-merge* / *squash-and-merge*
(merge commits are disabled), and both rewrite history: when a PR merges its
commits land on `master` under *new* SHAs. A branch stacked on that parent
still carries the parent's *old*-SHA commit, so the moment the parent merges
the child conflicts on every file the parent touched and needs a
`git rebase --onto origin/master <old-parent-tip>` to drop the now-duplicated
commit. Branching each scenario straight off `master` avoids this entirely —
the branch has only its own commit, so there is nothing to duplicate.

To keep even the `PARITY_HARNESS.md` edits conflict-free, **let each
scenario's PR merge before starting the next**: the fresh `master` then
already has the prior scenario's doc edits, and yours stack on them cleanly.
If you must start the next scenario before the previous one merges, keep the
doc edits append-only and don't *both* rewrite the aggregate count line under
"Current scenario coverage" — that single line is the only place concurrent
scenario branches collide.

When a scenario is complete — written, run, every divergence fixed or
documented, tests updated, and **the full backend suite + all parity
scenarios green** (ruff / ruff-format / mypy clean, pre-commit hooks
passing):

1. **Branch off the latest master.**
   `git fetch origin && git checkout -b claude/parity-scenario-NN origin/master`.
2. **Commit** per logical group (one scenario + the fixes its divergences
   forced; see Commit conventions above). End commit messages with the
   `Co-Authored-By` trailer.
3. **Push immediately** — don't wait to be asked:
   `git push -u origin claude/parity-scenario-NN`.
4. **Open a PR immediately against `master`** — don't wait to be asked:
   `gh pr create --base master --head claude/parity-scenario-NN --title … --body-file -`.
   End the PR body with the Claude Code attribution line.

If `master` has advanced since you branched, `git fetch origin && git rebase
origin/master` before pushing so GitHub shows the PR mergeable.

The user reviews and merges the PRs. (Historical note: scenarios 01–08 once
lived on a single `claude/emacs-behavior-parity-bwoWL` branch, later
replaced by stacked per-scenario branches; both are superseded by the
branch-off-`master` rule above, which is what keeps PRs conflict-free under
rebase/squash merging.)
