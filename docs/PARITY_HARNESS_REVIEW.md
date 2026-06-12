# Parity Effort Review — 2026-06-12

A point-in-time review of the editor architecture and the Emacs-parity
effort (scenarios 01–20), done after all 20 scenario PRs merged. Judges
the progress claimed in `PARITY_HARNESS.md` against the code, and
evaluates whether continuing the scenario-by-scenario approach leads to
the desired outcome ("the editor genuinely feels like Emacs").

## Verdict

The effort is healthy and genuinely converging. The handover is
accurate, honest about residual divergences, and the architecture has
absorbed 20 scenarios of fixes without accumulating hacks. **Continuing
the approach is the right call** — but the harness's "prevent
regressions" promise is currently an illusion (no automated pass/fail,
not in CI, no Emacs version pinning). One hardening session on the
harness is higher-leverage than scenario 21.

## Claims verified against the code

- **78 checkpoints across 20 scenarios — confirmed** by counting
  snapshot labels in every scenario file. The "69 pixel-perfect / 9
  explained" split is consistent with the documented deviations.
- **Divergences are honestly documented.** At least 9 scenarios carry
  per-checkpoint divergence docstrings (e.g.
  `scenario_09_undo_redo.py` explains the undo-to-saved modified-flag
  gap and the redo cursor landing; `scenario_13_kill_ring_browse.py`
  explains the Emacs ≥28 `yank-from-kill-ring` gap). Each is classified
  as fix-later / intentional game semantics / content-only — exactly
  the triage the workflow prescribes.
- All 20 scenario branches merged cleanly under the branch-off-master
  rule. ~25 deviation comments exist in the editor source, localized,
  each with a rationale — disciplined, not patchwork.
- **Where perceived progress overstates reality:** "treating each
  scenario as a living checkpoint" describes a *manual* process.
  `parity/run.py` historically always exited 0 and only printed a diff
  report; nothing imported the parity package from pytest; CI runs
  ruff/mypy/pytest only — no emacs, no parity. Every "pixel-perfect"
  claim was a point-in-time human observation. *(Addressed: the harness
  now asserts — see "Hardening work" below.)*

## Architecture state

Structurally sound for this work:

- **Dispatch** mirrors Emacs's command loop: capture sessions
  (describe-key, query-replace, registers) → ESC-as-Meta state machine
  → minibuffer routing → C-g intercept → keymap lookup with
  Emacs-equivalent precedence (buffer-local > minor > major > global),
  prefix args, undo boundaries, and the scenario-13 `last-command`
  reset fix.
- **Rendering** earned its parity: the modeline reproduces Emacs's TTY
  format exactly (`-UU-:`/`-UUU:` mnemonics, `%12b` padding, `%%-`
  read-only); the `StyleSpan` post-compose pass (Option A) has held up
  and the cell-attribute grid (Option D) hasn't been needed.

### Known structural gaps (all documented in code), in order of bite

1. **Undo doesn't record save-points** (`editor/undo.py` has no
   analogue of Emacs's `(t . TIME)` entries; `Buffer.modified` is
   binary). Already a *visible* parity diff — scenario 09's
   undo-to-saved modified-flag residual. First structural item worth
   scheduling.
2. **Mark is always active** (`buffer.py` — `region_active ⟺ mark is
   not None`; no inactive mark, no mark ring). Invisible to the
   text-only harness — which means the harness *cannot* drive this part
   of Emacs feel.
3. **Minibuffer is a widget, not a buffer** (`minibuffer.py` — string +
   ad-hoc `key_handlers`, patched `process_key`). Fine and arguably
   cleaner for everything done so far; caps future parity at recursive
   minibuffers, minibuffer-local keymaps, richer completion styles. The
   `yank-from-kill-ring` picker will lean on this widget.
4. **`default_commands.py` is ~2,750 lines** and the destination of
   every new command. Not a god-module yet; isearch / query-replace /
   registers are natural seams to split along before it becomes one.

## Remaining work queued in the handover

`yank-from-kill-ring` picker; `C-x C-b` list-buffers in a split window;
`kill-buffer` confirm-if-modified; full
`python-indent-calculate-levels`; `column-number-mode`; the rest of the
`C-x r` register family; `replace-string` history wiring; two cosmetics
(odd-split row allocation, empty-file EOL mnemonic); the scenario-09
undo-to-saved fix. All well-scoped.

## Caveats that determine whether the outcome sticks

1. **Make the harness assert.** Machine-checked comparisons with a
   per-checkpoint expected-divergence baseline, nonzero exit on
   anything else, and a CI job with a pinned `emacs-nox`. Until then,
   every new scenario adds to a manual re-verification burden that
   grows linearly and will eventually be skipped. *(Done — see below.)*
2. **Pin/record the Emacs version.** The ground truth itself drifts
   across Emacs releases (the M-y rebinding in 28 is documented proof).
   A version check in `targets.py` is cheap insurance.
3. **Schedule the structural items deliberately** rather than letting
   scenarios force them ad hoc: undo save-point tracking first (clears
   a visible diff), then inactive-mark/mark-ring if the harness ever
   gains attribute-aware snapshots — also the only way to verify region
   rendering, currently a blind spot.

## Hardening work (started from this review)

- [x] Harness asserts: per-checkpoint field comparison
  (body/modeline/echo_area/cursor) against an `EXPECTED_DIVERGENCES`
  baseline declared in each scenario module; unexpected divergence →
  exit 1; stale expectation (documented diff that no longer occurs) →
  warning. See `parity/compare.py` and the updated `parity/run.py`,
  plus unit tests in `parity/tests/test_compare.py`.
- [x] Baselines validated empirically: a full 20-scenario run on GNU
  Emacs 29.3 reproduced *exactly* the 9 documented divergences and
  nothing else — the handover's "69 pixel-perfect / 9 explained" claim
  is confirmed, and the suite now exits 0 only in that state.
- [x] Emacs version recorded per run (`Ground truth: GNU Emacs NN.N`
  header) with a `NEON_PARITY_EMACS` override in `parity/targets.py`.
- [x] CI job running the parity scenarios (`ci.yml` job "Editor Parity
  (Emacs)"): pinned `ubuntu-24.04` runner (distro emacs-nox = 29.3, the
  version the baselines were validated against), runs the verdict unit
  tests then the full scenario suite on every push/PR to master.
- [ ] Undo save-point tracking (clears scenario 09 residual).
- [ ] Inactive mark / mark ring — needs attribute-aware snapshots to be
  harness-verifiable; schedule alongside any region-rendering work.
