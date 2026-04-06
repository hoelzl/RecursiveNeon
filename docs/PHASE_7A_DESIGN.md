# Phase 7a Design: Shell Buffer Completions

> **Date**: 2026-04-06
> **Status**: Design (pre-implementation)
> **Depends on**: Phase 6l (complete), Phase 6j shell-in-editor
> **Unlocks**: 7b (pipeline), 7c (tech debt), 7d (extensibility), 7e (game hooks)

## Overview

Phase 7a transforms the `*shell*` buffer from a demo into a first-class
interactive environment.  Five sub-items, in dependency order:

| Sub-item | Summary | Scope |
|----------|---------|-------|
| 7a-1 | Read-only regions | Buffer model |
| 7a-2 | Attributed text (ANSI colours in buffer) | Buffer model + rendering |
| 7a-3 | General `after_key` async bridge | Editor + runner |
| 7a-4 | Interactive programs in shell buffer | Shell mode + async bridge |
| 7a-5 | TUI app passthrough from shell buffer | Runner + shell mode |

### Design principles

1. **Zero cost for plain-text buffers.**  Most buffers (text files, scratch,
   help, tutorial) have no attributes and no read-only regions.  Every new
   mechanism must be lazily initialised and incur no overhead when absent.

2. **Reuse the rendering pipeline.**  The `StyleSpan` + `_style_text_rows`
   post-compose pass (Phase 6l-3) already handles priority-based styled
   overlays.  Buffer attributes feed into this pipeline as another span
   producer — no new rendering machinery required.

3. **Mutations stay in one place.**  Buffer has six core mutation primitives.
   Attribute maintenance is added *inside* those same primitives behind a
   `if self._line_attrs is not None` guard — no separate "sync" step that
   can drift.

4. **Undo round-trips attributes.**  Deleting attributed text captures the
   attributes in the undo record.  Re-inserting (undo) restores them.  The
   cycle `insert → undo → redo` preserves colours exactly.

5. **Interactive programs use cooperative async.**  Shell commands are
   spawned as `asyncio.Task`s.  `get_line` suspends the task via a
   `Future`; the minibuffer resolves it; `asyncio.sleep(0)` in
   `on_after_key` yields to the event loop so the task can resume before
   re-rendering.

---

## 1. Read-Only Regions (7a-1)

### Data model

```python
# buffer.py

@dataclass
class ReadOnlyRegion:
    """A range of text that cannot be modified."""
    start: Mark   # tracked, kind="left"
    end: Mark     # tracked, kind="left"

class Buffer:
    _read_only_regions: list[ReadOnlyRegion]   # default: []
```

Start and end marks are **tracked** (via `track_mark`), so they
automatically adjust as surrounding text is inserted or deleted.  Both
are `kind="left"` so that text inserted exactly at a boundary goes
*outside* the protected region.

### API

```python
class Buffer:
    def add_read_only_region(self, start: Mark, end: Mark) -> ReadOnlyRegion:
        """Mark a range as read-only.  Returns the region for later removal."""

    def remove_read_only_region(self, region: ReadOnlyRegion) -> None:
        """Remove a previously-added read-only region."""

    def clear_read_only_regions(self) -> None:
        """Remove all read-only regions."""

    def is_read_only_at(self, line: int, col: int) -> bool:
        """True if position falls inside any read-only region."""

    def _check_read_only_range(self, start_line: int, start_col: int,
                                end_line: int, end_col: int) -> bool:
        """True if any part of the range overlaps a read-only region."""
```

### Enforcement points

Read-only checks are added at the **public mutation API** — the level
where undo recording and `read_only` flag checks already live:

| Method | Check |
|--------|-------|
| `insert_char` | `is_read_only_at(point)` |
| `insert_string` | `is_read_only_at(point)` |
| `delete_char_forward` | `is_read_only_at(point)` |
| `delete_char_backward` | `is_read_only_at(point.line, point.col - 1)` (the char being deleted) |
| `delete_region` | `_check_read_only_range(start, end)` |

On violation, the method sets `self._read_only_error = True` and returns
early (same pattern as the existing `self.read_only` whole-buffer flag).
The editor translates this into a `"Text is read-only"` message (distinct
from the whole-buffer `"Buffer is read-only"`).

The six internal primitives (`_insert_within_line`, `_insert_newline`,
`_delete_within_line_forward/backward`, `_join_line_forward/backward`)
are **not** guarded — they trust the public API to have checked.

### Shell-mode usage

After each command completes (`execute_shell_command`):

```python
buf.clear_read_only_regions()
buf.add_read_only_region(
    Mark(0, 0, kind="left"),     # buffer start
    state.input_start,            # already tracked, kind="left"
)
```

One region covers all historical output + prompts.  It grows
automatically as `input_start` moves forward after each command.

### Why mark-pair regions (not a per-character property)

Read-only protection is inherently *range-based*: "everything before the
prompt is frozen."  Storing a per-character `read_only` flag would waste
memory on the same boolean for thousands of characters, and would need
to be maintained in every mutation primitive — the same cost as
attributes, but for a simpler problem.  Mark-pair regions are O(regions)
to check (typically 1-2 regions in a shell buffer) and leverage the
existing mark-tracking infrastructure.

---

## 2. Text Attributes (7a-2)

### TextAttr — the value type

```python
# editor/text_attr.py  (new file)

@dataclass(frozen=True, slots=True)
class TextAttr:
    """Visual attributes for a character, modelled after terminal SGR."""
    fg: int | None = None       # 256-colour index, None = terminal default
    bg: int | None = None       # 256-colour index, None = terminal default
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False

    def to_sgr(self) -> str:
        """Convert to ANSI SGR escape sequence.  Empty string if default."""

    _sgr_cache: str | None = field(default=None, repr=False, compare=False)
```

Frozen and slotted for cheap equality checks and compact memory.
The `to_sgr` result is cached on first call (via `object.__setattr__`
on the frozen instance) because the same attr is shared across many
characters and rendered every frame.

256-colour covers standard (0-7), bright (8-15), and extended (16-255)
palette entries — sufficient for all common shell output.  True colour
(24-bit) can be added later by widening `fg`/`bg` to `int | tuple[int,int,int] | None`
without changing any other code.

### Buffer storage

```python
# buffer.py

class Buffer:
    _line_attrs: list[list[TextAttr | None]] | None = None
```

- **`None`** (default): no attribute layer.  All existing buffers behave
  exactly as before.  Zero overhead.
- **Not `None`**: parallel to `self.lines`.  `_line_attrs[i]` has the same
  length as `self.lines[i]`.  Each element is a `TextAttr` for that
  character position, or `None` for default styling.

### Enabling the attribute layer

```python
class Buffer:
    def enable_attrs(self) -> None:
        """Lazily initialise the attribute layer (all positions default)."""
        if self._line_attrs is None:
            self._line_attrs = [[None] * len(line) for line in self.lines]
```

Called once by shell-mode's `setup_shell_buffer` (or any future mode that
needs per-character styling).  Never called for plain-text buffers.

### Attributed insertion

```python
class Buffer:
    def insert_string_attributed(
        self, runs: list[tuple[str, TextAttr | None]]
    ) -> None:
        """Insert text with per-character attributes at point.

        Each run is a ``(text, attr)`` pair.  ``attr=None`` means default
        styling.  Enables the attribute layer if not already enabled.

        Undo records capture the attributes so that undo/redo round-trips
        correctly.
        """
```

This is the primary entry point for attributed insertion.  It:

1. Calls `enable_attrs()` if needed.
2. Builds a flat `(full_text, attrs_list)` from the runs.
3. Delegates to `insert_string(full_text, _attrs=attrs_list)` — a new
   internal-only keyword argument on the existing method (see below).

The public `insert_string(s)` continues to work unchanged for plain text.
When `_line_attrs` is not `None`, plain insertions fill the corresponding
attr positions with `None` (default).

### Mutation primitive changes

Each of the six primitives gains an `# --- attrs ---` section, guarded
by `if self._line_attrs is not None`.  The logic mirrors the text
operation exactly:

| Primitive | Attr operation |
|-----------|---------------|
| `_insert_within_line(text)` | Splice attr list at `col`: `attrs[ln] = attrs[ln][:col] + new_attrs + attrs[ln][col:]` |
| `_insert_newline()` | Split attr list at `col`: `attrs[ln+1] = attrs[ln][col:]`, `attrs[ln] = attrs[ln][:col]` |
| `_delete_within_line_forward()` | `del attrs[ln][col]` |
| `_delete_within_line_backward()` | `del attrs[ln][col-1]` |
| `_join_line_forward()` | `attrs[ln].extend(attrs[ln+1]); del attrs[ln+1]` |
| `_join_line_backward()` | `attrs[ln-1].extend(attrs[ln]); del attrs[ln]` |

For `delete_region` (multi-line): the same slice/delete pattern as for
`self.lines`, applied to `self._line_attrs`.

Where does `new_attrs` come from for insertions?  The `_insert_within_line`
primitive is extended with an optional `_attrs` parameter:

```python
def _insert_within_line(self, text: str, *, _attrs: list[TextAttr | None] | None = None) -> None:
```

When `_attrs` is `None` and the layer is active, `[None] * len(text)` is
used (default styling).  When `_attrs` is provided, it must have the same
length as `text`.

### Undo integration

**`UndoDelete` grows an optional `attrs` field:**

```python
@dataclass(frozen=True)
class UndoDelete:
    line: int
    col: int
    text: str
    attrs: tuple[tuple[TextAttr | None, ...], ...] | None = None
```

`attrs` is a tuple of per-line attr tuples, parallel to `text.split('\n')`.
When `None`, the buffer had no attribute layer at deletion time.

**Capture path** (in `delete_region` and single-char deletions):

```python
# Before deletion, capture attrs for the affected range
captured_attrs = self._capture_line_attrs(start_line, start_col, end_line, end_col)
# ... perform deletion ...
self.undo_list.append(UndoDelete(line, col, deleted_text, attrs=captured_attrs))
```

```python
def _capture_line_attrs(self, sl, sc, el, ec) -> tuple[tuple[TextAttr | None, ...], ...] | None:
    """Capture attrs for a range.  Returns None if no attr layer."""
    if self._line_attrs is None:
        return None
    # Extract per-line attr slices, same structure as text.split('\n')
    ...
```

**Restore path** (in `Buffer.undo`, when processing `UndoDelete`):

```python
elif isinstance(entry, UndoDelete):
    self.point.move_to(entry.line, entry.col)
    self._undo_recording = False
    self.insert_string(entry.text, _attrs=entry.attrs)  # restores attributes
    self._undo_recording = True
    reverse.append(UndoInsert(entry.line, entry.col, self.point.line, self.point.col))
```

When `insert_string` receives `_attrs`, it distributes the per-line attrs
to the `_insert_within_line` calls.

**Round-trip correctness:**

```
insert_string_attributed([("hello", Red)]) →
    undo_list: UndoInsert(0,0, 0,5)
undo() →
    delete_region(0:0, 0:5) → captured attrs = ((Red,Red,Red,Red,Red),)
    undo_list: UndoDelete(0, 0, "hello", attrs=((Red,Red,Red,Red,Red),))
undo() again (redo) →
    insert_string("hello", _attrs=((Red,Red,Red,Red,Red),))
    text AND attrs are fully restored ✓
```

### ANSI parser

```python
# editor/ansi_parser.py  (new file)

def parse_ansi(text: str) -> tuple[str, list[list[TextAttr | None]]]:
    """Parse ANSI-encoded text into plain text + per-line attr lists.

    Returns (plain_text, line_attrs) where line_attrs[i] has the same
    length as plain_text.split('\\n')[i].
    """
```

The parser is a simple state machine:
1. Walk the input character by character.
2. When `\033[` is encountered, consume the SGR parameter string up to
   the terminating letter.
3. Update the "current attr" state based on the SGR codes (reset, fg, bg,
   bold, etc.).
4. Non-escape characters are appended to the output with the current attr.

This replaces `strip_ansi` in `BufferOutput.write` / `writeln` / `error`.
The old `strip_ansi` function stays for non-buffer uses.

### Rendering — buffer attrs as StyleSpans

Buffer attributes are rendered through the **existing** `StyleSpan` +
`_style_text_rows` pipeline.  No new rendering machinery.

A new method in `view.py`:

```python
def _compute_buffer_attr_spans(
    self, win: Window, text_spans: list[StyleSpan]
) -> None:
    """Append StyleSpans from buffer attributes for visible lines."""
    buf = win.buffer
    if buf._line_attrs is None:
        return
    text_h = win.text_height
    for row in range(text_h):
        line_idx = win.scroll_top + row
        if line_idx >= buf.line_count:
            break
        line_attrs = buf._line_attrs[line_idx]
        screen_row = win._top + row
        # Convert per-character attrs into runs of identical attr
        runs = _attrs_to_runs(line_attrs, win._width)
        for col, width, attr in runs:
            if attr is None:
                continue  # default styling, no span needed
            screen_col = win._left + col
            # Clip to window bounds
            win_right = win._left + win._width
            if screen_col >= win_right:
                continue
            clipped_width = min(width, win_right - screen_col)
            text_spans.append(StyleSpan(
                row=screen_row,
                col=screen_col,
                width=clipped_width,
                style=attr.to_sgr(),
                priority=_BUFFER_ATTR_PRIORITY,  # = 10
            ))
```

Called from `_render_window`, right before `_compute_highlight_spans`.
Since buffer attrs are priority 10 and isearch highlights are priority
20/25, search highlights correctly override buffer colours.

**Why this works well:**
- Zero changes to `ScreenBuffer`, `set_line`, `set_region`, or `render_ansi`.
- Composition with isearch/query-replace highlights is automatic.
- Future syntax highlighting (7d) would also produce spans at priority 10.
- Window splits work correctly — spans use screen coordinates.

### Helper: `_attrs_to_runs`

```python
def _attrs_to_runs(
    attrs: list[TextAttr | None], max_width: int
) -> list[tuple[int, int, TextAttr | None]]:
    """Convert per-character attrs to (col, width, attr) runs.

    Merges adjacent characters with identical attrs into single runs
    for efficient span generation.  Caps at max_width characters.
    """
```

This is a small utility (10-15 lines) that collapses `[None, None, Red,
Red, Red, None]` into `[(0, 2, None), (2, 3, Red), (5, 1, None)]`.
Only non-`None` runs produce `StyleSpan`s.

---

## 3. General After-Key Async Bridge (7a-3)

### Current state

`Editor._pending_async` holds a single `Callable[[], Awaitable[None]]`.
`EditorView.on_after_key` awaits it, then re-renders.  Only one callback
can be pending at a time.

### New design

```python
# editor.py

class Editor:
    _after_key_queue: list[Callable[[], Awaitable[None]]]

    def after_key(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Queue an async callback to run after the current keystroke."""
        self._after_key_queue.append(callback)
```

`_pending_async` is replaced entirely by `_after_key_queue`.  Shell
mode's `_comint_send_input` changes from
`editor._pending_async = _execute` to `editor.after_key(_execute)`.

### Runner integration

```python
# view.py

async def on_after_key(self) -> ScreenBuffer | None:
    queue = self.editor._after_key_queue
    if not queue:
        return None
    changed = False
    while queue:
        cb = queue.pop(0)
        try:
            await cb()
            changed = True
        except Exception as e:
            self.editor.message = f"Error in after-key callback: {e}"
            changed = True
    # Yield to the event loop so that any asyncio.Tasks that became
    # runnable during callback execution (e.g., a Future was resolved)
    # can make progress before we re-render.
    await asyncio.sleep(0)
    # Check for render requests from background tasks
    if self.editor._render_requested:
        self.editor._render_requested = False
        changed = True
    if changed:
        self._tree.active.sync_from_buffer()
        return self._render()
    return None
```

Key behaviours:
- **FIFO order**: callbacks execute in queue order.
- **Error isolation**: a failing callback logs to the message area but
  does not prevent subsequent callbacks from running.
- **Event loop yield**: `await asyncio.sleep(0)` lets background tasks
  (spawned by 7a-4) run before re-rendering.  This is the bridge between
  the synchronous keystroke loop and cooperative async.
- **Render coalescing**: multiple callbacks produce a single re-render.

### Background task support

For interactive programs (7a-4), callbacks may spawn `asyncio.Task`s
that outlive a single `on_after_key` invocation.  These tasks signal
the need for a re-render via:

```python
class Editor:
    _render_requested: bool = False

    def request_render(self) -> None:
        """Signal that the display needs updating (called from background tasks)."""
        self._render_requested = True
```

The runner checks `_render_requested` after each `asyncio.sleep(0)` yield.

Additionally, in `run_tui_app`, after every `get_key()` return (which is
an event-loop yield point where tasks can run), check and flush render
requests:

```python
# runner.py — inside the main loop, after get_key():
if hasattr(app, '_check_render_request'):
    render = app._check_render_request()
    if render is not None:
        _deliver_screen(render, output, send_screen)
```

This ensures that when a background task (like `chat` producing a
response) modifies the buffer while the runner is idle waiting for a
keystroke, the update is displayed immediately after the next key press
(or, in the future when 7c-1 `on_tick` lands, on the next tick).

---

## 4. Interactive Programs in Shell Buffer (7a-4)

### Problem

`ShellBufferInput.get_line()` currently raises `EOFError`.  Interactive
programs like `chat` cannot run from the shell buffer.

### Design: Future-based suspension

```python
# editor/shell_mode.py

class ShellBufferInput:
    def __init__(self, editor: Editor, buf: Buffer, state: ShellState):
        self._editor = editor
        self._buf = buf
        self._state = state

    async def get_line(self, prompt: str, *, complete: bool = True,
                       history_id: str | None = None) -> str:
        # 1. Flush any pending output before showing the prompt
        self._flush_output()

        # 2. Create a Future for the result
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()

        # 3. Pop the editor minibuffer
        def on_submit(result: str) -> None:
            if not future.done():
                future.set_result(result)

        def on_cancel() -> None:
            if not future.done():
                future.set_exception(KeyboardInterrupt())

        self._editor.start_minibuffer(
            prompt, on_submit,
            # Wire C-g to raise KeyboardInterrupt
        )
        # Override minibuffer's C-g handler to call on_cancel
        mb = self._editor.minibuffer
        original_cancel = mb.key_handlers.get("C-g")
        def cancel_handler(key: str) -> str | None:
            on_cancel()
            if original_cancel:
                return original_cancel(key)
            return "cancel"
        mb.key_handlers["C-g"] = cancel_handler

        # 4. Await the Future — this suspends the Task
        return await future

    def _flush_output(self) -> None:
        """Drain BufferOutput and insert into the buffer."""
        text = self._state.output.drain()
        if not text:
            return
        buf = self._buf
        # Insert with attrs (if ANSI parsing is enabled)
        plain, line_attrs = parse_ansi(text)
        if plain:
            runs = _plain_and_attrs_to_runs(plain, line_attrs)
            buf.insert_string_attributed(runs)
        self._state.input_start.move_to(buf.point.line, buf.point.col)
```

### Execution model

Shell command execution changes from synchronous-in-`on_after_key` to
a spawned `asyncio.Task`:

```python
# editor/shell_mode.py — _comint_send_input

async def _execute():
    try:
        await execute_shell_command(buf, state, input_text)
    except Exception as e:
        buf.insert_string(f"\nError: {e}\n")
    finally:
        editor.request_render()

# Spawn as a Task — don't await directly
import asyncio
editor.after_key(lambda: _spawn_shell_task(editor, _execute))

async def _spawn_shell_task(editor: Editor, coro_fn):
    """Spawn a shell command as a background Task."""
    task = asyncio.create_task(coro_fn())
    editor._background_tasks.append(task)
```

**Why Task and not direct await?**

If `execute_shell_command` calls `get_line`, the `get_line` awaits a
Future.  If this were directly awaited in `on_after_key`, the runner
would be blocked — it couldn't process the keystrokes the user types
into the minibuffer to resolve the Future.  Deadlock.

Spawning as a Task decouples the shell command's lifetime from
`on_after_key`.  The task suspends at `await future`, control returns to
the runner, the runner processes keystrokes, the minibuffer resolves the
Future, and the task resumes at the next event loop yield.

### Output flushing

**Problem**: `execute_shell_command` currently drains output *after*
`shell.execute_line` returns.  For interactive programs, `execute_line`
doesn't return until the program exits — output produced mid-session
stays buffered indefinitely.

**Solution**: flush output *before each `get_line` call* (in
`ShellBufferInput._flush_output`).  This ensures that:
- `chat`'s welcome message appears before the first prompt.
- Each NPC response appears before the next input prompt.
- `ls` output appears immediately (no `get_line` called, so
  `execute_shell_command` drains at the end as before).

The `execute_shell_command` function still does a final drain after
`execute_line` returns, catching any trailing output.

### Cancellation

When the user presses `C-g` in the minibuffer during `get_line`:
1. The `on_cancel` callback sets a `KeyboardInterrupt` on the Future.
2. The Task's `await future` raises `KeyboardInterrupt`.
3. The `chat` program catches `KeyboardInterrupt` and exits cleanly.
4. `execute_shell_command`'s `finally` block appends the exit prompt.

### Background task lifecycle

```python
class Editor:
    _background_tasks: list[asyncio.Task]
```

Tasks are weakly tracked for cleanup.  On editor exit (`running = False`),
all pending tasks are cancelled.  Completed tasks are pruned during
`on_after_key`.

---

## 5. TUI App Passthrough (7a-5)

### Problem

`codebreaker`, `sysmon`, and `edit` are TUI apps that require raw-mode
input.  When run from the shell buffer (M-x shell → `codebreaker`), they
need to take over the screen and raw input, then return control to the
editor.

### Design: Nested `run_tui_app` via injected launcher

The TUI runner injects a **child launcher callback** into the app:

```python
# shell/tui/runner.py

async def run_tui_app(app, raw_input, output, *, ...):
    # Create a launcher that captures the runner's resources
    async def launch_child(child_app: TuiApp) -> int:
        """Run a nested TUI app with the same I/O resources."""
        return await run_tui_app(
            child_app, raw_input, output,
            width=width, height=height,
            send_screen=send_screen,
            # No enter_raw/exit_raw — parent is already in raw mode
        )

    # Inject into the app if it supports it
    if hasattr(app, 'set_tui_launcher'):
        app.set_tui_launcher(launch_child)

    # ... rest of runner loop unchanged ...
```

The EditorView stores and exposes the launcher:

```python
# editor/view.py

class EditorView:
    _tui_launcher: Callable[[TuiApp], Awaitable[int]] | None = None

    def set_tui_launcher(self, launcher: Callable[[TuiApp], Awaitable[int]]) -> None:
        self._tui_launcher = launcher
        # Also expose on the editor for shell-mode access
        self.editor.tui_launcher = launcher
```

```python
# editor/editor.py

class Editor:
    tui_launcher: Callable | None = None
```

### Execution flow

When a TUI command is submitted in the shell buffer:

```
User types "codebreaker" → Enter
  → _comint_send_input → spawns execute_shell_command as Task
  → execute_shell_command → shell.execute_line("codebreaker")
  → codebreaker program handler → ctx.run_tui(CodeBreakerApp())
  → ctx.run_tui calls editor.tui_launcher(CodeBreakerApp())
  → launch_child → run_tui_app(CodeBreakerApp(), raw_input, ...)
      Child takes over:
        → child.on_start() → screen delivered
        → child keystroke loop runs (same raw_input)
        → child.on_key(key) → returns None → child exits
      → run_tui_app returns
  → execute_shell_command continues (drain output, show prompt)
  → editor.request_render()
  → editor re-renders with restored screen
```

**Why this works with asyncio:**

The child `run_tui_app` is awaited inside the parent's `on_after_key`
(via the spawned Task).  While the child runs:
- The child's `await raw_input.get_key()` yields to the event loop.
- The parent's `await raw_input.get_key()` is *not* being awaited (the
  parent runner is blocked inside `on_after_key`).
- There is no contention on `raw_input` — only one reader at a time.

When the child exits, the parent task resumes, `execute_shell_command`
continues, and the editor re-renders.

### TUI command detection

Shell-mode needs to know which commands are TUI apps to set up the
correct `ctx.run_tui`:

```python
# editor/shell_mode.py

_TUI_COMMANDS = {"codebreaker", "sysmon", "edit"}
```

When `execute_shell_command` runs, it sets `ctx.run_tui` to a function
that delegates to `editor.tui_launcher`:

```python
async def execute_shell_command(buf, state, command):
    # Set up the run_tui bridge if launcher is available
    if editor.tui_launcher:
        async def run_tui_bridge(app):
            return await editor.tui_launcher(app)
        # Inject into the ProgramContext somehow
        ...
```

The exact wiring depends on how `ProgramContext` provides `run_tui`.
The cleanest approach: shell-mode's `Shell` instance gets its `run_tui`
factory set to the bridge function at setup time:

```python
# In setup_shell_buffer, after the shell is created:
def make_run_tui(raw_input_source):
    """Factory that creates a run_tui for the shell buffer context."""
    async def run_tui(app):
        if editor.tui_launcher:
            return await editor.tui_launcher(app)
        raise RuntimeError("TUI apps not available in this context")
    return run_tui
shell._make_run_tui = make_run_tui
```

### Edge cases

- **Nested `edit` from shell-in-editor**: Valid.  The nested editor is a
  fresh `EditorView` with its own buffer list.  It does *not* get a
  `shell_factory` by default, preventing infinite M-x shell recursion.
  If needed, explicitly enabling it is a user choice.

- **Child app crash**: `run_tui_app` wraps the child loop in try/finally.
  If the child raises, control returns to the parent, which re-renders.
  The error is shown in the editor message area.

- **Screen restoration**: No explicit save/restore needed.  The editor
  calls `self._render()` after the Task completes, which redraws the
  entire screen fresh.

---

## 6. Integration: How the Pieces Compose

### Shell buffer lifecycle

```
1. M-x shell → setup_shell_buffer()
   - Creates Shell, BufferOutput, ShellBufferInput, ShellState
   - Enables attrs on buffer: buf.enable_attrs()
   - Inserts welcome banner + first prompt (with attrs from ANSI)
   - Adds read-only region: [(0,0), input_start)
   - Installs keymap (Enter, M-p, M-n, Tab)
   - Injects tui_launcher bridge into the shell

2. User types "ls" → Enter
   - _comint_send_input: extract input, spawn Task
   - Task: execute_shell_command("ls")
     - shell.execute_line("ls") → ls program runs
     - BufferOutput captures ANSI output
     - After execute_line returns: flush output
       - parse_ansi(raw_output) → (plain, attrs)
       - insert_string_attributed(runs) → text + colours in buffer
     - Insert new prompt (with attrs)
     - Move input_start past prompt
     - Update read-only region
   - editor.request_render() → screen updated

3. User types "chat npc_001" → Enter
   - Task: execute_shell_command("chat npc_001")
     - shell.execute_line("chat npc_001") → chat handler starts
     - chat outputs welcome message → BufferOutput captures
     - chat calls ctx.get_line("> ") →
       - ShellBufferInput._flush_output() → welcome text appears in buffer
       - Future created, minibuffer opened
       - Task suspends at await future
     - Runner continues processing keystrokes (user types in minibuffer)
     - User types "hello" → Enter → minibuffer resolves Future
     - asyncio.sleep(0) in on_after_key → Task resumes
     - chat processes "hello", calls LLM, outputs response
     - chat calls ctx.get_line("> ") again → response flushed, new prompt
     - ...cycle continues until "/exit"
   - After chat exits: final flush, new shell prompt, update read-only region

4. User types "codebreaker" → Enter
   - Task: execute_shell_command("codebreaker")
     - shell.execute_line("codebreaker") → codebreaker handler
     - ctx.run_tui(CodeBreakerApp()) → editor.tui_launcher(app)
     - Nested run_tui_app starts:
       - Child takes over screen + raw input
       - User plays the game
       - User presses 'q' → child exits
     - run_tui_app returns → Task resumes
     - Flush output, show new prompt, update read-only region
   - editor.request_render() → editor redraws fully
```

### Rendering pipeline (updated)

```
EditorView._render()
  → _compute_layout()                    # assign screen regions to windows
  → for each window:
      _render_window(win, screen, ...)   # write plain text to ScreenBuffer
        → _compute_buffer_attr_spans()   # NEW: buffer attrs → StyleSpan (priority 10)
        → _compute_highlight_spans()     # isearch/qr → StyleSpan (priority 20/25)
  → _render_dividers()                   # vertical split lines
  → _style_text_rows(screen, spans)      # apply all StyleSpans (unchanged)
  → _style_modeline_rows(screen, ...)    # modeline ANSI (unchanged)
  → _render_message_line()               # minibuffer / message (unchanged)
```

### Priority composition table

| Priority | Source | Wins over |
|----------|--------|-----------|
| 10 | Buffer attributes (ANSI colours) | nothing |
| 20 | Isearch/query-replace: non-current match | buffer attrs |
| 25 | Isearch/query-replace: current match | non-current match |
| 30 | Region/active mark (future) | all search highlights |
| 40 | Cursor line highlight (future) | everything |

Higher priority wins per-cell.  A search match inside coloured shell
output correctly shows the search highlight, not the shell colour.

---

## 7. Implementation Order

The sub-items have a clear dependency graph:

```
7a-1 (read-only regions)     independent
7a-2 (text attributes)       independent
7a-3 (async bridge)          independent
7a-4 (interactive programs)  depends on 7a-2 (ANSI parsing) + 7a-3 (async bridge)
7a-5 (TUI passthrough)       depends on 7a-3 + 7a-4
```

Recommended implementation order:

1. **7a-1** — Small and self-contained.  Adds read-only region
   infrastructure to Buffer.  ~30 tests.
2. **7a-3** — Replace `_pending_async` with the queue + `asyncio.sleep(0)`
   + `request_render`.  Small diff, unlocks 7a-4.  ~15 tests.
3. **7a-2** — The largest sub-item.  `TextAttr`, attr layer on Buffer,
   ANSI parser, undo integration, rendering via StyleSpan.  ~40 tests.
4. **7a-4** — Future-based `get_line`, output flushing, Task spawning.
   Depends on 7a-2 (ANSI parsing for output) and 7a-3 (async bridge).
   ~20 tests.
5. **7a-5** — Injected launcher, nested `run_tui_app`.  Depends on 7a-3
   and 7a-4.  ~10 tests.

Each sub-item is a standalone commit.

---

## 8. Files Modified

| Sub-item | Files |
|----------|-------|
| 7a-1 | `buffer.py` (regions API + enforcement), `shell_mode.py` (apply region after command) |
| 7a-2 | `text_attr.py` (new), `ansi_parser.py` (new), `buffer.py` (attr layer + mutations), `undo.py` (UndoDelete.attrs), `view.py` (attr span producer), `shell_mode.py` (use parse_ansi) |
| 7a-3 | `editor.py` (queue + request_render), `view.py` (on_after_key rewrite), `shell_mode.py` (use after_key) |
| 7a-4 | `shell_mode.py` (ShellBufferInput rewrite, flush, Task spawning) |
| 7a-5 | `runner.py` (launcher injection), `view.py` (set_tui_launcher), `editor.py` (tui_launcher field), `shell_mode.py` (bridge) |

New test files:
- `test_read_only_regions.py`
- `test_text_attr.py`
- `test_ansi_parser.py`
- `test_buffer_attrs.py`
- `test_async_bridge.py`
- `test_shell_buffer_interactive.py`
- Extensions to: `test_shell_mode.py`, `test_undo.py`, `test_view.py`

---

## 9. Open Questions

1. **Attr storage: per-character list vs run-length encoding?**
   Decision: per-character `list[TextAttr | None]`.  Simpler to splice
   during mutations.  Shell output lines rarely exceed 200 chars, so
   memory is not a concern.  The `_attrs_to_runs` helper in the renderer
   collapses them to runs for efficient `StyleSpan` generation.  If
   profiling shows this is slow, `LineAttrs` can be swapped to RLE
   internally without changing any external API.

2. **True colour (24-bit) support?**
   Deferred.  256-colour covers all common shell output.  `TextAttr.fg/bg`
   can be widened to `int | tuple[int,int,int] | None` later without
   affecting any code outside `TextAttr.to_sgr()`.

3. **Should `BufferOutput` bypass `strip_ansi` immediately or keep it as
   a fallback?**
   Decision: `BufferOutput` switches to `parse_ansi` when the buffer has
   an attr layer (`buf._line_attrs is not None`).  When it doesn't (which
   shouldn't happen in practice for shell buffers, but guards against
   misconfiguration), fall back to `strip_ansi`.

4. **Read-only region error reporting — message area or exception?**
   Decision: set a flag (`_read_only_error`) and return early.  The
   editor's key dispatch checks the flag after command execution and
   shows `"Text is read-only"` in the message area.  Same pattern as
   the existing `read_only` whole-buffer flag.  No exceptions.

5. **Task cleanup on editor exit?**
   Decision: `Editor.shutdown()` method (called from `EditorView` on exit)
   cancels all `_background_tasks`.  The tasks' `finally` blocks handle
   cleanup (e.g., resetting shell state).
