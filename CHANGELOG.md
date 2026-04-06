# Changelog

All notable changes to Recursive://Neon are documented here.

## Phase 7c — Tech Debt Cleanup (2026-04-06)

### Added
- **TUI `on_tick` timer** (7c-1 / TD-003) — `TuiApp` protocol gained `tick_interval_ms` and `on_tick(dt_ms)`. `RawInputSource.get_key` now accepts `timeout` keyword. `run_tui_app` fires ticks via keystroke-read timeout. `sysmon` sets `tick_interval_ms=1000` and auto-refreshes every second without keypresses. 5 new tests in `test_tui.py`.
- **`_MarkSet` identity wrapper** (7c-2 / TD-004) — New `_MarkSet` class in `buffer.py` wraps mark tracking with `id()`-based membership. `track_mark`/`untrack_mark` delegate to `_MarkSet.add`/`discard`. Debug assertion catches duplicate tracking. 9 new tests in `test_mark_set.py`.
- **TUI terminal size + resize handling** (7c-4 / TD-005) — `_measure_terminal()` reads real terminal dimensions via `shutil.get_terminal_size`. `run_tui_app` accepts `resize_source` callback and drains resize events each loop iteration. Local CLI path polls on each keystroke/tick. WebSocket protocol extended with `{"type": "resize", "width": N, "height": M}` messages. `TerminalSession.feed_resize()` stores pending events. `wsclient` sends resize on connect. 11 new tests in `test_tui_resize.py`.
- **Filesystem name uniqueness** (7c-5 / TD-006 bug 1) — `AppService` gained `_find_child_by_name` and `_check_name_collision` helpers. All mutating methods (`create_file`, `create_directory`, `update_file` rename, `copy_file`, `move_file`) now raise `FileExistsError` on `(parent_id, name)` collision. `copy_file`/`move_file` accept `overwrite: bool = False` flag for future `cp -f`/`mv -f` semantics. 9 xfail tests turned green.
- **Per-buffer save_callback** (7c-5 / TD-006 bug 2) — Editor `save_callback` replaced single shared `file_id` closure with per-buffer `dict[id(buffer), str]` mapping. Save resolves existing files by path on first save of a `find-file`'d buffer, preventing duplicate nodes and cross-buffer corruption. 4 xfail tests turned green.
- **Undo-group coalescing** (7c-6) — `Command` dataclass gained `coalesce_key: str | None` field. `defcommand` decorator accepts `coalesce_key=`. Dispatcher skips undo boundary when consecutive commands share a non-None key. Keys: `"insert"` (self-insert), `"delete-backward"` (Backspace), `"delete-forward"` (C-d), `"kill"` (kill-line/word/region/sentence), `"yank"` (yank/yank-pop). `_last_coalesce_key` cleared in `_reset_transient_state`. 7 new tests in `test_undo_chain.py`.
- **45 new tests** across 4 files (2 new + 2 extended). **1815 passing tests total** (+45 from 7b's 1770). **0 xfail** (down from 13).

### Changed
- **`RawInputSource` protocol** — `get_key` signature changed to `get_key(*, timeout: float | None = None) -> str | None`. `None` return signals timeout (used for tick callbacks). All implementations (`LocalRawInput`, `WebSocketRawInput`, test mocks) updated.
- **`run_tui_app` signature** — gained `resize_source` parameter for pluggable resize detection.
- **`shell.py::_make_run_tui`** — now measures terminal size and passes `width`/`height`/`resize_source` to `run_tui_app`.
- **`terminal.py::TerminalSession`** — gained `_terminal_size`, `_resize_pending`, `feed_resize()`. TUI factory passes measured WS dimensions and resize drain to `run_tui_app`.
- **`main.py::_ws_reader`** — routes `"resize"` message type to `session.feed_resize()`.
- **`editor/editor.py` dispatcher** — undo boundary logic uses `cmd.coalesce_key` instead of hard-coded `name != "self-insert-command"` check. Both `_execute_command_by_name` and `execute_command` updated.

### Fixed
- **TD-001 re-audit** (7c-3) — `pydantic.v1` warning still fires with `langchain-core==1.2.20` / `pydantic==2.12.5` / Python 3.14.3. Filter stays; dated re-audit note added to `TECH_DEBT.md`.
- **TD-006 resolved** — 13 xfail regression tests (9 filesystem + 4 editor) now pass. Filesystem prevents duplicate `(parent_id, name)` pairs; editor tracks file IDs per buffer.

## Phase 7b — Shell Pipeline Completeness (2026-04-06)

### Added
- **Recursive globs (`**`)** (7b-1) — `expand_globs()` now handles `**` patterns for zero-or-more directory matching. Supports `**/*.txt` (any depth), `Documents/**` (everything under), `**/notes.md` (specific name at any depth), `deep/**/c.txt` (between literals), and `**` alone (all files). Combined with `?` and `[...]`. Recursive traversal stays bounded to the virtual filesystem. 13 new tests in `test_glob.py`.
- **Stderr redirection** (7b-2) — Parser recognises `2>`, `2>>`, and `2>&1` redirect forms. `Redirect` dataclass gained `fd` field (1=stdout, 2=stderr). `Pipeline` gained `stderr_redirect` field. All five forms work: `cmd 2> file`, `cmd 2>> file`, `cmd > out 2> err`, `cmd > all 2>&1`, `cmd 2>&1 | grep`. New `MergedStderrOutput` class routes `error()` calls to the stdout stream for `2>&1` merging. 17 new tests in `test_pipeline.py`.
- **Builtins in pipes** (7b-3) — Builtins (`cd`, `exit`, `export`) verified to work correctly in pipelines: they safely discard piped stdin and now route stderr through the redirect infrastructure when `2>` is used. 5 new tests in `test_builtins.py`.
- **WS client `--command` batch mode** (7b-4) — `python -m recursive_neon.wsclient --command "ls Documents"` connects to the server, runs a single command, prints output, and disconnects. ANSI codes are stripped when stdout is not a TTY (for pipeline use). Exit code reflects command success/failure. `-c` short flag available. Persistent sessions remain deferred. 6 new tests in `test_wsclient_batch.py`.
- **40 new tests** across 4 files. **1770 passing tests total** (+40 from 7a's 1730).

### Changed
- **`shell/glob.py`** — `_match_glob` refactored into `_match_simple` (original single-level logic) and `_match_recursive` + `_collect_all` (new depth-first `**` traversal).
- **`shell/parser.py`** — `parse_pipeline` rewritten to handle multiple redirect operators in a single line. New `_extract_redirect_target` helper parses one token at a time, allowing `> out 2> err` combinations.
- **`shell/shell.py`** — `_execute_tokens` and `_make_program_context` gained `stderr_output` parameter. `execute_line` routes stderr based on `Pipeline.stderr_redirect`. Builtin error-stream swapped when stderr is redirected.
- **`wsclient/__main__.py`** — Added `--command`/`-c` argument; batch mode exits with the command's exit code.

## Phase 7a — Shell Buffer Completions (2026-04-06)

### Added
- **Read-only regions** (7a-1) — `ReadOnlyRegion` dataclass with tracked mark pairs on `Buffer`. New API: `add_read_only_region`, `remove_read_only_region`, `clear_read_only_regions`, `is_read_only_at`. Enforcement at all public mutation boundaries (`insert_char`, `insert_string`, `delete_char_forward/backward`, `delete_region`). Programmatic bypass when `_undo_recording=False` (for shell output insertion). Editor shows "Text is read-only" in message area. Shell mode applies a single region `[(0,0), input_start)` after each command.
- **Text attributes** (7a-2) — `TextAttr` frozen dataclass (`fg`/`bg`/`bold`/`dim`/`italic`/`underline`/`reverse`, 256-colour). Lazy `Buffer._line_attrs` per-character attribute storage (zero cost for plain-text buffers). `Buffer.insert_string_attributed(runs)` for attributed text insertion. `AnsiParser.parse_ansi()` converts ANSI-encoded text to `(text, attr)` runs. All six mutation primitives maintain attrs behind `if self._line_attrs is not None` guards. `UndoDelete.attrs` field captures per-character attributes for undo round-trip. Rendering via existing `StyleSpan` pipeline at priority 10 (below isearch 20/25).
- **General after-key async bridge** (7a-3) — `Editor._after_key_queue` replaces `_pending_async`. `Editor.after_key(cb)` enqueues callbacks; `EditorView.on_after_key()` drains in FIFO order with error isolation. `asyncio.sleep(0)` yields to event loop so background tasks can run before re-render. `Editor.request_render()` flag for background-task re-render signalling.
- **Interactive programs in shell buffer** (7a-4) — `ShellBufferInput.get_line` creates an `asyncio.Future`, opens the editor minibuffer, and `await`s the result. Shell commands spawned as `asyncio.Task`s (not direct await) so interactive programs like `chat` can suspend at `get_line` without blocking the runner. Output flushed before each `get_line` call. C-g in minibuffer raises `EOFError` on the Future.
- **TUI app passthrough** (7a-5) — `run_tui_app` injects a `launch_child` callback into apps via `set_tui_launcher`. `EditorView` stores and exposes to `Editor`. Shell mode sets `_run_tui_factory` on the shell to delegate to `editor.tui_launcher`, enabling `codebreaker`/`sysmon`/`edit` from the shell buffer.
- **Design document** at `docs/PHASE_7A_DESIGN.md` covering all five sub-items.
- **110 new tests** across 7 new test files: `test_read_only_regions.py` (39), `test_async_bridge.py` (10), `test_text_attr.py` (10), `test_ansi_parser.py` (19), `test_buffer_attrs.py` (22), `test_shell_buffer_interactive.py` (6), `test_tui_passthrough.py` (4). **1730 passing tests total** (+110 from 6l-5's 1620).

### Changed
- **`BufferOutput`** no longer strips ANSI at write time — raw text is preserved for later parsing by the attr layer. `execute_shell_command` parses ANSI into attributed runs when the buffer has attrs enabled, falls back to `strip_ansi` otherwise.
- **`_pending_async`** replaced by `_after_key_queue` across `editor.py`, `view.py`, and `shell_mode.py`. Shell mode tests updated accordingly.
- **`UndoDelete`** dataclass gains optional `attrs` field (default `None`, backward-compatible).

### Architecture notes
- **Buffer attrs are rendered through the existing StyleSpan pipeline** — `_compute_buffer_attr_spans` in `view.py` converts per-character attrs to `StyleSpan` entries at priority 10. Isearch highlights (priority 20/25) correctly override buffer colours. Zero changes to `ScreenBuffer`, `set_line`, `set_region`, or `render_ansi`.
- **Interactive shell programs use cooperative async** — shell commands run as `asyncio.Task`s. `get_line` suspends via `asyncio.Future`; `asyncio.sleep(0)` in `on_after_key` yields to the event loop so the task can resume before re-rendering. This avoids deadlock: the runner can process minibuffer keystrokes while the interactive program is suspended.
- **TUI passthrough uses nested `run_tui_app`** — the injected launcher calls `run_tui_app` recursively with the same `raw_input`/`output`. Only one reader is active at a time (child takes over during its lifetime), so no contention.

## Phase 6l-5 — Deferred Items: Undo Granularity Bug (2026-04-06)

### Fixed
- **Undo-after-Backspace bug** (observed during the Phase 6k tutorial walk-through): a second `C-/` after a `Backspace` used to behave like redo instead of continuing to walk back through history. Two-layered root cause, both fixed:
  1. `Editor._execute_command_by_name` / `Editor.execute_command` unconditionally called `buf.add_undo_boundary()` before every command — including `undo` itself. `add_undo_boundary()` has a chain-break side effect (it clears `last_command_type == "undo"` and resets `_undo_cursor`) that defeated `Buffer.undo()`'s consecutive-undo chain tracking. **Fix**: skip the boundary in the dispatcher when the command is `undo`. Inlined rationale references the chain-break side effect.
  2. `Buffer.undo()` extended reverse entries onto the undo list without inserting a boundary between the source group and the reverse group. A later chain-break followed by another undo would then walk both groups in a single pass, collapsing two user-visible states into one keystroke. **Fix**: `Buffer.undo()` now appends an `UndoBoundary` before extending reverse entries (no-op if the previous entry is already a boundary).

### Changed
- **`Buffer.add_undo_boundary()` signature** — now takes an optional `break_undo_chain: bool = True` keyword argument. Default behaviour is unchanged (break the chain, for fresh command dispatch). `Buffer.undo()` passes `break_undo_chain=False` when inserting the mid-chain boundary before its reverse entries, so the undo chain state survives. The alternative — inlining the boundary-append in `undo()` — was rejected as a footgun: future code touching the undo path would be easy to miss. A single, documented flag on the public API is cleaner.

### Added
- **`tests/unit/editor/test_undo_chain.py`** (new, 7 tests) covering both the editor-level flow (the exact tutorial walk-through scenario — `type "abc" → Backspace → C-/ → C-/` must end at `""`, not `"ab"`) and the buffer-level invariants (boundary-before-reverses, no duplicate boundary when the source group is already bounded, consecutive `Buffer.undo()` calls walk multiple groups back). **1620 passing tests total** (+7 from 6l-4's 1613).

### Architecture notes
- **Two last-command trackers, at two layers**: `Editor._last_command_name: str` (dispatcher-level, used for self-insert-command coalescing) and `Buffer.last_command_type: str` (buffer-level, used for kill-ring merging and the undo chain). The chain-break machinery in `add_undo_boundary` is wired through the *buffer-level* `last_command_type == "undo"` check. Regular edit primitives (`insert_char`, `delete_char_*`, `delete_region`, ...) do NOT touch `last_command_type` at all — only `undo`, the kill family, and the yank family do. This is why the 6l-5 fix targets the dispatch path (where `undo` is named) rather than the primitive path (where the chain-break would need a new signal wired through every edit primitive).
- **Discovery recorded in `V2_HANDOVER.md` 7c-6** (new sub-phase): the existing command-run coalescing is too conservative — only `self-insert-command` runs merge into a single undo group. Real Emacs coalesces runs of Backspace, C-d, C-k, yank, etc. Scheduled for Phase 7c before the browser work so every future frontend inherits the improved granularity. The design adds a new `Command.coalesce_key: str | None` attribute and an `Editor._last_coalesce_key` field — explicitly separate from `Buffer.last_command_type` (which stays focused on kill-ring merging + undo chain, orthogonal concerns).

## Phase 6l-4 — Query-Replace (M-%) (2026-04-05)

### Added
- **`query-replace` command** bound to `M-%`. Emacs-style interactive find-and-replace:
  - Two sequential minibuffer prompts collect the search and replacement strings (`Query replace: `, `Query replace <from> with: `). Both prompts accept `M-Enter` to insert a literal newline, enabling multi-line search/replace (the Buffer-level multi-line support from 6l-3).
  - Match highlighting via the 6l-3 `editor.highlight_term` mechanism — all occurrences in the visible region show the non-current highlight; the match point is on shows the current-match highlight (point-driven, no new field needed).
  - Ten in-session keys: `y` / `SPC` replace-and-advance; `n` / `DEL` / `Backspace` / `Delete` skip-and-advance; `q` / `Enter` exit; `.` replace-and-exit; `!` replace-all-remaining; `u` undo-last; `U` undo-all-and-exit; `e` edit replacement in a nested minibuffer; `C-g` cancel-and-restore-point; `?` show a one-line help legend.
  - **Per-session undo stack** for `u`/`U` — each replacement is recorded in `_QueryReplaceSession.replacements` as a `_Replacement(line, col, from_text, to_text)` tuple. `u` pops LIFO and issues reverse `buf.delete_region` + `buf.insert_string` ops to revert the last replacement; session stays active and re-installs the reverted match. `U` pops the whole stack, reverts everything, exits, and restores point to the session start.
  - **Single undo group on exit** — replacements and reverts during the session go through raw buffer ops without intervening boundaries, so the entire session compacts into one `Buffer.undo_list` group. A single post-session `C-/` reverts every replacement at once.
  - Smart-case default: session case-fold is computed once at entry using the same rule as isearch (`case-fold-search` defvar AND `from_text.islower()`). No per-session `M-c` toggle (not in the 6l-4 spec).
  - `e` (edit replacement) opens a nested minibuffer pre-filled with the current `to_text`. A `paused_for_edit` flag on the session suppresses the top-level query-replace routing so the minibuffer handles keystrokes normally. The minibuffer's `process_key` is patched so the session resumes on both submit (new text applied) and cancel (old text preserved).
  - `C-g` cancels cleanly: point is restored to the session start, committed replacements stay, highlight is cleared, message shows "Quit".
  - Zero-match on entry: `"No matches for <from>"` message, session never installed.
  - Report message on natural exit: `"Replaced N occurrence(s)"`; on `U`: `"Undid all N replacement(s)"`; on `C-g`: `"Quit"`.
- **`_QueryReplaceSession` + `_Replacement` dataclasses** in `editor/default_commands.py`. Session holds from/to text, case-fold flag, start point, replacement stack, `paused_for_edit`, and `replaced_count`. Cleared by `Editor._reset_transient_state()` so `keyboard-escape-quit` and other blanket resets cover it for free.
- **Query-replace routing hook in `Editor.process_key`** — new branch between describe-key and the ESC state machine (per the 6l-2 discovery). Runs only when the session is active and NOT paused for edit, so the nested `e` minibuffer gets keys via the normal minibuffer routing step.
- **62 new tests** in `test_query_replace.py` across 13 classes: registration/keymap binding (2), entry flow (7), basic keys y/SPC/n/Backspace/Delete/q/Enter/./highlight cleanup (12), replace-all `!` (3), undo stack u/U with single-undo-group verification (8), C-g cancel (4), `e` edit replacement with submit *and* cancel resume (4), `?` help and invalid-key handling (3), multi-line search/replacement via M-Enter (4), highlighting + case-fold (5+2), reset/routing/session-dataclass invariants (3+3+2). **1613 passing tests total** (+62 from 6l-3's 1551).

### Changed
- **Describe-key state refactored to a `_DescribeKeySession` dataclass** in `editor/editor.py` — collapses six previously-scattered fields (`_describing_key`, `_describing_key_briefly`, `_describing_key_prefix`, `_describing_key_map`, `_dkb_prefix`, `_dkb_map`) into a single `self._describe_key_session: _DescribeKeySession | None`. Establishes the "capture-mode session object" pattern that query-replace reuses; future capture modes should follow suit and clear their session in `_reset_transient_state()`. 14 existing test-level assertions migrated; all 896 pre-existing editor tests still pass.
- **`Editor.process_key` routing order**: describe-key → **query-replace (NEW)** → ESC state machine → meta-pending rewrites → minibuffer → C-g intercept → normal keymap. The query-replace branch sits *above* the ESC state machine so a bare ESC inside a session is handled as an in-session invalid key (the spec has no ESC action); blanket cancellation goes through `C-g` or `keyboard-escape-quit` which calls `_reset_transient_state()`.

### Fixed
- **Test isolation bug in `test_isearch_v2.py`** (pre-existing, only surfaced when test_query_replace landed alphabetically after it): `test_case_fold_search_variable_false_disables_smart_fold` mutated the module-level `VARIABLES["case-fold-search"].default` via `ed.set_variable(...)` without restoring it, leaking state into subsequent tests. Wrapped in try/finally.

### Deviations (documented inline in `default_commands.py`)
- **`?` help is a one-line message area legend** instead of Emacs's pop-up window. Real Emacs shows query-replace help in a split window that doesn't disturb the session; our `_show_help_buffer` would switch the active buffer and lose the current match. A faithful implementation is disproportionately complex under our synchronous TUI model. The compact legend fits on ~95 columns and clips gracefully on narrower screens.
- **`case-replace` (preserve input case in replacement) is NOT implemented.** Literal replacement only. Deferred.
- **`M-c` mid-session case-fold toggle is NOT implemented** — isearch has it (6l-3), but the 6l-4 spec doesn't. Case-fold is decided once at session entry via the smart-case rule.

### Architecture notes
- **Session-object pattern is now the convention** for long-running capture modes. Describe-key and query-replace both use `dataclass-on-Editor + routing-check-early-in-process_key + clear-in-_reset_transient_state`. Any future capture mode (a plausible candidate: `query-replace-regexp` in a follow-up) should follow suit.
- **Undo model: no-internal-boundary invariant drives the single-session-group guarantee.** Query-replace keystrokes bypass `_execute_command_by_name` (they're captured directly), so no `add_undo_boundary()` calls fire during the session. Raw `delete_region` + `insert_string` operations pile into one contiguous run between boundaries; a post-session `C-/` walks the whole run LIFO and reverts everything. The session's own `replacements` stack handles `u`/`U` at a higher level without touching `Buffer.undo()`. **Alternate design considered and recorded in `V2_HANDOVER.md` 6l-4 addendum** (per-replacement boundaries with exit-collapse) in case the compound-reverts model ever produces confusing interactions with future features.
- **Multi-line match end helper**: `_qr_match_end` in `default_commands.py` duplicates the 5-line logic of `view._match_end`. Both compute "position just past a multi-line match start". Could be factored to a shared module if a third caller emerges.

## Phase 6l-3 — True Incremental Search (2026-04-05)

### Added
- **`StyleSpan` + post-compose styling pass** — new `StyleSpan(row, col, width, style, priority)` dataclass in `shell/tui/__init__.py`. `EditorView._style_text_rows` walks the composed plain-text screen after `_render_window` finishes and wraps character ranges in ANSI codes. Parallel to the existing `_style_modeline_rows`. Overlap resolution per cell by priority (strict `>`, stable by emission). Reserved priorities: 10 syntax (future), 20 isearch non-current match, 25 isearch current match, 30 region (future), 40 cursor line (future). **This is the canonical extension point for syntax highlighting** and any future layered-text-overlay feature.
- **True `isearch-forward` / `isearch-backward`** on C-s / C-r (`default_commands.py`):
  - Match highlighting: all occurrences of the search term in the visible region are rendered with a yellow-background style; the current match uses a distinct bold+red-background style (`view.py:_compute_highlight_spans`).
  - Wrap-around: when the forward search fails at EOB, the prompt shows `Failing I-search:`. The next C-s wraps to BOB and shows `Wrapped I-search:`. Symmetric for backward (BOB → EOB).
  - State-stack backspace: each successful operation pushes a 6-tuple state (`_IsearchState(text, line, col, direction, wrapped, failing)`). Backspace pops one state, restoring text, point, and wrap flag. Backspace across a wrap correctly returns to the failing state that preceded the wrap.
  - **Smart case-fold** + `M-c` toggle: when the search string is all lowercase, folding is active (Emacs smart-case). Typing an uppercase character disables folding for the session. `M-c` explicitly toggles the override; prompt shows `(case)` / `(fold)` when overridden.
  - **Multi-line search** via `M-Enter` (not C-j — see Deviations). Inserts a literal `\n` into the search term; `Buffer.find_forward`/`find_backward` match across line boundaries.
- **`editor.highlight_term` / `editor.highlight_case_fold` fields** — lifecycle owned by the active interactive command. Set on isearch entry, updated on every keystroke that changes the term, cleared on exit / cancel / exit-and-replay. `Editor._reset_transient_state()` also clears them, so `keyboard-escape-quit` and future blanket-reset callers cover them for free. `query-replace` in 6l-4 will inherit the same contract.
- **`search-forward` / `search-backward`** — the legacy (pre-6l-3) incremental-search behaviour, retained as M-x-only commands. No highlighting, no wrap-around. Use C-s / C-r for the full experience.
- **`Buffer.find_forward` / `find_backward`** now handle `\n` in the needle and accept a `case_fold: bool = False` kwarg. Multi-line scan walks line-by-line without allocating a joined string. Returned positions refer to the un-lowercased buffer even when case-fold is active.
- **`defvar("case-fold-search", True)`** in `variables.py` — global default for case-fold behaviour, overridable per-buffer via the existing cascade.
- **58 new tests** — 21 Buffer search tests (`TestFindForwardMultiLine`, `TestFindBackwardMultiLine`, `TestFindForwardCaseFold`, `TestFindBackwardCaseFold` in `test_isearch.py`); 9 `TestStyleTextRows` tests in `test_view.py`; 28 behaviour tests in the new `test_isearch_v2.py` (highlighting, wrap progression, state-stack, case-fold smart + toggle, M-Enter multi-line, exit-and-replay with highlight, rename routing). 1551 tests total.

### Changed
- **C-s / C-r** now route to the new isearch implementation. Command names are unchanged (`isearch-forward` / `isearch-backward`), so existing keymap lookups and M-x invocations continue to work. The old behaviour's 19 minibuffer-contract tests in `test_isearch.py` still pass unchanged.
- **`EditorView._render_window`** signature gains a `text_spans: list[StyleSpan]` out-parameter that each window contributes to; `EditorView._render` aggregates and passes to `_style_text_rows` before modeline styling.

### Deviations (documented inline)
- **`M-Enter` instead of `C-j`** for inserting a literal newline into the isearch search term. Rationale: `shell/keys.py:45-46` maps both `\r` and `\n` to `"Enter"`, making C-j indistinguishable from Enter in our key encoding. M-Enter is unambiguous on every platform. Registered via `ed.minibuffer.key_handlers["M-Enter"]` from the isearch setup code. See the comment block at the top of the isearch section in `default_commands.py`. This is a sanctioned deviation under the project's Emacs-fidelity rule (faithful behaviour would require redesigning key encoding for one binding).
- **`minibuffer.py` was not modified.** The original addendum plan anticipated a C-j self-insert branch and an M-c handler hook inside the minibuffer core. Both turned out to be achievable via the existing `minibuffer.key_handlers[...]` extension mechanism from the isearch setup code. Net scope shrink.

### Architecture notes
Phase 6l-3's rendering architecture (span-list + post-compose, chosen as "Option A" from four candidates evaluated in `V2_HANDOVER.md:6l-3 addendum`) locks in a clean migration path: future syntax highlighting produces additional spans at priority 10, with no changes needed to `StyleSpan` or the post-pass. If per-cell merging ever becomes expensive enough to warrant a character-attribute grid (Option D), the span *producers* (isearch, query-replace, syntax highlighter) won't need to change — only the internal storage of `ScreenBuffer`.

## Phase 6l-2 — `keyboard-escape-quit` + ESC-as-Meta (2026-04-05)

### Added
- **`keyboard-escape-quit` command** — ESC ESC ESC cancels all transient state and dismisses the minibuffer / `*Help*` buffer. Delegates minibuffer cancellation to `mb.process_key("C-g")` so isearch's patched-process cancel (with point restore) still fires. Dismisses `*Help*` by switching to the most recent non-Help buffer; the buffer stays on the list so the user can C-x b back to it.
- **ESC-as-Meta state machine** in `Editor.process_key` — bare Escape sets `_meta_pending`; the next non-ESC key is rewritten as `M-<key>` (ESC f → M-f, ESC x → M-x, ESC C-f → C-M-f). A second bare Escape transitions to `_escape_quit_pending`; a third runs `keyboard-escape-quit`. C-g during meta-pending always cancels (not C-M-g) to preserve the universal-quit semantics.
- **`_rewrite_as_meta` static helper** — rewrite rules for the ESC state machine: printable → `M-x`, named → `M-Enter`, `C-f` → `C-M-f`, already-`M-` / `C-M-` leave unchanged.
- **Describe-key handles Escape specially** — `C-h k Escape` now describes Escape as the Meta prefix (with a curated help message) instead of reporting "not bound". Describe-key runs *before* the ESC state machine in `process_key` so capture works cleanly.
- **38 new tests** in `test_escape_meta.py` across 9 classes: `TestEscAsMeta` (8), `TestEscapeQuitNormalMode` (4), `TestEscapeQuitMinibuffer` (5), `TestEscapeQuitHelpBuffer` (2), `TestKeyboardEscapeQuitDirect` (4), `TestEscapeDescribeKey` (2), `TestEscapeInIsearch` (1), `TestEscStateMachine` (6), `TestRewriteAsMeta` (6). 1493 tests total.
- **TD-006 recorded** — user bug report during Phase 6l-2 surfaced two tightly related bugs: (1) `AppService` mutating calls (`create_file`, `create_directory`, `update_file` rename, `copy_file`, `move_file`) never check for `(parent_id, name)` collisions; (2) `shell/programs/edit.py`'s `save_callback` closes over a single shared `file_id`, so buffers opened later via `find-file` write into the wrong filesystem node. Together they produce duplicate filenames and silent data corruption during multi-buffer editing. **16 xfail regression tests** (13 xfail + 3 passing control tests) added: `tests/unit/test_filesystem_name_uniqueness.py` (12) + `tests/unit/shell/test_edit_save_callback.py` (4). Scheduled for Phase 7c-5; full fix plan in `docs/TECH_DEBT.md` and `V2_HANDOVER.md`.

### Changed
- **Describe-key capture now runs *before* minibuffer routing** in `process_key`. Necessary so the ESC state machine (which sits between describe-key and minibuffer routing) doesn't steal ESCs intended for `C-h k` / `C-h c` capture. Any future capture-style mode should sit alongside describe-key, above the ESC state machine.
- **Three-ESCs-in-minibuffer** intentionally deviates from Emacs prose. The prose said "three ESCs dismiss" AND "bare ESC in minibuffer still cancels cleanly" — contradictory in a synchronous keystroke model. Implementation prefers the state-machine-clean interpretation: a single ESC in the minibuffer sets `_meta_pending` but does not cancel; three ESCs run `keyboard-escape-quit` which dismisses via `mb.process_key("C-g")`. The unit-level `Minibuffer.process_key("Escape")` contract is preserved for direct callers.

### Fixed
- **Describe-key `C-g` / `Escape` not cancelled** — `C-h k C-g` now describes the `keyboard-quit` binding (Emacs behaviour) instead of cancelling the capture. `C-h k Escape` describes the Meta prefix.
- **Minibuffer cancel preserves the mark** — `C-SPC C-x b C-g` leaves the mark active (Emacs behaviour). The original prose said "clears the transient region/mark in all cases" which was a bug.

## Phase 6l-1 — `keyboard-quit` Audit and Hardening (2026-04-05)

### Added
- **`Editor._reset_transient_state()` helper** — shared foundation for `keyboard-quit` (C-g) and the upcoming `keyboard-escape-quit` (6l-2). Clears region / mark, pending prefix keymap, `_prefix_keys`, prefix argument state, describe-key capture (both full and briefly), and any other transient interactive flags.
- **Top-level C-g intercept in `Editor.process_key`** — mirrors Emacs's `quit` signal. C-g short-circuits any pending prefix keymap (mid-`C-x`) instead of falling through as "C-x C-g is undefined".
- **Promoted describe-key state to explicit `__init__` fields** — `_describing_key_prefix`, `_describing_key_map`, `_dkb_prefix`, `_dkb_map` are now initialised in `Editor.__init__` instead of being dynamic attributes set on demand. Makes the reset helper robust.
- **19 new tests** in `test_keyboard_quit.py` covering every cancellation path: mid-prefix-keymap C-g, C-u prefix-arg cancel, minibuffer cancel preserving mark, M-x mid-type cancel, describe-key capture (C-g is NOT cancelled; it describes the `keyboard-quit` binding — Emacs behaviour), isearch cancel with point restore, region clear at top level. 1452 tests total.

### Introduced
- **Emacs-fidelity design principle** in `V2_HANDOVER.md`: *"Emacs is the ground truth."* For every neon-edit feature, the goal is to match real GNU Emacs exactly. If a design doc contradicts Emacs, the prose is almost certainly wrong — treat it as a bug and match Emacs instead. Sanctioned deviations require documenting next to the diverging code.

## Phase 6k — Tutorial Verification + Polish (2026-04-04)

### Added
- **Tutorial walk-through integration test** — `test_tutorial_walkthrough.py` drives every chapter (1–14) of `TUTORIAL.txt` programmatically through the `EditorHarness`. One test class per chapter covers movement, scrolling, editing, kill/yank, mark/region, word/sentence motion, search, files/buffers, help, replace-string, fill, windows, and (async) shell mode. A Quick-Reference consistency class ensures every advertised command appears in `describe-bindings` output. 72 new tests.
- **`describe-bindings` (C-h b)** — Lists every reachable keybinding in a `*Help*` buffer, grouped by layer (buffer-local → minor modes → major mode → global). Prefix keymaps are recursively expanded so nested sequences like `C-x C-s`, `C-h k`, and `C-x 4 C-f` all appear.
- **`_format_bindings_local` helper** — Local-only variant of the existing `_format_bindings` that walks sub-keymaps without inheriting parent chain entries, so layered display doesn't duplicate global bindings under each layer.
- **Autouse variable-restore fixture** in the walk-through test — Saves and restores `VARIABLES` defaults around each test so `set-fill-column` and `M-x set-variable` mutations don't leak into `test_variables.py`.
- **10 new `describe-bindings` unit tests** in `test_help.py` covering section headers, prefix expansion, self-reference, nested prefixes, buffer-local and major-mode layers, and the no-duplication invariant.
- **82 new tests total** (10 describe-bindings + 72 walkthrough). 1433 total tests.

### Changed
- **TUTORIAL.txt** — Removed all 5 `[NOT YET IMPLEMENTED]` markers (chapters 10–14: sentence motion, find/replace, text filling, windows, shell mode). Each chapter now has real practice prompts instead of "will be available in a future system update" placeholders. Quick Reference expanded with `M-a`/`M-e`/`M-k` (sentence), `M-q`/`C-x f` (fill), `C-x s` (save-some-buffers), window commands (`C-x 2`/`3`/`o`/`0`/`1`, `C-x 4 C-f`), shell mode (`M-x shell`, `M-p`, `M-n`), and help additions (`C-h b`, `C-h m`, `C-h v`).
- **`C-h` prefix keymap** gains `b` → `describe-bindings`.

### Deferred
- **Python config file loading** — the `EditorVariable`/`Mode` API (Phase 6g) is fully functional but there's no `~/.neon-edit.py` loader. Tracked as "Python extension API" under Future 6a extensions.
- **Game-world integration hooks** — no NPC-triggered buffer events or editor↔game-state bridge. A dedicated phase would need to design those hooks before a tutorial chapter makes sense.
- **Undo granularity inspection** — observed during walk-through that a second C-/ after a single Backspace appears to redo rather than continue undoing. Not blocking; noted in handover for a future polish pass.

## Phase 6j — Shell-in-Editor (2026-04-04)

### Added
- **Shell-in-editor (M-x shell)** — Run the game's shell inside an editor buffer, like Emacs comint-mode. `shell-mode` major mode with a buffer-local keymap. Type commands at a prompt, press Enter, see output appear inline. The shell is an in-process Python object (no subprocess).
- **Async bridge (`on_after_key`)** — Backward-compatible TUI runner extension: after each keystroke, the runner checks for an optional async `on_after_key()` method on the TuiApp and awaits it. Enables sync `on_key()` to trigger async shell command execution. Existing TUI apps are unaffected.
- **`BufferOutput`** — `Output` subclass that captures shell output as ANSI-stripped plain text for insertion into the editor buffer.
- **`ShellState`** — Per-buffer shell state tracking: Shell reference, `input_start` mark, history navigation index, finished flag.
- **Shell-mode commands**: `comint-send-input` (Enter), `comint-previous-input` (M-p), `comint-next-input` (M-n), shell Tab completion.
- **`Editor.shell_factory`** — Callback set by the `edit` shell program so `M-x shell` can create Shell instances without the editor knowing about the service layer.
- **`Editor._pending_async`** — General-purpose mechanism for commands to schedule async work that the TUI runner executes after the current keystroke.
- **66 new tests** — `test_shell_mode.py`: ANSI stripping (5), BufferOutput (6), setup (9), input extraction (4), input replacement (4), comint-send-input (5), history navigation (8), completion (5), async execution (8), on_after_key (3), M-x shell command (4), integration (5). 1348 total tests.

## Phase 6i — Window System (2026-04-04)

### Added
- **Emacs-style window splitting** — `Window` class with independent cursor (tracked `Mark`) and scroll state per window. `WindowTree` manages a binary tree of horizontal/vertical splits. Each window implements the `Viewport` protocol for per-window scrolling.
- **Window commands**: `split-window-below` (C-x 2), `split-window-right` (C-x 3), `other-window` (C-x o), `delete-window` (C-x 0), `delete-other-windows` (C-x 1), `scroll-other-window` (C-M-v), `find-file-other-window` (C-x 4 C-f). New `C-x 4` prefix keymap.
- **Window rendering** — EditorView refactored to render a window tree: per-window text regions, per-window modelines (active = bright reverse, inactive = dim reverse), vertical dividers (`│`) for side-by-side splits, global message line at bottom.
- **`ScreenBuffer.set_region()`** — Column-range write method for rendering vertical split windows without disturbing adjacent content.
- **Dual-point sync** — Window-local tracked marks stay correct during edits via buffer mark tracking. Movement sync happens around each keystroke dispatch. All 1215 pre-existing headless and TUI tests pass unchanged.
- **67 new tests** — `test_window.py` (30: tree ops, point tracking), `test_window_view.py` (15: rendering), `test_window_commands.py` (22: command integration + headless no-ops). 1282 total tests.

### Fixed
- **`Buffer.track_mark()` identity bug** — Changed from equality-based (`not in`) to identity-based (`any(t is m ...)`) duplicate detection. Two marks at the same position but different objects (e.g., `buffer.point` and `window._point`) were incorrectly treated as duplicates, preventing multi-window point tracking.

## Phase 5 — Shell Improvements (2026-03-26)

### Added
- **Context-sensitive tab completion** (5a) — Per-command completion framework. Programs register `CompletionFn` callbacks via `ProgramRegistry`. New `shell/completion.py` with `CompletionContext`, shared helpers (`complete_paths`, `complete_flags_or_paths`, `complete_choices`).
  - `cd` completes directories only
  - `ls`, `rm`, `grep`, `find`, `mkdir` complete their flags
  - `note` / `task` complete subcommands, then dynamic note indices / task list names / task refs
  - `chat` completes NPC IDs dynamically
  - `help` completes all command names
  - Unknown commands fall back to path completion
  - Works over WebSocket (same `get_completions_ext` path)
- **Shell-level glob expansion** (5b) — `tokenize_ext()` returns `Token(value, quoted)` with quoting metadata. New `shell/glob.py` expands unquoted `*`, `?`, `[...]` against the virtual filesystem before dispatch. Quoted tokens pass through unchanged (POSIX behavior). Unmatched globs are literal.
- **Pipes and output redirection** (5c) — `parse_pipeline()` splits command lines at unquoted `|`, `>`, `>>`. Pipeline segments execute sequentially with buffered stdout passing. `CapturedOutput` (no ANSI codes) used for pipes/redirects. `ProgramContext.stdin` field added; `cat` and `grep` read from it when piped. Redirect writes to virtual files. Stderr always goes to real output.
- **Pipe-aware tab completion** — `_last_pipe_segment()` scopes completions to the current segment after `|`.
- **125 new tests** — context-sensitive completion (58), glob expansion (33), pipes/redirection (34). 527 total tests.

### Changed
- `ProgramRegistry.register` / `register_fn` accept optional `completer` parameter
- `ProgramEntry` gains `completer` field; `get_completer()` method added
- `Shell.get_completions_ext` delegates to per-command completers; `ShellCompleter` simplified to wrapper
- `Shell.execute_line` uses `parse_pipeline` → `expand_globs` → segment execution pipeline
- `builtins.py` exports `BUILTIN_COMPLETERS` dict
- `_get_current_argument` and `_quote_path` moved to `completion.py` (re-exported from `shell.py` for compat)
- Integration test for `find -name` now quotes the glob pattern (required by shell-level expansion)

## Post-Phase 4 Fixes (2026-03-26)

### Changed
- **LangChain migration** — Replaced deprecated `ConversationChain` + `ConversationBufferWindowMemory` from `langchain_classic` with direct LLM message invocation using `langchain_core.messages`. The NPC model already tracked conversation history, making LangChain's memory abstraction redundant. Eliminates all `LangChainDeprecationWarning` messages.
- **Simplified mock LLM** — Test fixtures no longer need `predict`, `generate_prompt`, `BaseChatModel` spec; only `invoke`/`ainvoke` returning `AIMessage`.

### Fixed
- **Chat autocomplete** — Shell tab-completion no longer pops up while chatting with NPCs. Added `complete` parameter to `get_line` protocol.
- **Chat history isolation** — Chat messages no longer pollute shell command history (and vice versa). Added `history_id` parameter to `get_line`; chat uses a separate `InMemoryHistory`.
- **Pydantic v1 warning** — Moved `warnings.filterwarnings` from `shell/__main__.py` and `main.py` to `recursive_neon/__init__.py` so it takes effect before transitive imports trigger the warning.

## Phase 4 — TUI Apps / Raw Mode (2026-03-25)

### Added
- **Raw mode protocol** — Server sends `{"type": "mode", "mode": "raw"|"cooked"}` to switch terminal modes. Client sends `{"type": "key", "key": "..."}` in raw mode; server ignores wrong-mode messages.
- **TUI framework** (`shell/tui/`):
  - `ScreenBuffer` — 2D text grid with cursor position, visibility, and ANSI rendering
  - `TuiApp` protocol — `on_start()`, `on_key()`, `on_resize()` interface for full-screen apps
  - `RawInputSource` protocol — keystroke input abstraction
  - `run_tui_app()` — lifecycle manager: mode switching, keystroke routing, screen delivery
- **CodeBreaker minigame** — Mastermind-style TUI game with ANSI-colored UI, arrow key navigation, symbol cycling, win/loss detection. Registered as `codebreaker` shell command.
- **Local terminal raw mode** — `PromptToolkitInput` wires up `LocalRawInput` + alternate screen buffer for TUI apps.
- **WebSocket client raw mode** — Platform-specific raw key reading (Windows `msvcrt` / Unix `tty.setraw`). Client detects mode switches and routes keystrokes.
- **Headless WebSocket client** — `--headless` flag reads/writes JSON on stdin/stdout for automation.
- **57 new tests** — TUI framework (19), CodeBreaker (27), terminal raw mode + WebSocket integration (11). 402 total tests.

### Changed
- `ProgramContext` gains `run_tui` callback for launching TUI apps
- `/ws/terminal` protocol extended with `mode`, `screen`, and `key` message types
- WebSocket client refactored with session-based architecture for mode switching

## Phase 3 — WebSocket Terminal Protocol + CLI Client (2026-03-24)

### Added
- **`InputSource` protocol** — Shell is now transport-agnostic; receives lines from any source (prompt_toolkit, WebSocket, test mock)
- **`QueueOutput`** — Output adapter that pushes messages to an `asyncio.Queue` for WebSocket delivery
- **`TerminalSessionManager`** — Manages Shell instances by UUID, independent of WebSocket connection lifecycle; supports future persistent sessions
- **`/ws/terminal` WebSocket endpoint** — JSON protocol with `input`, `output`, `prompt`, `complete`/`completions`, `exit`, `error` message types
- **WebSocket CLI client** — `python -m recursive_neon.wsclient` connects to the backend over WebSocket with interactive prompt_toolkit REPL
- **Periodic auto-save** — Background task saves game state every 60s while WebSocket sessions are active
- **Tab completion over WebSocket** — `_WebSocketCompleter` (async generator) sends completion requests to server; server returns items + replacement length
- **`ProgramContext.get_line`** — Callback so programs (e.g. `chat`) can read user input through the shell's `InputSource`, enabling sub-REPLs over WebSocket
- **Typing indicator** — Animated spinner ("NPC is typing...") shown while waiting for LLM response in chat
- **28 new tests** — QueueOutput, WebSocketInput, session manager lifecycle, shell start/stop/feed/exit, tab completion (incl. `get_completions_ext`), WebSocket completer unit test, 8 WebSocket integration tests (345 total)

### Changed
- `shell.py` refactored: prompt_toolkit imports are now lazy (only loaded for local CLI); `PromptToolkitInput` class encapsulates all prompt_toolkit logic
- `ShellCompleter` moved inside a factory function (`_make_shell_completer`) to keep prompt_toolkit deferred
- `Shell.run()` accepts an optional `InputSource` parameter (defaults to `PromptToolkitInput`)
- `Shell.get_completions()` method added for transport-agnostic tab completion; `get_completions_ext()` also returns replacement length
- Chat commands now all use `/` prefix for consistency: `/exit`, `/help`, `/relationship`, `/status`
- WebSocket client uses `patch_stdout(raw=True)` to preserve ANSI codes, `complete_while_typing=False` for Tab-only completion

### Fixed
- ANSI color codes rendered as literal text in chat prompt (missing `ANSI()` wrapper for prompt_toolkit)
- ANSI color codes rendered as literal text in WebSocket client output (`patch_stdout` was stripping escape codes)
- Chat sub-REPL hung over WebSocket (was creating local `PromptSession` instead of using shell's `InputSource`)
- Windows console ANSI support enabled via `ENABLE_VIRTUAL_TERMINAL_PROCESSING` for older terminals

## Phase 2 — Deepen Core Features (2026-03-24)

### Added
- **Note CLI** — `note list/show/create/edit/delete` with 1-based index and UUID prefix references
- **Task CLI** — `task lists/list/add/done/undone/delete` with auto-created default list and `--list` flag
- **`grep`** — regex search across virtual filesystem files/directories (`-i` for case-insensitive)
- **`find`** — glob-based filename search (`find [path] -name <pattern>`)
- **`write`** — create or overwrite file content from the command line
- **`save`** — explicitly save game state to disk
- **Persistence** — filesystem, notes, tasks, NPC state, and shell history all persist to `game_data/` as JSON; auto-save on shell exit
- **NPC think-tag stripping** — `<think>...</think>` blocks from qwen3 models are removed before display and storage
- **NPC system prompt refinement** — brevity instruction, stay in character, no meta-commentary
- **Chat slash commands** — `/help`, `/relationship`, `/status` within NPC conversations
- **Integration tests** — end-to-end workflows for notes, tasks, filesystem, persistence round-trips, chat
- **Corrupt save file handling** — graceful recovery (log + skip) instead of crash

### Changed
- `delete_note`, `delete_task_list`, `delete_task` now raise `ValueError` on missing IDs (consistency with other methods)
- Modernized type hints from `typing.Dict`/`List` to built-in `dict`/`list` across all source files
- Test fixtures use `settings.initial_fs_path` instead of hardcoded relative paths
- Removed duplicate `mock_llm` fixture from `test_npc_manager.py`
- DRY persistence: extracted `_save_json`/`_load_json` helpers in `AppService`

### Fixed
- Think-tags were stored in NPC memory before stripping, polluting conversation history
- `note edit` silently ignored unknown flags (now returns error)
- UUID prefix matching could return wrong item on ambiguous prefix (now requires unique match)
- `ChatProgram` created a new `PromptSession` per input line (chat history now works)

## Phase 1 — CLI Shell (2026-03-24)

### Added
- Interactive shell via `python -m recursive_neon.shell` using prompt_toolkit
- Shell architecture: builtins vs. programs separation with restricted `ProgramContext`
- **Builtins**: `cd`, `exit`, `export`
- **Filesystem programs**: `ls` (`-l`, `-a`), `pwd`, `cat`, `mkdir` (`-p`), `touch`, `rm` (`-r`), `cp`, `mv`
- **Utility programs**: `help`, `clear`, `echo` (with `$VAR` expansion), `env`, `whoami`, `hostname`, `date`
- **Chat program**: `chat <npc_id>` with NPC conversation sub-REPL
- Tab completion for command names and virtual filesystem paths (quoting-aware)
- Command history via prompt_toolkit
- `-h`/`--help` flag support for all commands
- ANSI-colored prompt with exit code indicator
- `CapturedOutput` test abstraction for programmatic testing
- 172 unit tests

## Phase 0 — V2 Bootstrap (2026-03-23)

### Added
- Orphan `master` branch with curated files from v1
- V2 handover document with decisions, file inventory, and implementation plan
- Code quality tooling: ruff, mypy, pre-commit hooks, GitHub Actions CI
- Upgraded langchain to 1.x with `langchain_classic` compatibility shim
- Pydantic v1 warning suppression for Python 3.14+
