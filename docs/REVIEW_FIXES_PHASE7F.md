# Deep Review Fix Plan: Phase 7f + Issue #52

**Date**: 2026-04-10
**Scope**: `fsbrowse.py`, `portscan.py`, `memdump.py`, `runner.py`, and their tests
**Total issues**: 18 findings across 4 modules (3 critical, 6 important, 9 minor)
**Estimated new tests**: ~30-40 across all fixes

---

## Dependency Graph

```
Task 1 (ANSI truncation) ──┬──> Task 4 (portscan duplicates) ──> Task 5 (portscan order)
                           │
Task 2 (memdump loss)      ├──> Task 10 (minor fixes)
                           │
Task 3 (runner lifecycle) ─┼──> Task 8 (child crash)
                           │──> Task 9 (double launch)
                           │
Task 6 (fsbrowse tiny)     │
Task 7 (memdump scroll)    │
                           │
                           └─��> Task 11 (test coverage) [blocked by all above]
```

Independent starting points: Tasks 1, 2, 3, 6, 7 can all be worked in parallel.

---

## Critical Fixes

### Fix 1: `set_region` ANSI truncation in fsbrowse and portscan

**Root cause**: `ScreenBuffer.set_region(row, col, width, text)` performs `text[:width].ljust(width)` which slices by character count, not visible width. ANSI escape codes (e.g., `\033[1m` = 4 invisible chars) consume slots, truncating styled text mid-escape-sequence.

**Affected locations**:

| File | Lines | Description |
|------|-------|-------------|
| `fsbrowse.py` | 243-246 | Header row with `BOLD`/`RESET` wrapping |
| `fsbrowse.py` | 277-295 | Left-pane entry rows with cursor highlight + style |
| `fsbrowse.py` | 300, 308-315 | Right-pane preview lines |
| `portscan.py` | 360-362 | `_render_port_cell` returns ANSI-styled cells |
| `portscan.py` | 439-450 | Grid compositing via `set_region` with `cell_width=8` |

**Fix strategy — fsbrowse**:

Replace per-column `set_region` compositing with full-line `set_line` construction. For each row:

1. Build the left-pane text at exactly `left_w` visible characters (pad/truncate plain text first).
2. Build the separator character.
3. Build the right-pane text at exactly `right_w` visible characters.
4. Wrap each segment with ANSI codes *after* fitting to width.
5. Concatenate and call `screen.set_line(row, full_line)`.

```python
# Example for entry row (lines 277-295):
label = f"  {icon} {entry.name}"
plain_label = f"{label:{left_w}}"[:left_w]  # Fit to width first
styled_label = f"{style}{plain_label}{RESET}" if style else plain_label
separator = "|"
# ... similar for right pane ...
screen.set_line(row, f"{styled_label}{separator}{right_text}")
```

**Fix strategy — portscan**:

Change `_render_port_cell` to return `(plain_text, style_prefix)` separately. Build each grid row as a single string:

```python
for row_idx in range(GRID_ROWS):
    row = grid_start_row + row_idx * 2
    parts: list[str] = [" " * grid_left]
    for col_idx in range(GRID_COLS):
        port_idx = row_idx * GRID_COLS + col_idx
        plain, style = self._render_port_cell(port, is_cursor)
        padded = f"{plain:{cell_width}}"
        parts.append(f"{style}{padded}{RESET}" if style else padded)
    screen.set_line(row, "".join(parts))
```

**Also fix**: `test_scanned_port_shows_type` (test_portscan.py:212-220) — assert on the specific grid row content, not `all_text`.

**Files modified**:
- `backend/src/recursive_neon/shell/programs/fsbrowse.py`
- `backend/src/recursive_neon/shell/programs/portscan.py`
- `backend/tests/unit/shell/test_portscan.py`

**Tests to add/fix**:
- Fix `test_scanned_port_shows_type` to assert on grid row
- Add test that styled grid cell text doesn't contain broken ANSI sequences

---

### Fix 2: memdump loss fires before player can confirm on last move

**Root cause**: `memdump.py:235-240` — when the final keystroke types the last character of a correct pattern and exhausts `moves_remaining`, `_check_loss()` fires inline, setting `phase = LOST`. Enter (free) can never be pressed.

**Fix approach**: Defer loss check. Remove `_check_loss()` from inside the typing handler. Instead, check at the *top* of `on_key` before processing the next keystroke, skipping the check if the key is Enter:

```python
def on_key(self, key: str) -> ScreenBuffer | None:
    s = self.state
    if s.phase in (Phase.WON, Phase.LOST):
        # ... existing win/loss handling ...

    if s.phase == Phase.PLAYING:
        # Deferred loss check: if budget exhausted, only Enter is free
        if s.moves_remaining <= 0 and key != "Enter":
            s.phase = Phase.LOST
            s.message = self._loss_message()
            return self._render()

        if key == "Enter":
            self._confirm_find()
            return self._render()
        elif key == "Backspace":
            # ...
        elif key == "Escape":
            # ...
        elif len(key) == 1 and key.isprintable():
            s.search += key
            s.moves_remaining -= 1
            s.message = ""
            # No _check_loss() here anymore
            return self._render()
    # ...
```

**Files modified**:
- `backend/src/recursive_neon/shell/programs/memdump.py`
- `backend/tests/unit/shell/test_memdump.py`

**Tests to add**:
- `test_last_move_correct_pattern_allows_confirm`: Type correct pattern using all remaining moves, then press Enter — should confirm, not lose.
- `test_zero_moves_non_enter_triggers_loss`: After moves hit 0, any non-Enter key triggers loss.
- `test_zero_moves_enter_still_works`: After moves hit 0 with correct pattern typed, Enter confirms.

---

### Fix 3: TUI runner `_run_child_inline` missing lifecycle hooks

**Root cause**: `runner.py:215-249` — the inline child loop omits two lifecycle hooks that the parent loop provides: `on_after_key` (lines 145-149 in parent) and `set_tui_launcher` (lines 91-92 in parent). This breaks nested TUI app launches (e.g., fsbrowse launching editor from within editor shell).

**Fix approach**:

```python
async def _run_child_inline(
    child_app: "TuiApp",
    raw_input: "RawInputSource",
    output: "RawOutputSink",
    width: int,
    height: int,
    child_done: asyncio.Event,
    send_screen: Callable | None = None,
    launch_child: Callable | None = None,  # NEW parameter
) -> None:
    try:
        # Inject launcher for nested children
        if launch_child is not None and hasattr(child_app, "set_tui_launcher"):
            child_app.set_tui_launcher(launch_child)

        screen = child_app.on_start(width, height)
        if screen is not None:
            _deliver_screen(screen, output, send_screen)

        while True:
            # ... existing key read / tick / resize logic ...

            result = child_app.on_key(key)
            if result is None:
                break
            _deliver_screen(result, output, send_screen)

            # Drain async post-key work (mirrors parent loop)
            on_after = getattr(child_app, "on_after_key", None)
            if on_after is not None:
                after_result = await on_after()
                if after_result is not None:
                    _deliver_screen(after_result, output, send_screen)
    finally:
        child_done.set()
```

Also pass `launch_child` from the parent's `_pending_child` check block into `_run_child_inline`.

**Files modified**:
- `backend/src/recursive_neon/shell/tui/runner.py`
- `backend/tests/unit/editor/test_issue_52_tui_in_shell.py`

**Tests to add**:
- `test_child_on_after_key_called`: Child with `on_after_key` has it drained after each keystroke.
- `test_child_receives_tui_launcher`: Child app gets `set_tui_launcher` called before `on_start`.
- `test_nested_child_launch`: Child launches a grandchild via `launch_child` — all three levels work.

---

## Important Fixes

### Fix 4: portscan duplicate port entry and misleading feedback

**portscan.py:273-286** — Add duplicate check in `_type_digit`:
```python
# After range validation, before accepting:
for i, existing in enumerate(s.sequence_slots):
    if i != s.seq_cursor and existing == val:
        s.message = f"Port {val} already in slot {i + 1}"
        return
```

**portscan.py:319** — Fix feedback calculation:
```python
in_answer = len(set(guess) & set(s.answer))
```

**Tests**: duplicate rejection message, feedback accuracy with partial matches.

---

### Fix 5: portscan order-sensitive win condition

**portscan.py:297** — Sort guess before comparing:
```python
if sorted(guess) == s.answer:
```

**Tests**: correct ports in wrong order → win.

---

### Fix 6: fsbrowse crash on tiny terminals

**fsbrowse.py:255-262** — Guard dimensions:
```python
content_rows = max(0, self.height - content_start - 2)
```

**fsbrowse.py:235** — Guard right pane:
```python
left_w = min(max(20, int(self.width * 0.4)), self.width - 2)
right_w = max(1, self.width - left_w - 1)
```

Add early return with "Terminal too small" message when `content_rows == 0` or `self.height < 5`.

**Tests**: `on_start(30, 5)`, `on_start(20, 3)`, `on_resize(20, 3)` — no crash.

---

### Fix 7: memdump scroll offset not clamped on resize

**memdump.py:244-247**:
```python
def on_resize(self, width: int, height: int) -> ScreenBuffer:
    self.width = width
    self.height = height
    max_scroll = max(0, NUM_ROWS - self._visible_rows())
    self.state.scroll_offset = min(self.state.scroll_offset, max_scroll)
    return self._render()
```

**Tests**: Scroll to bottom on small terminal, resize larger, verify scroll_offset clamped.

---

### Fix 8: TUI runner child crash killing parent

**runner.py** — Wrap inline child call:
```python
# In the parent's main loop, where _run_child_inline is awaited:
try:
    await _run_child_inline(...)
except Exception:
    import logging
    logging.getLogger(__name__).exception("child TUI app crashed")
```

**Tests**: Child raises in `on_key` / `on_start` — parent continues.

---

### Fix 9: TUI runner rapid double launch_child deadlock

**runner.py:77** — Guard the slot:
```python
async def launch_child(child_app: TuiApp) -> int:
    if _pending_child[0] is not None:
        raise RuntimeError("A child TUI app is already pending")
    done = asyncio.Event()
    _pending_child[0] = (child_app, done)
    await done.wait()
    return 0
```

**Tests**: Second `launch_child` while one is pending → `RuntimeError`.

---

## Minor Fixes (Task 10)

| # | File | Lines | Fix |
|---|------|-------|-----|
| 10a | `fsbrowse.py` | 47-53, 75-81 | Extract `_sorted_dir_first(children)` static method |
| 10b | `portscan.py` | 349 | Rename `grid_pixel_width` → `grid_char_width` |
| 10c | `memdump.py` | 167-171 | Fallback placement: check overlap with existing patterns |
| 10d | `memdump.py` | 88-109 | `from_patterns`: validate `offset + len(text) <= MEM_SIZE` |
| 10e | `memdump.py` | 419 | Hex separator: `hex_parts.append("")` for 2-space gap |
| 10f | `runner.py` | 108-149 vs 215-249 | Extract shared loop body (pairs with Fix 3) |
| 10g | `runner.py` | 89 | Store child exit code for future use |
| 10h | `test_issue_52_tui_in_shell.py` | 81-117 | Fix scheduling-dependent assertion in characterization test |

---

## Test Coverage Additions (Task 11)

### fsbrowse (82% → ~95%)

| Test | Description |
|------|-------------|
| `test_on_after_key_launches_editor` | Mock tui_launcher, press `e` on file, verify `on_after_key` calls launcher |
| `test_run_fsbrowse_entry_point` | Test `_run_fsbrowse` with mock context, verify path resolution |
| `test_run_fsbrowse_no_tui` | `_run_fsbrowse` returns 1 when `run_tui is None` |
| `test_render_tiny_terminal` | `on_start(30, 5)` — no crash, shows message |
| `test_preview_truncation_boundary` | File with exactly `content_rows` lines — no truncation indicator |

### portscan (97% → ~99%)

| Test | Description |
|------|-------------|
| `test_q_exits_from_sequence` | `q` in sequence phase returns None |
| `test_escape_exits_from_sequence` | `Escape` in sequence phase returns None |
| `test_feedback_accuracy` | Verify "N/M ports correct" value matches unique correct ports |
| `test_small_terminal_rendering` | `on_start(40, 12)` — no crash or overlap |
| `test_cursor_highlight_on_scanned_port` | Cursor on already-scanned port renders correctly |

### memdump (95% → ~99%)

| Test | Description |
|------|-------------|
| `test_multiple_match_offsets` | Search text at 2+ positions — all highlighted |
| `test_found_pattern_green_highlight` | Found patterns render with GREEN style |
| `test_escape_exits_from_won` | Escape on won screen returns None |
| `test_escape_exits_from_lost` | Escape on lost screen returns None |
| `test_confirm_already_found_pattern` | "Not a target pattern" message |
| `test_backspace_then_confirm` | Type "ROOT", backspace to "ROO", confirm — not found |

### TUI runner (3 → ~10)

| Test | Description |
|------|-------------|
| `test_eof_during_child` | `EOFError` in raw_input during child — parent survives |
| `test_child_on_after_key_called` | Child's `on_after_key` drained after each key |
| `test_child_receives_launcher` | Child gets `set_tui_launcher` before `on_start` |
| `test_nested_child_launch` | Child launches grandchild via launcher |
| `test_child_crash_parent_survives` | Child raises in `on_key` — parent continues |
| `test_double_launch_child_raises` | Second pending launch → `RuntimeError` |
| `test_characterization_assertion_fix` | Fix scheduling-dependent test assertion |

---

## Execution Order

Recommended order for minimal conflict and maximum parallelism:

1. **Parallel batch 1** (no dependencies):
   - Fix 1 (ANSI truncation) — largest change, touch rendering in 2 apps
   - Fix 2 (memdump loss) — isolated to memdump
   - Fix 3 (runner lifecycle) — isolated to runner
   - Fix 6 (fsbrowse tiny) — isolated to fsbrowse
   - Fix 7 (memdump scroll) — isolated to memdump

2. **Parallel batch 2** (after batch 1):
   - Fix 4 (portscan duplicates) — depends on Fix 1 (same file)
   - Fix 8 (child crash) — depends on Fix 3 (same file)
   - Fix 9 (double launch) — depends on Fix 3 (same file)

3. **Sequential**:
   - Fix 5 (portscan order) — after Fix 4
   - Fix 10 (minor) — after Fixes 1, 2, 3

4. **Final**:
   - Task 11 (test coverage) — after all fixes landed

**Run full test suite after each batch** to catch regressions.
