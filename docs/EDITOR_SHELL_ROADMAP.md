# Editor-as-Game-Shell Roadmap

> **Status**: Planning handover, written 2026-06-12. Nothing in this
> document is implemented yet. Prerequisite reading:
> `docs/PARITY_HARNESS.md` (the verify-against-Emacs methodology this
> plan reuses), `docs/V2_HANDOVER.md` §Phase 8, `CLAUDE.md` rule 5
> (Emacs is the ground truth).

## 1. The goal

Two complementary outcomes, in the user's words:

1. **A fairly functional stand-alone terminal** — the game playable in
   a plain terminal window (today's CLI, and in Phase 8 an xterm.js
   browser terminal).
2. **The editor as a shell for the complete game** — the entire game
   playable *without leaving neon-edit*: integrated shells, dired for
   file management, TUI apps running in editor windows. Traditional
   CLI and (later, optional) GUI programs remain available alongside.

Strategic consequence worth keeping in mind: if neon-edit can host
everything, Phase 8's "desktop GUI with window manager" shrinks
dramatically — one fullscreen xterm.js pane running the editor *is* a
desktop, with editor windows as the window manager. GUI-native apps
(Phase 8 task 6) stop being load-bearing.

## 2. Where things stand (surveyed 2026-06-12)

### Standalone terminal stack — layers 1–2 done, no emulator of our own

- Shell is transport-agnostic (`shell/shell.py`, `InputSource`
  protocol); real CLI via `python -m recursive_neon.shell`; cooked +
  raw modes; TUI framework `shell/tui/` (`ScreenBuffer`, `TuiApp`
  protocol, `run_tui_app`) hosts six apps. Child TUI apps launch
  *inline* — only one consumer reads keys at a time (the issue-52 fix
  in `shell/tui/runner.py::_run_child_inline`).
- WebSocket side proven: `/ws/terminal` (`terminal.py` — session
  manager, raw mode, resize-on-connect protocol) plus a Python client
  (`wsclient/`, `--command` batch mode).
- **No terminal emulator exists in the product**: the CLI and wsclient
  delegate emulation to the user's real terminal. The only in-repo
  emulator is pyte, inside the parity harness. The browser terminal
  (xterm.js) is unstarted, as is the entire frontend.

### Editor shell (`M-x shell`) — comint, not a terminal emulator

`editor/shell_mode.py` is a faithful Emacs `shell-mode` equivalent:

- Prompt + editable input region, read-only history region, `M-p`/`M-n`
  history, TAB completion via the shell's own completer.
- ANSI **SGR colors** parsed into buffer attributes
  (`editor/ansi_parser.py::parse_ansi` → `TextAttr` runs); all non-SGR
  CSI sequences are stripped.
- Interactive programs (`chat`) suspend at `get_line()` into the
  minibuffer (`ShellBufferInput`, asyncio Future).
- TUI apps launched from the shell buffer take over the **full screen**
  via `editor.tui_launcher` → `launch_child`.

It cannot do cursor addressing or render a raw-mode app inside a
buffer — it is `shell-mode`, not `term`/`vterm`/`eat`. One `*shell*`
buffer only.

### Editor-as-game-shell, current coverage

- Game bridge (`editor/game_bridge.py`): `open-note`,
  `open-task-list`, `list-npcs`; find-file over the virtual FS; save
  event bus (`docs/GAME_EVENTS.md`).
- **No dired.** `shell/programs/fsbrowse.py` is a standalone
  fullscreen two-pane TUI file browser — useful as the reference for
  VFS access patterns, but not an editor mode.
- Editor host wiring (file I/O callbacks, path completion,
  `shell_factory`, game state) lives in `shell/programs/edit.py`.

## 3. The key architectural decision (made — do not relitigate)

**For the in-editor goal, build a TuiApp-in-window host, not a VT100
emulator.** Real Emacs needs `term`/`vterm` because external programs
speak escape-sequence byte streams over PTYs. This game has no PTYs:
every program is either structured `Output` text (already handled by
shell-mode) or a `TuiApp` that renders `ScreenBuffer`s directly. So
hosting a TUI app in an editor window means: blit the child's
`ScreenBuffer` (text + ANSI runs — `parse_ansi` already converts these
to buffer attributes) into a read-only attributed buffer shown in a
normal editor window, route keys to the child while its window is
selected, propagate the *window* size through the existing
`TuiApp.on_resize`. Far smaller and more robust than emulation, and it
reuses the entire existing rendering pipeline.

Real terminal emulation arrives for free where it's actually needed:
**xterm.js** on the browser side (Phase 8), speaking the existing
`/ws/terminal` protocol.

## 4. Roadmap

Ordered; each step is CLI-first and independently shippable.

### Step 1 — Dired (`C-x d`, `M-x dired`) — highest value, ~1–2 sessions

An Emacs dired-mode buffer over the **virtual filesystem** (never real
paths — `FILESYSTEM_SECURITY.md`).

- **The parity harness applies directly** — this is the big
  multiplier. Stage a real directory tree for Emacs (extend
  `parity/fixtures.py`: `staged_file` → a `staged_tree` variant) and
  identical VFS content for neon (`write_file_via_echo` + `mkdir`
  lines). Probe-first, exactly like scenarios 22–30: capture Emacs
  29.3's listing format, then the command battery.
- Scope for the first scenario set: buffer layout (` /path:` header
  line, `total used …` line, per-file lines), point motion (`n`/`p`),
  `RET` (visit file / descend into dir), `^` (up), `g` (revert),
  `d`/`u`/`x` (flag, unflag, execute deletions — with the
  `Delete N files? (yes or no)` flow), `+` (create-directory with
  prompt), `R` (rename → prompt), `C` (copy → prompt), `q` (quit
  window). Marks (`m`) and `D`-immediate can be a follow-up scenario.
- **Metadata design point** (decide while probing): Emacs lines look
  like `-rw-r--r-- 1 user user 1234 Jun 12 16:00 name`. `FileNode` has
  name/type/content (→ size) and `created_at`/`updated_at`
  (→ mtime-ish), but **no permissions/owner/group** — synthesize
  constants that fit the game fiction (e.g. `-rw-r--r-- 1 neon neon`
  for files, `drwxr-xr-x 2 neon neon` for dirs). Dates/owner will
  inherently diverge from the staged real tree, so expect
  `EXPECTED_DIVERGENCES = {…: {"body"}}` on listing checkpoints with
  the *structure* verified by unit tests (the scenario-28 Buffer-List
  precedent), OR consider a column-normalizing comparison. Probe
  first, then choose; document the choice in the scenario docstring.
- Implementation home: new `editor/dired.py` (mode `dired-mode`,
  indicator `Dired`, read-only buffer, buffer-local keymap with parent
  = global — the shell-mode keymap pattern). VFS access through the
  same callbacks `edit.py` already injects (extend the host wiring as
  needed; `fsbrowse.py` shows the service calls). Killing/reverting
  must re-list from the VFS, not cache.

### Step 2 — TuiApp window host — the "never leave the editor" enabler, ~2 sessions

Make `codebreaker`, `sysmon`, `portscan`, `fsbrowse`, `memdump`
playable in a split window instead of taking over the screen.

- A hosted-app buffer: each frame, write the child's `ScreenBuffer`
  rows + ANSI into the buffer via the attribute layer (the
  `BufferOutput`/`insert_string_attributed` machinery from shell-mode
  is the precedent); read-only; rendered by the normal window pipeline.
- Key routing: while the hosted buffer's window is **selected**, keys
  go to the child app; a prefix escape hatch returns to the editor
  (Emacs `term-mode` convention — probe what real `M-x term` uses,
  `C-c` prefix, before inventing one). When an unhosted window is
  selected, the app keeps rendering but receives nothing.
- Child size = the *window's* text area, not the screen; re-send
  `on_resize` on window-layout changes. Periodic apps (sysmon ticks)
  already use `editor.request_render()` / the `after_key` queue.
- Decide entry points: `M-x sysmon` style commands, and/or running a
  TUI app from `M-x shell` opens it in the other window instead of
  fullscreen (config variable; Emacs-style default to discuss).
- Not parity-verifiable (the apps are ours, not Emacs's): use unit
  tests + `tests/unit/editor/harness.py::EditorHarness`, which can
  inspect attributed screen rows (`test_mark_ring.py::_highlight_cols`
  shows the SGR-scraping pattern).

### Step 3 — Shell polish — small, can ride along with 1–2

- Multiple shells: `C-u M-x shell` prompts for a buffer name (Emacs
  behaviour); probe the exact prompt.
- `C-c C-c` (`comint-interrupt-subjob`) to cancel a running command —
  wire to the C-g/EOFError path `ShellBufferInput` already has.
- Optional: ERC-style `chat-mode` buffer per NPC instead of
  minibuffer `get_line` round-trips (nice, not load-bearing).

### Step 4 — Phase 8: xterm.js browser terminal

Per `V2_HANDOVER.md` §Phase 8 tasks 1–3: xterm.js → `/ws/terminal`
(same protocol as `wsclient`, including resize-on-connect), cooked +
raw modes in the browser. After steps 1–3 the browser gets **both**
experiences at once: a plain standalone terminal *and* the
editor-as-complete-environment running inside it. Re-evaluate Phase 8
tasks 4–6 (desktop chrome, GUI apps) afterwards — see §1.

## 5. Working conventions (carry over from the parity effort)

- **Probe first.** Throwaway `parity/probe_*.py` scripts against real
  Emacs (`GNU Emacs 29.3` locally and in CI) before implementing;
  delete probes before committing. Beware probe pitfalls already hit:
  settle between `send_text` and `RET`; Emacs resolves relative paths
  against its cwd (targets now launch with the staging dir as cwd).
- **Scenario numbering**: next is `scenario_31_*`. Update the counts +
  coverage table in `PARITY_HARNESS.md` with every scenario; baseline
  divergences in `EXPECTED_DIVERGENCES` with a docstring rationale.
  `COMPARE_HIGHLIGHTS = True` exists for attribute-level checks
  (scenario 30) — dired probably doesn't need it.
- **Gates before every commit** (from `backend/`):
  `../.venv/bin/pytest`, `ruff check`, `ruff format --check`, `mypy`;
  from repo root: `python -m parity.run` (full suite — shared-code
  fixes ripple). CI runs the parity job on a pinned ubuntu-24.04.
- **Command modules**: `default_commands.py` was split along seams
  (`isearch_commands.py`, `replace_commands.py`,
  `register_commands.py`). Dired and the window host should be their
  own modules from day one (`editor/dired.py`, `editor/app_host.py` or
  similar), imported from `default_commands.py` for registration.
- Editor structural note: the minibuffer is still a widget, not a
  buffer (the last open gap in `PARITY_HARNESS_REVIEW.md`) — dired's
  prompts all fit the widget; no need to touch this.
