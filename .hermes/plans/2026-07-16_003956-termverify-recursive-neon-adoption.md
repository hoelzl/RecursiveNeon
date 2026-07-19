# TermVerify / RecursiveNeon Example Adoption Plan

> **For Hermes:** Treat each phase below as a separately reviewable workstream. Do not begin adapter or extraction work until the corresponding TermVerify readiness gate is open.

**Goal:** Make RecursiveNeon's editor and terminal paths ready to become high-value TermVerify examples quickly, without moving or deleting RecursiveNeon code and without prematurely coupling either repository to an unstable TermVerify API.

**Architecture:** Use a two-track RecursiveNeon adoption, with native-host applications kept as a separate TermVerify example family. First, TermVerify verifies the living RecursiveNeon application through an external consumer integration. Second, after the verification core stabilizes, TermVerify may contain a frozen, provenance-tracked fixture derived by copying a deliberately reduced editor/TUI slice. The initial example exercises the synchronous direct `TuiApp` seam over RecursiveNeon's in-memory environment; ConPTY and differential GNU Emacs coverage follow. A native-host editor or command suite is not a mode of RecursiveNeon and must not weaken its virtual-filesystem boundary.

**Repositories reviewed:**

- Original assessment: RecursiveNeon `c0e91467e955b966b6d66d9a8cda1b9bbf6e2375`; TermVerify `2a98a4c1472aed7da906fb66d7197c1d17f9a847`.
- Reassessment updated on 2026-07-19: RecursiveNeon `bc88dc368adeb225281e37559a911b129848eb7e`; TermVerify `2c514be3805a2a24892d9f57bfe1ea12d74c70d9`.
- Phase 2 activation update on 2026-07-19: TermVerify `ae370b0ac3b89d70e22d32ce8b9847f8a2289192` (the `2c514be` reassessment line above remains authoritative for the pre-Phase-2 baseline). RecursiveNeon master is now `5cd7247` after PR #72 landed.

**Licensing:** Both repositories are Apache-2.0. Any copied source must retain notices, identify modified files, and be accompanied by source-path and revision provenance.

### 2026-07-19 status change

> **Note:** This entry is the pre-Phase-2 baseline as of TermVerify `2c514be`. It is superseded for current state by the **"2026-07-19 status change (Phase 2 activation)"** entry below, which records slices 1 and 2 shipping at `ae370b0`. The bullets here are retained unchanged for provenance.

TermVerify has crossed several gates that were closed in the original assessment:

- `Adapter`, `ConstraintPorts`, `DirectApplication`, immutable run/input/observation values, constructive enforcement receipts, and `DirectAdapter` now exist.
- Direct readiness, single-flight causality, application-reported quiescence, stop/drain behavior, and semantic `termverify.key/v1` inputs are implemented.
- The Windows production path now includes a ConPTY binding and adapter, explicit readiness-marker epochs, a fail-closed VT normalizer, cooperation-tier constraint delivery, resize/process evidence, and terminal key-byte dispatch through `termverify.key-encoding/v1`. PR #144 completed the real-child Windows evidence: a cooperative raw-mode subject observes the exact registry bytes for one representative of every encodable family class, retained output replays to the frames, and an unencodable chord fails closed with OS-observed teardown.
- A separate external subject, GlyphWright, has completed a direct-adapter spike and produced a deterministic valid transcript; its findings are tracked in [TermVerify issue #114](https://github.com/hoelzl/termverify/issues/114).

The verification core is still missing: there is no generic run/scenario orchestrator or `TranscriptRecorder`, transcript comparator, subject replay, report, differential multi-target runner, or governed behavior-baseline workflow. Adapter-author contracts are documented at module paths rather than exposed as a curated top-level external-author surface. Phase 2 remains inactive. These are now the blockers to a supported example; the direct adapter contract itself is no longer the blocker.

The latest commit strengthens but does not reverse the recommendation. Generic Windows key delivery is no longer an evidence gap, so an experimental RecursiveNeon ConPTY harness no longer waits on TermVerify key work. It still waits on subject-specific work: the core profile, truthful constraint cooperation, readiness markers after every completed epoch, RecursiveNeon's raw-input compatibility, and proof that its output stays inside the claimed VT subset. A supported example still waits on the verification core above.

### 2026-07-19 status change (Phase 2 activation)

TermVerify is now at `ae370b0ac3b89d70e22d32ce8b9847f8a2289192` on `main`. Phase 2 is no longer inactive: PR #145 proposed and PR #147 recorded owner acceptance (issue #146) of a narrow **Phase 2 verification-core boundary** — a pure consumer of the frozen `termverify.transcript/v1` protocol, implemented as three sequential slices, each gated through its own issue/sibling worktree/TDD/full validation/adversarial review. No transcript semantics change, no new dependency, no release claim; behavioral baselines and golden-master governance remain outside the boundary.

Two of the three slices have shipped:

- **Slice 1 — recorder + run orchestrator (SHIPPED, PR #150, merged 2026-07-19 14:01Z, closes #148).** `termverify.recorder.TranscriptRecorder` assembles immutable adapter results into `termverify.transcript/v1` records in occurrence order and fails closed with structured errors on out-of-order/mistimed/foreign contributions. The `run_scripted` orchestrator drives one adapter through a scripted input sequence and returns validated transcript bytes plus the terminal outcome. Output goes only through the existing strict serializer. This removes the "external adapters must hand-assemble protocol records" blocker that forced GlyphWright to write its own recorder.
- **Slice 2 — exact comparator + deterministic report (SHIPPED, PR #152, merged 2026-07-19 14:38Z, closes #151).** `termverify.comparator.compare_transcripts(left, right)` validates both byte sequences with the strict codec's `parse_transcript` (invalid side raises structured `TranscriptInputError`, never a comparison result), then compares position-by-position by canonical semantic equality over the full record sequence, with exactly one disclosed identity exclusion: envelope `run_id`. It returns a `ComparisonVerdict` listing every divergent record (`RecordDivergence`) with exact differing members (`MemberDifference`: dotted path, canonical RFC 8785 renderings, `None` for absence) in deterministic sorted order. `render_report(verdict)` renders deterministic plain text. `termverify.comparator` is at 100% line+branch coverage. No normalizers/predicates/tolerances/per-scenario config — those remain caller-side, on purpose.
- **Slice 3 — caller-bound transcript replay (NOT YET).** This is the remaining TermVerify-side dependency before a supported direct example can claim end-to-end verify-record-and-replay.

The verification-core picture is therefore changed but not closed: the generic recorder/orchestrator and the exact comparator/readable report exist, but subject replay, a semantic/snapshot oracle policy, and a normalizer/state-schema registry are still absent. The recommendation is strengthened: a RecursiveNeon direct tracer can now consume a supported recorder and comparator instead of hand-rolling either, but it still cannot claim a supported example until slice 3 and the remaining G3 pieces land.

Concurrently, RecursiveNeon PR #72 (merged into master as `5cd7247`) shipped `feat(editor): CoreEditorSession for deterministic in-process driving` — the Phase C compatibility seam this plan calls for. Phase C is now substantially complete; see the §5 Phase C update below.

---

## 1. Recommended decision

Do **not** extract code now and do **not** make RecursiveNeon depend on TermVerify. Begin the living-checkout direct-tracer workstream now, through an adapter owned by the integration, while keeping it explicitly experimental until TermVerify supplies the verification core. Do not execute a successful direct run until the core profile proves that its constructive receipts are truthful: integrations and user configuration are absent, registries are isolated, and clock, network, and host-filesystem facilities are unreachable.

Prepare for a future **copy-and-adapt snapshot**, not a move, submodule, subtree, or runtime dependency on a sibling checkout:

1. RecursiveNeon remains the living game and original source.
2. The existing TermVerify direct contract is exercised against RecursiveNeon before either repository adopts a cross-repository runtime dependency.
3. A small framework-neutral RecursiveNeon compatibility seam is added without changing game behavior.
4. TermVerify verifies the real RecursiveNeon checkout as a downstream integration; temporary transcript assembly is no longer required as of Phase 2 slice 1 (PR #150, `TranscriptRecorder`/`run_scripted`), so the tracer consumes the supported recorder directly.
5. Only after that succeeds is a reduced, frozen fixture copied into TermVerify with explicit provenance.
6. The existing `parity/` harness remains authoritative for RecursiveNeon until a separate, later migration is approved. Replacing it is not part of this plan.

This order avoids designing TermVerify around one application while preserving a fast path to a realistic example.

The adoption ladder should be: **direct core editor → direct in-process shell with a synthetic service container → ConPTY editor harness → ConPTY full shell → optional POSIX PTY → WebSocket/browser terminal**. The direct shell is not a prerequisite for freezing the editor fixture, but it should precede terminal shell work because it separates shell semantics from transport failures.

The environment decision is explicit:

1. **RecursiveNeon remains the simulated environment.** Its editor, shell, and dired operate over the UUID-backed in-memory virtual filesystem. Adding host-file access to make the example look more conventional would violate a core security boundary and make the subject less deterministic.
2. **The example is still a real editor.** "Simulated environment" describes its I/O ports, not toy behavior: editing, windowing, minibuffer, rendering, and selected command semantics remain production RecursiveNeon code.
3. **A native-host editor or command-line suite should be a separate subject.** It can exercise sandbox-root delivery, real subprocess behavior, host path normalization, and command discovery without contaminating RecursiveNeon or the reduced fixture. Reuse the same scenario concepts and TermVerify contracts where useful, but do not force one application to cover incompatible trust boundaries.

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
  +-- TerminalNeonEditorAdapter     (later)
  |     +-- marker-emitting fixture executable
  |     +-- ConPTY transport (Windows)
  |     +-- optional POSIX PTY transport (future)
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

| Gate | Status on TermVerify `ae370b0` (post-Phase-2 activation) | RecursiveNeon work allowed after gate |
| --- | --- | --- |
| G0 — protocol hardening | Open. The strict transcript codec, lifecycle, resource limits, schema access, and safe evidence writer exist. | Documentation and scenario inventory are no longer the only permitted work. |
| G1 — adapter contract | Open. Immutable run configuration, enforced/unsupported negotiation, direct execution, semantic key/resize/clock/stop inputs, and observation values exist. | Add the small core-editor seam and prototype a living-checkout `DirectApplication`. |
| G2 — recording + causality | Open at the generic recorder/orchestrator (was Partial). Slice 1 shipped in PR #150: `termverify.recorder.TranscriptRecorder` and `run_scripted` produce validated `termverify.transcript/v1` bytes through the strict serializer, failing closed on out-of-order/mistimed/foreign contributions. Adapter-level readiness, single-flight causality, and quiescence remain. | An experimental direct tracer may now consume `TranscriptRecorder`/`run_scripted` directly instead of hand-assembling records. Still present it as experimental until G3 closes. |
| G3 — verification core | Partial (was Blocked). Slice 2 shipped in PR #152: `termverify.comparator.compare_transcripts` validates both sides via the strict codec, compares position-by-position by canonical semantic equality with one disclosed identity exclusion (`run_id`), returns a deterministic `ComparisonVerdict` of `RecordDivergence`/`MemberDifference`, and `render_report` produces deterministic plain text. Still missing: caller-bound transcript replay (Phase 2 slice 3), semantic/snapshot oracle policy, and a normalizer/state-schema registry. | A supported direct example still waits on slice 3 + the remaining G3 pieces. A RecursiveNeon tracer may exercise the comparator against its own recorded transcripts now, but must not claim a supported verify-record-and-replay loop until G3 is open. |
| G4 — behavior-evidence governance | Partial. Safe persistence exists but redacts useful editor state/frame content; no reviewed content-preserving baseline flow exists. | Commit a derived fixture after living integration, but do not publish useful baselines until this gate opens. |
| G5 — production terminal | Open at the generic Windows substrate, not yet for RecursiveNeon. ConPTY lifecycle, readiness-marker epochs, VT normalization, cooperation deliveries, resize/process evidence, and real-child key-byte delivery evidence exist. Key-support negotiation and input-mode tracking remain explicit non-claims. | Add a dedicated RecursiveNeon harness executable after it proves compatible raw-input mode, emits a marker after startup and every input/resize, stays inside the VT subset, and passes the real adapter. Never reuse `parity.Driver` as transport. |
| G6 — differential orchestration | Blocked. Multiple subjects/reference targets, scenario normalizers, approved divergence predicates, and comparison reports are absent. | Port selected GNU Emacs differential scenarios. |
| G7 — browser transport | Blocked and unproven as a shared abstraction. | Consider RecursiveNeon's WebSocket/xterm.js terminal only after direct and terminal examples establish a concrete need. |

An experimental living-checkout tracer can start at **G1/G2 now**, and as of the Phase 2 activation may consume `TranscriptRecorder`/`run_scripted` (slice 1, PR #150) and `compare_transcripts`/`render_report` (slice 2, PR #152) directly rather than hand-rolling either. The first supported example still ships at **G3** as a direct editor fixture, and now also waits on Phase 2 slice 3 (caller-bound replay). ConPTY and GNU Emacs differential coverage are incremental, not prerequisites for demonstrating value.

---

## 5. Work plan

### Phase A — Prepare metadata now (no runtime coupling)

**Objective:** Preserve decisions and make the future extraction mechanical.

**Files:**

- Keep this plan in RecursiveNeon: `.hermes/plans/2026-07-16_003956-termverify-recursive-neon-adoption.md`
- Keep the corresponding status and boundary summary in TermVerify: `docs/agent/design/recursive-neon-reuse-assessment.md`

**Actions:**

1. Record the two-track decision: living integration first, frozen fixture second.
2. Record the initial scope as editor direct adapter, not WebSocket/browser terminal.
3. Record the source revision, candidate paths, excluded features, and Apache-2.0 obligations.
4. Create a scenario inventory table mapping selected RecursiveNeon parity scenarios to TermVerify input, semantic assertions, UI assertions, and required capabilities.
5. Do not introduce a TermVerify dependency or copy source merely because G1 is open.

**Validation:** Documentation distinguishes shipped TermVerify substrate from missing verification-core and RecursiveNeon-integration work.

### Phase B — Stabilize TermVerify prerequisites

**Objective:** Build the missing verification core needed to turn the now-usable adapters into a supported example workflow.

**Status (2026-07-19, Phase 2 activation):** Phase 2 is active. The boundary accepted via issue #146 / PR #147 scopes the verification core as a pure consumer of the frozen `termverify.transcript/v1` protocol, delivered as three sequential slices. **Slice 1 (PR #150, closes #148) and slice 2 (PR #152, closes #151) have shipped** at TermVerify `ae370b0`. Slice 3 (caller-bound transcript replay) is the next TermVerify-side dependency and is not yet landed.

**Slices shipped:**

1. Slice 1 — `termverify.recorder.TranscriptRecorder` + `run_scripted` orchestrator (PR #150). Generic recording and minimal run orchestration now exist; external adapters no longer hand-assemble protocol records.
2. Slice 2 — `termverify.comparator.compare_transcripts` + `render_report` (PR #152). Exact transcript comparator with deterministic plain-text report, single disclosed identity exclusion (`run_id`), structured input errors, 100% line+branch coverage.

**Remaining TermVerify work in this phase:**

3. Slice 3 — caller-bound transcript replay (next TermVerify-side dependency; gates the supported verify-record-and-replay loop).
4. Semantic/snapshot oracle policy and a normalizer/state-schema registry (the comparator is intentionally exact-only; caller-side normalizers/predicates/tolerances remain out of the Phase 2 boundary by design).
5. Package and document the external adapter-author surface, compatibility intent, and a minimal example without flattening module ownership.
6. Define content-preserving evidence and reviewed baseline governance separately from the existing redacted safe-evidence path (G4).
7. Add differential multi-target orchestration before porting GNU Emacs scenarios (G6).
8. Treat the implemented ConPTY substrate as available but require subject-specific readiness, VT-subset, key-delivery, and constraint evidence before claiming a RecursiveNeon terminal example.

**Likely TermVerify areas:**

- `src/termverify/` adapter/run/observation modules, only after approved contracts;
- `tests/` fake-adapter contract tests;
- `docs/knowledge/architecture.md` and `protocol.md` only through explicit compatibility gates;
- `docs/agent/handovers/pre-release-boundary-hardening-handover.md` for current progress boundaries.

**Historical actions (pre-Phase-2 framing, retained for provenance):**

1. Add a generic scenario/run orchestrator and transcript recorder so external adapters do not hand-assemble protocol records. — **Done in slice 1 (PR #150).**
2. Implement transcript comparison and subject replay with semantic and frame policies plus readable diffs/reports. — **Comparison + readable report done in slice 2 (PR #152); subject replay, semantic/frame policies pending slice 3 + caller-side oracle policy.**
3. Package and document the external adapter-author surface, compatibility intent, and a minimal example without flattening module ownership.
4. Define content-preserving evidence and reviewed baseline governance separately from the existing redacted safe-evidence path.
5. Add differential multi-target orchestration before porting GNU Emacs scenarios.
6. Treat the implemented ConPTY substrate as available but require subject-specific readiness, VT-subset, key-delivery, and constraint evidence before claiming a RecursiveNeon terminal example.

**Validation:** TermVerify's full locked quality gates pass and each public contract has independent human-readable review. (Phase 2 slices 1 and 2 each passed TDD + full validation + adversarial review before merge.)

### Phase C — Add a small RecursiveNeon compatibility seam

**Objective:** Make the editor consumable without pulling in the game and shell graph.

**Status (2026-07-19):** Substantially complete. RecursiveNeon PR #72 (merged into master as `5cd7247`) shipped `feat(editor): CoreEditorSession for deterministic in-process driving`, which delivers the compatibility seam this phase calls for:

- `CoreEditorSession` — a production session wrapper around the real `Editor` + `EditorView` with fresh per-session command/mode/variable registries, so direct cases in one Python process no longer leak registry state (resolves the M6 isolation concern at the integration boundary).
- `core_commands.py` — a capability-free core-only keymap, separate from `build_default_keymap()`, so the core editor profile does not drag in shell mode, dired, game bridge, or app-host registration (the H4 closure concern).
- `editing_primitives.py` — shared editing primitives used by the session.
- `EditorObservationV1` + `EditorObservationV1Dict` — an immutable versioned semantic observation (`schema_version: Literal[1]`) with a TypedDict serialization form, framework-neutral (no TermVerify import). This is the read-only semantic observation projection action 3 below asks for; RecursiveNeon owns the schema and TermVerify consumes it.
- Complete `CoreEditorFrame`s, synchronous `start/send_key/resize/observe/stop/abort`, fail-closed quiescence, and `rows >= 3` geometry validation.
- Lazy optional editor/shell exports so importing the seam does not force the rest of the application graph.

Phase D (living-checkout `DirectNeonEditorAdapter`) can now compose `CoreEditorSession` directly. Remaining Phase C follow-ups that PR #72 does not claim to close: (a) the deterministic async drain/quiescence operation for shell-mode/hosted-app scenarios (action 7 — still needed before Phase D2 shell work), (b) dired current-time injection if dired enters a later tranche (action 8), and (c) any additional no-ticks/core-profile invariant assertions TermVerify's G1 contract winds up requiring.

**Likely RecursiveNeon files:**

- Modify: `backend/src/recursive_neon/editor/default_commands.py`
- Modify or add a sibling factory near: `backend/src/recursive_neon/editor/view.py:964-984`
- Add tests under: `backend/tests/unit/editor/`
- **Added by PR #72:** `backend/src/recursive_neon/editor/core_commands.py`, `backend/src/recursive_neon/editor/editing_primitives.py`, and the `CoreEditorSession` + `EditorObservationV1` modules (see PR #72 diff for exact paths).

**Actions:**

1. Split keymap construction into a core editor profile and optional integrations while preserving `build_default_keymap()` behavior byte-for-byte. — **Done in PR #72 via `core_commands.py`.**
2. Add a public factory that creates the core editor fixture with explicit content, name, dimensions, and optional in-memory file port. — **Done in PR #72 via `CoreEditorSession`.**
3. Add a read-only semantic observation projection only after TermVerify's state-schema contract is stable; keep it framework-neutral so RecursiveNeon does not need to import TermVerify. — **Done in PR #72 via `EditorObservationV1` / `EditorObservationV1Dict` (`schema_version: Literal[1]`).**
4. Add an explicit no-ticks/core-profile invariant and, if G1 requires them even for unused ambient facilities, framework-neutral seed/manual-clock ports. Do not invent no-op capability semantics inside the RecursiveNeon integration. — **Partially addressed by PR #72's capability-free core keymap and synchronous, fail-closed session surface; verify against the final G1 contract during Phase D.**
5. Keep game bridge, NPC events, shell mode, dired, hosted apps, WebSocket, and host filesystem out of the initial profile. — **Held by PR #72's lazy optional exports + core-only keymap.**
6. Disable executable user config in the fixture profile and prove repeated construction does not leak command/mode/variable registry mutations. Introduce injected registries or an explicit tested reset only if isolation tests show it is needed. — **Addressed by PR #72's fresh per-session registries; confirm with an explicit isolation test during Phase D if not already covered.**
7. Before adding async shell/hosted-app scenarios, expose a deterministic async drain/quiescence operation and an optional framework-neutral command/event observer. — **Still open; prerequisite for Phase D2.**
8. If dired enters a later tranche, inject its current-time provider instead of allowing `datetime.now()` in verified observations. — **Still open; only relevant if/when dired is added.**

**Validation:**

```bash
.venv/Scripts/python -m pytest backend/tests/unit/editor --no-cov -q
.venv/Scripts/ruff check backend/src/recursive_neon/editor backend/tests/unit/editor
```

Then run the normal RecursiveNeon backend and parity gates on a supported Unix/WSL host. Existing `build_default_keymap()` and parity scenarios must remain unchanged in behavior. (PR #72's validation is authoritative for the seam itself; Phase D must re-run these gates after the adapter composes the session.)

### Phase D — Verify the living RecursiveNeon checkout from TermVerify

**Objective:** Prove the adapter against real application code before creating a forked fixture.

**Location:** Use a dedicated external sibling worktree/branch in TermVerify and an explicit path or editable dependency only for development. Do not make repository tests depend on an ambient sibling checkout.

**Actions:**

1. Implement `DirectNeonEditorAdapter` outside RecursiveNeon, composing its public core factory — as of PR #72, compose `CoreEditorSession` directly (synchronous `start/send_key/resize/observe/stop/abort`, fresh per-session registries, `EditorObservationV1` semantic observation).
2. Map TermVerify key inputs to RecursiveNeon's canonical key strings in one adapter-owned table.
3. Negotiate constraints honestly: enforce only those supplied through explicit ports or covered by G1's reviewed non-use attestation semantics; return unsupported before input for the rest. If this prevents the tracer from dispatching input, add the missing framework-neutral port rather than a RecursiveNeon-specific exception in TermVerify.
4. Normalize editor state and `ScreenBuffer` into the agreed state/UI/frame schema. `EditorObservationV1` already supplies the semantic side; the adapter still owns `ScreenBuffer`-to-frame normalization.
5. Run three tracer scenarios:
   - startup/open known text;
   - insert, move, undo, and observe semantic state;
   - resize and observe cursor/frame geometry.
6. Add one deliberate failure now that the generic comparator exists (PR #152, `termverify.comparator.compare_transcripts` + `render_report`), to prove readable semantic and frame diffs via `ComparisonVerdict` / `RecordDivergence` / `MemberDifference`. The tracer must consume the supported comparator and must not implement a tracer-local one.
7. Validate replay identity includes exact RecursiveNeon build, fixture, adapter, normalizer, and state-schema versions. Note: replay itself still waits on Phase 2 slice 3; until then the adapter can record + compare but not yet drive a supported replay loop.

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

### Phase F — Add terminal-transport and GNU Emacs layers

**Objective:** Demonstrate that the same semantic fixture can be verified both directly and through a real terminal.

**Actions:**

1. Add a minimal fixture executable that uses the core editor profile and has deterministic startup/exit semantics.
2. On Windows, drive it exclusively through `ConptyAdapter`; do not transplant `parity.Driver` lifecycle code. Add a POSIX path only after TermVerify owns one.
3. Emit TermVerify's readiness marker after startup and every completed key/text/resize epoch. The abort deadline is failure policy, never readiness evidence.
4. Capture structured state from the direct path and normalized VT frame/process evidence from the terminal path. Do not imply that the terminal path exposes RecursiveNeon's structured editor state unless a separately designed telemetry channel provides it.
5. Port a small GNU Emacs differential tranche after generic multi-target orchestration exists:
   - scenario 01 startup;
   - scenario 02 end-of-buffer;
   - scenario 06 kill/yank or scenario 09 undo/redo;
   - one resize/window-layout scenario.
6. Replace whole-field divergence allowances with named normalizers/predicates tied to reviewed reasons.
7. Record exact GNU Emacs version/build as reference identity; keep the differential suite optional where Emacs is unavailable.

**Validation:** The direct path proves semantic editor outcomes. The terminal path independently proves frame/cursor, input decoding, resize, and process behavior. Cross-mode semantic agreement is claimed only after a structured telemetry channel and generic cross-mode comparator exist; until then, compare only shared frame/cursor evidence. Differential tests fail on unexpected divergence and identify stale approved exceptions.

### Phase G — Integrate TermVerify into RecursiveNeon later

**Objective:** Replace `parity/` only after TermVerify has proven equivalent or stronger coverage.

This is intentionally outside current scope. A future migration plan must run the existing parity harness and TermVerify side by side, compare all 32 scenarios, preserve documented divergences, and remove the old harness only after explicit approval. No part of Phases A-F requires this migration.

---

## 6. Initial scenario tranche

| Scenario | Direct semantic oracle | UI/frame oracle | Terminal-transport value | Defer |
| --- | --- | --- | --- | --- |
| Startup with 3-line file | text, point, mode, modified=false | body/modeline/echo/cursor | startup readiness and initial paint | host path semantics |
| End-of-buffer | unchanged text, point at max, message | cursor and echo | control-key decoding | none |
| Insert/move/undo | text, point, modified/undo outcome | cursor/modeline/message | ordered key delivery | exact Emacs redo-point deviation initially |
| Resize | stable state, active visible range | dimensions, regions, cursor bounds | terminal resize propagation | split windows until core slice is stable |
| Exit | running=false, final state | optional final frame | stop/exit/drain evidence | process-tree stress cases until the terminal contract is ready |

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
| Terminal portability blocks the first example | Ship direct example at G3; use implemented ConPTY on Windows and keep POSIX PTY as a separate future adapter |
| Licensing/provenance loss | `LICENSE`, `NOTICE`, `PROVENANCE.md`, and executable manifest checks |
| Browser terminal expands scope | Defer until G7 and a terminal slice proves the abstraction is needed |

---

## 8. Verification performed for this assessment

- Original 2026-07-16 evidence: TermVerify `206 passed`; RecursiveNeon editor `1,585 passed` on Windows/Python 3.13.2. The Unix-only parity harness was not run, so the assessment made no GNU Emacs PTY claim.
- The 2026-07-19 reassessment inspected TermVerify code, tests, accepted design records, active handover, merged history through `2c514be`, PR #144's real-child key evidence, and external-subject evidence in issue #114. No new local test-count claim is made because this documentation update does not change runtime code.
- No RecursiveNeon editor/TUI source changed between the original reviewed revision and this documentation reassessment.

---

## 9. Next decision point

The Phase 2 activation reshapes the next focused workstreams. On the TermVerify side, **slice 3 (caller-bound transcript replay)** is the next dependency: once it lands, the supported verify-record-and-replay loop is available end-to-end and G3 can move from Partial to Open for the exact-comparison path. The remaining G3 pieces — semantic/snapshot oracle policy and a normalizer/state-schema registry — stay caller-side by design and will be exercised through the RecursiveNeon adapter rather than added to the Phase 2 boundary.

On the RecursiveNeon side, Phase C is substantially done (PR #72, `CoreEditorSession`), so **Phase D (living-checkout `DirectNeonEditorAdapter`)** can now compose `CoreEditorSession` directly and exercise the slice-1 recorder + slice-2 comparator against real editor transcripts. The remaining Phase C follow-ups (deterministic async drain for shell-mode scenarios; dired current-time injection) gate Phase D2, not Phase D.

Suggested next sequencing:

1. TermVerify slice 3 (caller-bound transcript replay) — unblocks the full G3 verify-record-and-replay path.
2. RecursiveNeon Phase D — `DirectNeonEditorAdapter` over `CoreEditorSession`, consuming `TranscriptRecorder`/`run_scripted`/`compare_transcripts` directly; add one deliberate-failure scenario to exercise the comparator's `ComparisonVerdict`/`render_report` against real divergent editor transcripts.
3. Remaining G3 oracle/normalizer pieces — defined caller-side through the Phase D adapter, not added to the Phase 2 boundary.
4. Phase D2 — direct in-process shell fixture, after the Phase C async drain/quiescence follow-up lands.

Use TermVerify issue #114 as the shared external-subject prioritization thread. Do not open an extraction PR (Phase E) or claim a supported example before Phase D passes against the open G3 path.
