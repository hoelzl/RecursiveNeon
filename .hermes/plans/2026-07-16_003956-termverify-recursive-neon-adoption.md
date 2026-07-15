# TermVerify / RecursiveNeon Example Adoption Plan

> **For Hermes:** Treat each phase below as a separately reviewable workstream. Do not begin adapter or extraction work until the corresponding TermVerify readiness gate is open.

**Goal:** Make RecursiveNeon's editor and terminal paths ready to become high-value TermVerify examples quickly, without moving or deleting RecursiveNeon code and without prematurely coupling either repository to an unstable TermVerify API.

**Architecture:** Use a two-track adoption. First, TermVerify will verify the living RecursiveNeon application through an external consumer integration. Second, after the TermVerify adapter and runner contracts stabilize, TermVerify will contain a frozen, provenance-tracked fixture derived by copying a deliberately reduced RecursiveNeon editor/TUI slice. The initial example will exercise the synchronous direct `TuiApp` seam; PTY and differential GNU Emacs coverage will follow. The browser/WebSocket terminal remains a later transport example.

**Repositories reviewed:**

- RecursiveNeon: `c0e91467e955b966b6d66d9a8cda1b9bbf6e2375`
- TermVerify: `2a98a4c1472aed7da906fb66d7197c1d17f9a847`

**Licensing:** Both repositories are Apache-2.0. Any copied source must retain notices, identify modified files, and be accompanied by source-path and revision provenance.

---

## 1. Recommended decision

Do **not** extract code now and do **not** make RecursiveNeon depend on TermVerify yet.

Prepare for a future **copy-and-adapt snapshot**, not a move, submodule, subtree, or runtime dependency on a sibling checkout:

1. RecursiveNeon remains the living game and original source.
2. TermVerify first proves framework-neutral adapter, runner, observation, and comparator contracts using fake applications.
3. A small RecursiveNeon compatibility seam is then added without changing game behavior.
4. TermVerify initially verifies the real RecursiveNeon checkout as a downstream integration.
5. Only after that succeeds is a reduced, frozen fixture copied into TermVerify with explicit provenance.
6. The existing `parity/` harness remains authoritative for RecursiveNeon until a separate, later migration is approved. Replacing it is not part of this plan.

This order avoids designing TermVerify around one application while preserving a fast path to a realistic example.

The adoption ladder should be: **direct scratch editor → direct in-process shell with a synthetic service container → PTY editor → PTY full shell → WebSocket/browser terminal**. The direct shell is not a prerequisite for freezing the editor fixture, but it should precede PTY shell work because it separates shell semantics from transport failures.

---

## 2. Extraction-focused code review

### High-priority findings

#### H1. Existing PTY readiness failures are not fail-closed

- `parity/targets.py:99-104` calls `Driver.wait_for(...)` for Emacs but ignores its Boolean result.
- `parity/targets.py:167-168` and `:178-182` also continue when the shell/editor readiness marker is absent.
- `parity/harness.py:143-184` returns only `bool`; timeout context is not preserved as structured evidence.

A failed launch can therefore be reported later as a visual divergence instead of an adapter-start/readiness failure. TermVerify must not reuse this behavior. Its future PTY target must turn readiness timeout, premature process exit, and incomplete initial paint into explicit failure records.

#### H2. Existing PTY teardown does not satisfy TermVerify's accepted lifecycle boundary

- `parity/harness.py:209-216` force-closes the child and suppresses every exception.
- It does not expose process exit, drain remaining output, distinguish graceful stop from forced termination, or report teardown failure.
- The accepted TermVerify boundary requires independent input/output draining, process-tree teardown, output draining before close, resize, and exit evidence (`termverify/docs/agent/design/phase-1-protocol-and-windows-boundary.md:23-31`).

Treat RecursiveNeon's `Driver` as a source of lessons and scenario behavior, not as TermVerify's production PTY adapter.

#### H3. The full runtime cannot truthfully enforce TermVerify's deterministic constraints yet

- `backend/src/recursive_neon/shell/tui/runner.py:105-145` and `:227-263` use ambient `time.monotonic()` for ticks.
- `backend/src/recursive_neon/terminal.py:275`, `:297`, and `:342-348` use ambient wall-time scheduling and UUID session IDs.
- `run_tui_app()` catches resize/tick/child exceptions, logs them, and often continues (`runner.py:123-143`, `:179-183`, `:239-260`); it always returns `0` (`:197`).

The initial example must therefore use the untimed editor subset through a direct adapter. A complete shell/WebSocket session must report unsupported for constraints it cannot enforce until explicit clock, identity, sandbox, and failure ports exist.

#### H4. A naive editor copy has a much larger dependency closure than it appears

`EditorView` plus `build_default_keymap()` is a strong direct seam, but `build_default_keymap()` imports shell mode, dired, game bridge, and app hosting for registration (`backend/src/recursive_neon/editor/default_commands.py:1694-1707`). `Editor` also contains injected game, NPC, shell, dired, and app-host state (`editor/editor.py:200-243`, `:1123-1168`). A static import-closure probe from the editor/TUI roots reached 56 RecursiveNeon modules, including shell programs, services, and game models.

Do not copy `backend/src/recursive_neon/editor/` wholesale. First define a core fixture profile that excludes game bridge, dired, shell mode, hosted apps, NPC events, and real filesystem tutorial loading unless a selected scenario needs them.

#### H5. There is no deterministic asynchronous quiescence boundary

- `EditorView.on_key()` dispatches and renders synchronously (`backend/src/recursive_neon/editor/view.py:93-121`).
- `EditorView.on_after_key()` separately drains queued callbacks and yields only once (`:159-196`).
- Shell mode can create background tasks that outlive that yield (`editor/shell_mode.py:355-376`), while the queues and task list are private mutable editor state (`editor/editor.py:204-215`).

A generic direct adapter cannot infer when all causally related work has reached a stable observation point. The core scratch-editor tranche avoids async features, but a later direct shell/editor fixture needs a public `step_key()`/`drain_async_work()`-style seam with reviewed quiescence semantics. A single `asyncio.sleep(0)` is not evidence of quiescence.

### Medium-priority findings

#### M1. The direct adapter seam is good but the observation contract is private and test-specific

- `TuiApp` already models start, key, resize, tick, and complete-frame return values (`shell/tui/__init__.py:128-167`).
- `EditorHarness` proves direct driving is practical (`backend/tests/unit/editor/harness.py:33-118`).
- However, tests use private rendering/state (`EditorHarness._screen`, `EditorView._render`, editor/window internals), and there is no public canonical editor observation.

Add one read-only fixture observation exporter after TermVerify's observation types stabilize. It should project semantic state rather than serialize the entire mutable object graph.

#### M2. Screen evidence needs normalization before it fits TermVerify

- `ScreenBuffer.lines` can contain embedded ANSI SGR (`shell/tui/__init__.py:43-57`).
- `ScreenBuffer.to_message()` omits dimensions (`:106-113`).
- RecursiveNeon uses `(cursor_row, cursor_col)` while the parity `Snapshot` uses `(x, y)` and TermVerify uses `{column, row}` (`parity/harness.py:26-40`; TermVerify protocol `ui.cursor`).

The adapter must define one explicit coordinate conversion and separate normalized text/frame evidence from style spans. It must not compare raw ANSI as the primary oracle.

#### M3. Differential baselines are too coarse for a generic verifier

`parity/compare.py:85-108` compares whole `body`, `modeline`, `echo_area`, `cursor`, and optional `highlights` fields. `EXPECTED_DIVERGENCES` permits any difference in an approved field. A changed body can therefore remain allowed even if its reason differs from the reviewed divergence.

Port scenario intent, not this baseline shape. TermVerify should use field-specific normalizers and predicates—for example path elision, command-set normalization, or region-specific assertions—plus digest-bound reviewed snapshots where exact comparison is appropriate.

#### M4. Scenario fixture text I/O inherits ambient host behavior

`parity/fixtures.py:42-46`, `:73-83`, and `:162-165` use `Path.write_text()` / `read_text()` without explicit encoding or newline policy. For durable replay fixtures, use UTF-8 and explicit LF semantics, or avoid host text I/O in the direct adapter.

#### M5. Rendering has useful property-test targets

- `ScreenBuffer.set_region()` and centering use Python character count rather than terminal display-cell width (`shell/tui/__init__.py:71-104`). Wide and combining characters are not modeled.
- `EditorView` syntax caching keys by `(hash(line), mode_name)` rather than line content (`editor/view.py:66-69`, `:385-390`), making collision correctness implicit.

These are excellent future TermVerify property/metamorphic examples, but they should not expand the first extraction slice.

#### M6. Process-global registries can leak state across replay cases

Commands, modes, and variables are registered in mutable globals (`editor/commands.py:33-58`, `editor/modes/__init__.py:74-107`, and `editor/variables.py:54-73`), and executable user configuration can redefine them. Multiple direct cases in one Python process therefore need explicit isolation.

The first fixture should disable user config and construct from a known command set. Before parallel/property execution, add injected registries or a tested snapshot/reset mechanism; do not silently reset production globals from a TermVerify adapter.

#### M7. Current safe evidence persistence is not yet suitable for useful editor baselines

TermVerify's evidence writer deliberately redacts observation state and frame content. That is safe, but it means a persisted transcript may not contain the editor behavior needed for replay comparison. Keep early tracer evidence in memory and do not publish a supported RecursiveNeon transcript or baseline until G4 defines a governed content-preserving mode. Publishing the first supported external artifact would also freeze TermVerify's inception-v1 compatibility policy.

### Strengths to preserve

1. `TuiApp` is already close to a deterministic state-machine boundary.
2. Complete-frame rendering after each key makes direct observation simple.
3. `EditorHarness` gives a proven in-process driver pattern.
4. The 32 parity scenarios form a mature behavior inventory and differential-oracle corpus.
5. `Driver.wait_for()` correctly recognizes that readiness conditions are better than silence windows, even though its current callers need fail-closed handling.
6. The parity comparator detects stale approved divergences, an important baseline-governance concept.
7. RecursiveNeon's virtual filesystem is a safer future filesystem fixture than exposing host paths.

---

## 3. Target example architecture

```text
TermVerify runner
  |
  +-- DirectNeonEditorAdapter
  |     +-- CoreEditorFixture
  |     |     +-- Editor
  |     |     +-- EditorView
  |     |     +-- core keymap/commands
  |     |     +-- ScreenBuffer
  |     +-- NeonEditorNormalizer
  |           +-- semantic state projection
  |           +-- UI regions/cursor/mode
  |           +-- normalized text frame
  |
  +-- PtyNeonEditorAdapter          (later)
  |     +-- fixture executable
  |     +-- TermVerify PTY transport
  |     +-- VT normalizer
  |
  +-- GNU Emacs reference adapter   (optional differential suite)
        +-- pinned version metadata
        +-- scenario-specific normalizers
```

### Initial semantic observation

Keep the first state schema intentionally small and versioned. Suggested fields:

- current buffer name;
- full current-buffer text;
- point `{line, column}`;
- mark `{line, column, active}` or `null`;
- modified and read-only flags;
- active major/minor mode names;
- minibuffer prompt/text/cursor or `null`;
- message/echo text;
- running flag;
- ordered buffer names;
- active window and visible range.

Suggested UI regions:

- `editor.body`;
- one region per window body/modeline when split-window scenarios are introduced;
- `editor.modeline` for the initial single-window slice;
- `editor.echo`;
- focus set to the active body or minibuffer/echo region;
- cursor expressed only as `{column, row, visible}`.

Do not expose Python object IDs, private cache contents, raw callbacks, host paths, UUIDs, timestamps, or full service state.

---

## 4. Readiness gates

| Gate | TermVerify capability required | RecursiveNeon work allowed after gate |
| --- | --- | --- |
| G0 — current | Transcript hardening only; public adapter/runtime gate remains closed | Documentation, review, scenario inventory only; no dependency or copied code |
| G1 — adapter contract | Immutable run config; enforced/unsupported negotiation; direct adapter protocol; explicit key/resize/clock/stop inputs | Prototype a tiny external adapter against `EditorHarness` without committing a dependency |
| G2 — runner + causality | Runner emits valid transcripts; input/observation correlation; readiness/quiescence semantics | Add a living-checkout integration in an isolated branch/worktree |
| G3 — observation/oracles | Versioned normalizer/state-schema identity; semantic and snapshot comparators; readable diffs | Commit the direct RecursiveNeon integration and select the extraction scenario tranche |
| G4 — evidence governance | Safe persistence and reviewed baseline flow usable by examples | Commit derived fixtures or baselines to TermVerify |
| G5 — production PTY | Proven create/drain/resize/stop/exit lifecycle on the supported host; VT normalization; truthful sandbox/network capability reporting | Add the PTY editor example; do not reuse `parity.Driver` as the transport |
| G6 — differential orchestration | Multiple subjects/reference targets, scenario normalizers, approved divergence predicates | Port selected GNU Emacs differential scenarios |
| G7 — browser transport | A terminal slice demonstrates a genuine shared browser abstraction | Consider RecursiveNeon's WebSocket/xterm.js terminal; not before |

The first useful example ships at **G3** as a direct editor fixture. PTY and GNU Emacs differential coverage are incremental, not prerequisites for demonstrating value.

---

## 5. Work plan

### Phase A — Prepare metadata now (no runtime coupling)

**Objective:** Preserve decisions and make the future extraction mechanical.

**Files:**

- Keep this plan in RecursiveNeon: `.hermes/plans/2026-07-16_003956-termverify-recursive-neon-adoption.md`
- Later update in TermVerify: `docs/agent/design/recursive-neon-reuse-assessment.md`

**Actions:**

1. Record the two-track decision: living integration first, frozen fixture second.
2. Record the initial scope as editor direct adapter, not WebSocket/browser terminal.
3. Record the source revision, candidate paths, excluded features, and Apache-2.0 obligations.
4. Create a scenario inventory table mapping selected RecursiveNeon parity scenarios to TermVerify input, semantic assertions, UI assertions, and required capabilities.
5. Do not introduce a TermVerify dependency or copy source while G0 is active.

**Validation:** Both repositories remain clean; documentation contains no claim that adapter/runtime support exists.

### Phase B — Stabilize TermVerify prerequisites

**Objective:** Open G1-G4 through the existing TermVerify readiness initiative.

**Likely TermVerify areas:**

- `src/termverify/` adapter/run/observation modules, only after approved contracts;
- `tests/` fake-adapter contract tests;
- `docs/knowledge/architecture.md` and `protocol.md` only through explicit compatibility gates;
- `docs/agent/handovers/phase-1-readiness-hardening-handover.md` for progress boundaries.

**Actions:**

1. Finish transcript/runtime/schema/fixture hardening and resource limits.
2. Approve normalized key and terminal-capability vocabularies.
3. Define readiness, quiescence, input-observation causality, and asynchronous drain behavior.
4. Implement immutable run configuration and a fake/direct adapter through strict TDD.
5. Implement runner, observation normalization, semantic comparator, and readable diff artifacts.
6. Keep PTY feasibility separate from production PTY claims.

**Validation:** TermVerify's full locked quality gates pass and each public contract has independent human-readable review.

### Phase C — Add a small RecursiveNeon compatibility seam

**Objective:** Make the editor consumable without pulling in the game and shell graph.

**Likely RecursiveNeon files:**

- Modify: `backend/src/recursive_neon/editor/default_commands.py`
- Modify or add a sibling factory near: `backend/src/recursive_neon/editor/view.py:964-984`
- Add tests under: `backend/tests/unit/editor/`

**Actions:**

1. Split keymap construction into a core editor profile and optional integrations while preserving `build_default_keymap()` behavior byte-for-byte.
2. Add a public factory that creates the core editor fixture with explicit content, name, dimensions, and optional in-memory file port.
3. Add a read-only semantic observation projection only after TermVerify's state-schema contract is stable; keep it framework-neutral so RecursiveNeon does not need to import TermVerify.
4. Add an explicit no-ticks/core-profile invariant and, if G1 requires them even for unused ambient facilities, framework-neutral seed/manual-clock ports. Do not invent no-op capability semantics inside the RecursiveNeon integration.
5. Keep game bridge, NPC events, shell mode, dired, hosted apps, WebSocket, and host filesystem out of the initial profile.
6. Disable executable user config in the fixture profile and prove repeated construction does not leak command/mode/variable registry mutations. Introduce injected registries or an explicit tested reset only if isolation tests show it is needed.
7. Before adding async shell/hosted-app scenarios, expose a deterministic async drain/quiescence operation and an optional framework-neutral command/event observer.
8. If dired enters a later tranche, inject its current-time provider instead of allowing `datetime.now()` in verified observations.

**Validation:**

```bash
.venv/Scripts/python -m pytest backend/tests/unit/editor --no-cov -q
.venv/Scripts/ruff check backend/src/recursive_neon/editor backend/tests/unit/editor
```

Then run the normal RecursiveNeon backend and parity gates on a supported Unix/WSL host. Existing `build_default_keymap()` and parity scenarios must remain unchanged in behavior.

### Phase D — Verify the living RecursiveNeon checkout from TermVerify

**Objective:** Prove the adapter against real application code before creating a forked fixture.

**Location:** Use a dedicated external sibling worktree/branch in TermVerify and an explicit path or editable dependency only for development. Do not make repository tests depend on an ambient sibling checkout.

**Actions:**

1. Implement `DirectNeonEditorAdapter` outside RecursiveNeon, composing its public core factory.
2. Map TermVerify key inputs to RecursiveNeon's canonical key strings in one adapter-owned table.
3. Negotiate constraints honestly: enforce only those supplied through explicit ports or covered by G1's reviewed non-use attestation semantics; return unsupported before input for the rest. If this prevents the tracer from dispatching input, add the missing framework-neutral port rather than a RecursiveNeon-specific exception in TermVerify.
4. Normalize editor state and `ScreenBuffer` into the agreed state/UI/frame schema.
5. Run three tracer scenarios:
   - startup/open known text;
   - insert, move, undo, and observe semantic state;
   - resize and observe cursor/frame geometry.
6. Add one deliberate failure to prove readable semantic and frame diffs.
7. Validate replay identity includes exact RecursiveNeon build, fixture, adapter, normalizer, and state-schema versions.

**Exit criterion:** The living integration passes with no source copy and exposes no missing generic adapter capability. If a generic gap appears, fix TermVerify's contract before extraction rather than embedding a workaround in the fixture.

### Phase D2 — Add a direct in-process shell fixture

**Objective:** Verify shell semantics independently of PTY, WebSocket, and production persistence.

**Actions:**

1. Construct a deterministic synthetic `ServiceContainer` and virtual filesystem; do not call production shell startup.
2. Supply fixed seed/manual time and deterministic username/hostname as fixture state, never replay identity.
3. Prove the direct fixture uses no host filesystem and no network before attesting those constraints.
4. Drive a small command tranche through the in-process shell surface and observe structured shell/VFS state.
5. Exclude editor shell-mode and nested TUI apps until the async quiescence seam is proven.

**Exit criterion:** Command behavior is reproducible without a terminal transport. This phase is a prerequisite for the later PTY **full-shell** example, but not for freezing the reduced editor fixture in Phase E.

### Phase E — Create the frozen TermVerify fixture by copying, never moving

**Objective:** Make a self-contained distributable example without altering RecursiveNeon.

**Proposed TermVerify layout:**

```text
examples/recursive-neon-editor/
  pyproject.toml
  README.md
  LICENSE
  NOTICE
  PROVENANCE.md
  upstream-manifest.json
  src/termverify_example_neon/
    ...reduced editor/TUI fixture...
    __main__.py
    adapter.py
    normalizer.py
  tests/
    test_direct_scenarios.py
    test_provenance_manifest.py
```

Final package naming is a human-review gate; do not preserve `recursive_neon` imports if doing so falsely implies this is the full application.

**Extraction rules:**

1. Copy an allowlist from a pinned RecursiveNeon commit; never delete or relocate upstream files.
2. Generate `upstream-manifest.json` with source revision, source path, destination path, SHA-256, and modification status for every copied file.
3. Retain Apache headers/notices and mark modified files prominently.
4. Copy only the tests/scenarios required by the selected feature tranche; record test provenance too.
5. Remove game/shell integrations only in the derived fixture, not in RecursiveNeon.
6. Use a standalone example project so RecursiveNeon's dependencies do not become TermVerify core dependencies.
7. Treat the copy as a deliberate snapshot/fork. Do not promise automatic synchronization.
8. Provide a verification-only extraction tool that can compare a local upstream checkout at the pinned revision to the manifest; normal package builds must not require that checkout.

**Why not submodule/subtree/runtime Git dependency:** Those approaches make examples network- or layout-dependent, blur replay identity, complicate source distributions, and couple TermVerify releases to the living game. A manifest-tracked snapshot is deterministic and reviewable.

### Phase F — Add PTY and GNU Emacs layers

**Objective:** Demonstrate that the same semantic fixture can be verified both directly and through a real terminal.

**Actions:**

1. Add a minimal fixture executable that uses the core editor profile and has deterministic startup/exit semantics.
2. Drive it exclusively through TermVerify's PTY adapter; do not transplant `parity.Driver` lifecycle code.
3. Make readiness an explicit condition with timeout and process-exit diagnostics.
4. Capture structured state from the direct path and normalized VT frame/process evidence from PTY.
5. Port a small GNU Emacs differential tranche after generic multi-target orchestration exists:
   - scenario 01 startup;
   - scenario 02 end-of-buffer;
   - scenario 06 kill/yank or scenario 09 undo/redo;
   - one resize/window-layout scenario.
6. Replace whole-field divergence allowances with named normalizers/predicates tied to reviewed reasons.
7. Record exact GNU Emacs version/build as reference identity; keep the differential suite optional where Emacs is unavailable.

**Validation:** Direct and PTY paths agree on semantic outcomes; PTY adds rendering/input-decoding/process evidence. Differential tests fail on unexpected divergence and identify stale approved exceptions.

### Phase G — Integrate TermVerify into RecursiveNeon later

**Objective:** Replace `parity/` only after TermVerify has proven equivalent or stronger coverage.

This is intentionally outside current scope. A future migration plan must run the existing parity harness and TermVerify side by side, compare all 32 scenarios, preserve documented divergences, and remove the old harness only after explicit approval. No part of Phases A-F requires this migration.

---

## 6. Initial scenario tranche

| Scenario | Direct semantic oracle | UI/frame oracle | PTY-specific value | Defer |
| --- | --- | --- | --- | --- |
| Startup with 3-line file | text, point, mode, modified=false | body/modeline/echo/cursor | startup readiness and initial paint | host path semantics |
| End-of-buffer | unchanged text, point at max, message | cursor and echo | control-key decoding | none |
| Insert/move/undo | text, point, modified/undo outcome | cursor/modeline/message | ordered key delivery | exact Emacs redo-point deviation initially |
| Resize | stable state, active visible range | dimensions, regions, cursor bounds | PTY resize propagation | split windows until core slice is stable |
| Exit | running=false, final state | optional final frame | stop/exit/drain evidence | process-tree stress cases until PTY contract is ready |

Dired, shell mode, hosted TUI apps, NPC events, browser xterm.js, and persistence should be separate later examples because each adds a distinct capability boundary.

---

## 7. Risks and controls

| Risk | Control |
| --- | --- |
| Premature TermVerify API coupling | G1-G4 gates; prototype externally before either repo imports the other |
| RecursiveNeon regression | Copy, never move; preserve full default profile; run 1,585 editor tests plus full parity on supported host |
| Fixture silently diverges from upstream | Pinned revision + path/hash manifest + explicit snapshot/fork policy |
| Example drags game dependencies into TermVerify | Core fixture profile and standalone example project |
| False deterministic claims | Enforced-or-unsupported negotiation; direct untimed slice first |
| Raw ANSI becomes the oracle | Semantic state first, normalized UI second, raw bytes diagnostic only |
| Coarse approved divergences hide regressions | Reason-specific normalizers/predicates and digest-bound readable diffs |
| PTY portability blocks the first example | Ship direct example at G3; add POSIX/ConPTY transports independently |
| Licensing/provenance loss | `LICENSE`, `NOTICE`, `PROVENANCE.md`, and executable manifest checks |
| Browser terminal expands scope | Defer until G7 and a terminal slice proves the abstraction is needed |

---

## 8. Verification performed for this assessment

- TermVerify current suite: `206 passed` using `uv --no-config run pytest -q`.
- RecursiveNeon editor suite: `1,585 passed` using `uv run --project backend pytest backend/tests/unit/editor --no-cov -q` on Windows/Python 3.13.2.
- RecursiveNeon parity verdict unit tests were not runnable in the current Windows venv because `pexpect` and `pyte` are intentionally extra Unix/WSL harness dependencies. No full GNU Emacs PTY claim is made by this review.
- Both repositories were clean before assessment. A transient `backend/uv.lock` timestamp change caused by `uv run` was inspected and restored; no source changes were made.

---

## 9. Next decision point

The next action should remain in TermVerify: continue the Phase 1 readiness hardening until G1 is formally open. At that point, create one focused design/implementation issue for the direct core-editor tracer, using this plan and `termverify/docs/agent/design/recursive-neon-reuse-assessment.md` as inputs. Do not open an extraction PR before the living integration passes at G3.
