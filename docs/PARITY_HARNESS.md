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
  harness.py                 Driver (pexpect + pyte), Snapshot, TargetSpec
  targets.py                 make_emacs_target / make_neon_target builders
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
  divergences forced is a fine commit boundary). Push to
  `claude/emacs-behavior-parity-bwoWL`.

## Current scenario coverage

(8 scenarios, 26 checkpoints. 21 are pixel-perfect; the 5 remaining
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
  height. Content-dependent; behaviour matches.

## Cosmetic items not yet polished

These are real divergences but low-impact:

1. **Modeline prefix `-UUU:%%-` vs `-UU-:%%-`** for read-only special
   buffers (`*Help*`, `*Completions*`). Emacs widens the coding-system
   mnemonic to 3 chars for the special-buffer class. Single-character
   fix in `view.py::_render_modeline` — detect `read_only` and emit
   three U's.

2. **Split-window proportion when odd**. Emacs gives the *top* window
   the extra row when total height is odd; neon-edit gives it to the
   bottom. Fix is in the view's region computation for split nodes.

3. **Buffer-name padding in modeline**. Emacs right-pads short buffer
   names to a fixed width (`*Help*         `) so the position info
   line up across consecutive renders. Currently we just emit the
   name verbatim.

## Proposed next scenarios

Each is sized for one session if the divergences turn out moderate.

1. **`scenario_09_undo_redo`**: `C-/` undo grouping (consecutive
   typing collapses into one undo unit; coalescing across kill
   commands; `C-g C-/` for redo). Likely to surface gaps in how
   neon-edit chunks edits into undo groups vs Emacs's `command-loop`-
   driven boundaries.

2. **`scenario_10_buffer_switching`**: `C-x b` (switch-to-buffer)
   completion + default suggestion (Emacs offers the
   most-recently-used as the default; neon-edit may not). `C-x C-b`
   (list-buffers) modeline format. `C-x k` (kill-buffer) confirm-if-
   modified flow.

3. **`scenario_11_indentation_and_auto_fill`**: TAB behaviour in
   `python-mode` vs `text-mode` vs `fundamental-mode`. `M-q`
   (fill-paragraph) on a wrapped paragraph. `auto-fill-mode` insertion
   at fill-column.

4. **`scenario_12_modeline_state_flags`**: Watch the modified mnemonic
   transition `---` → `**-` after the first edit; flip read-only with
   `C-x C-q` and confirm `%%-` shows up; line/column readout under
   `column-number-mode` enabled.

5. **`scenario_13_kill_ring_browse`**: `M-y` cycling across multiple
   kills. After several `C-k`, `C-y M-y M-y` should walk back through
   the ring, replacing the just-yanked text in place.

6. **`scenario_14_query_replace`**: `M-%` interactive replace —
   minibuffer flow (`Query replace: ` → `Replace string FOO with: `),
   per-match prompts (`y` / `n` / `q` / `!`), echo-area summary at end.

7. **`scenario_15_register_basics`**: `C-x r SPC <letter>` to save
   point in a register, `C-x r j <letter>` to jump back. Mostly a test
   of whether the binding exists at all.

8. **`scenario_16_minibuffer_history`**: `M-p` / `M-n` in any
   minibuffer prompt to recall previous input. Common Emacs feature
   that's easy to overlook.

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

Past commits on this branch all follow a similar template:

```
<type>: <scenario or area> + <Emacs-shaped fix>

<bullet list of behavioural fixes>

Test pressure: <which tests changed and why, in one paragraph>.
Suite: <N> passing.
Scenario NN: <K>/<K> checkpoints pixel-perfect parity.
```

That format is easy to grep for and tells the next reader exactly what
changed in editor semantics vs. what's just test bookkeeping.

## Branch

All work lives on `claude/emacs-behavior-parity-bwoWL`. Push as you
go (`git push -u origin claude/emacs-behavior-parity-bwoWL`); the user
will review and merge from there. Don't create PRs unless asked.
