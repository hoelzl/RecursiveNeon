# Changelog

All notable changes to Recursive://Neon are documented here.

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
