"""
dired-mode — an Emacs dired equivalent over the virtual filesystem.

A dired buffer is a read-only directory listing the user navigates and
operates on with single-key commands, mirroring GNU Emacs 29.3 (verified
against the parity probes of 2026-06-12; see parity scenarios 31+):

    n / p / SPC   move between lines, landing on the filename column
    RET / e / f   visit the file or descend into the directory at point
    ^             visit the parent directory, point on the child's line
    g             re-read the directory (marks and point preserved)
    d / u         flag for deletion / unflag (mark char in column 0)
    x             delete flagged entries after a yes-or-no confirm
    +             create a directory
    R / C         rename (move) / copy the entry at point
    q             quit-window

The editor knows nothing about the virtual filesystem: all access goes
through a :class:`DiredProvider` injected by the hosting environment as
``editor.dired_provider`` (the ``save_callback``/``open_callback``
pattern — see ``shell/programs/edit.py``).

Layout notes (all verified against Emacs 29.3 ``-Q``):

* Header line ``  /path/to/dir: (N available)`` — Emacs 29's
  ``dired-free-space`` default ``'first`` appends the free space to the
  header instead of printing ls's ``total used`` line.
* ``.`` and ``..`` entries precede the real entries (``ls -al``).
* The VFS has no permissions, owners or link counts, so they are
  synthesized to fit the game fiction: ``-rw-r--r--``/``drwxr-xr-x``,
  owner and group ``neon``, link count 1 for files and 2 + number of
  subdirectories for directories, size 4096 for directories. Free space
  is the constant :data:`DIRED_FREE_SPACE`.
* Newly created/renamed/copied entries are inserted *at point's line*
  (Emacs's ``dired-add-entry``), aligned to the listing's current grid
  (``dired-align-file``); a wider value stretches only that row until
  ``g`` re-lists. Like real dired, lines are therefore re-parsed by
  their date-stamp shape, not by fixed columns. Copies are marked ``C``
  (``dired-keep-marker-copy``); renames keep the old mark.

Documented deviations from GNU Emacs (cheaper than fidelity, see
CLAUDE.md rule 5):

* Mark/flag changes are not undoable (the listing is rewritten outside
  the undo system).
* ``dired`` on a non-directory path shows an error message instead of
  Emacs's single-file listing.
* Flagged directories are deleted recursively without Emacs's extra
  ``dired-recursive-deletes`` confirmation.
* Declining the ``Copy … recursively?`` confirm aborts silently.
* The `` *Deletions*`` popup window splits evenly instead of shrinking
  to fit its contents.
"""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, Protocol

from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.modes import defmode

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor


# Synthesized free space shown in the header line. The VFS does not
# model disk capacity; the constant just has to look right in-fiction.
DIRED_FREE_SPACE = "13.4 GiB"

_FILE_PERMS = "-rw-r--r--"
_DIR_PERMS = "drwxr-xr-x"
_OWNER = "neon"
_GROUP = "neon"
_DIR_SIZE = 4096

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip

# ls shows "Mon DD HH:MM" for mtimes within roughly the last six months
# and "Mon DD  YYYY" otherwise (GNU ls uses the now-6months .. now window).
_RECENT_WINDOW = timedelta(days=182, hours=12)

# An entry line: mark cell, space, permission bits, then the numeric
# columns through the 12-character date stamp, then the filename. Like
# GNU dired's ``dired-move-to-filename``, lines are recognised by this
# shape rather than fixed columns — a freshly inserted entry (R/C/+) is
# rendered with its own minimal widths and may sit off-grid until ``g``.
_ENTRY_RE = re.compile(
    r"^(?P<mark>.)\s"
    r"[-d][rwx-]{9}\s+"  # permissions
    r"(?P<nlink>\d+)\s+"  # link count
    r"\S+\s+\S+\s+"  # owner, group
    r"(?P<size>\d+)\s"  # size
    r"[A-Z][a-z]{2} [ \d]\d (?:\d{2}:\d{2}| \d{4})\s"  # date stamp
    r"(?P<name>.+)$"
)


# ------------------------------------------------------------------
# Provider protocol — implemented by the hosting environment
# ------------------------------------------------------------------


@dataclass
class DiredEntry:
    """One directory entry as reported by the provider."""

    name: str
    is_dir: bool
    size: int = 0
    mtime: datetime | None = None
    nsubdirs: int = 0
    """Number of subdirectories (directories only) — synthesizes nlink."""


class DiredProvider(Protocol):
    """Virtual-filesystem access for dired buffers.

    All paths are absolute virtual paths (``/home/user/...``). Methods
    raise ``OSError`` subclasses (``FileNotFoundError``,
    ``NotADirectoryError``, ``FileExistsError``) or ``ValueError`` with
    user-presentable messages; dired surfaces them in the echo area.
    """

    def list_dir(self, path: str) -> list[DiredEntry]: ...

    def metadata(self, path: str) -> DiredEntry: ...

    def is_dir(self, path: str) -> bool | None:
        """True/False for an existing path, None when it does not exist."""
        ...

    def create_dir(self, path: str) -> None: ...

    def delete(self, path: str) -> None: ...

    def rename(self, old: str, new: str) -> str:
        """Move *old* to *new*; an existing-directory target means "into
        it under the original name". Returns the resulting path."""
        ...

    def copy(self, old: str, new: str) -> str:
        """Copy *old* to *new* (same target semantics as :meth:`rename`).
        Directory copies are recursive. Returns the resulting path."""
        ...


# ------------------------------------------------------------------
# Per-buffer state
# ------------------------------------------------------------------


@dataclass
class DiredState:
    """State attached to a dired buffer as ``buf._dired_state``."""

    path: str
    """Absolute directory path, no trailing slash (except the root)."""

    fingerprint: list[tuple[str, bool, int, datetime | None]] = field(
        default_factory=list
    )
    """Sorted (name, is_dir, size, mtime) snapshot of the directory as of
    the last provider read — revisits compare against it to show Emacs's
    "Directory has changed on disk; type g to update Dired" hint."""


def _parent_path(path: str) -> str:
    if path == "/":
        return "/"
    head = path.rsplit("/", 1)[0]
    return head or "/"


def _basename(path: str) -> str:
    if path == "/":
        return "/"
    return path.rsplit("/", 1)[-1]


def _join(dirpath: str, name: str) -> str:
    if dirpath == "/":
        return "/" + name
    return f"{dirpath}/{name}"


def _normalize(path: str, *, relative_to: str) -> str:
    """Normalize *path*: make relative input absolute, strip the
    trailing slash (the prompts pre-fill ``…/``)."""
    path = path.strip()
    if not path.startswith("/"):
        path = _join(relative_to, path) if path else relative_to
    while len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _fingerprint(
    entries: list[DiredEntry],
) -> list[tuple[str, bool, int, datetime | None]]:
    return sorted((e.name, e.is_dir, e.size, e.mtime) for e in entries)


# ------------------------------------------------------------------
# Listing rendering
# ------------------------------------------------------------------


def _format_mtime(mtime: datetime | None, now: datetime) -> str:
    dt = mtime or now
    if dt.tzinfo is not None:
        # The VFS stores aware (UTC) timestamps; ls shows local time.
        dt = dt.astimezone().replace(tzinfo=None)
    recent = now - _RECENT_WINDOW <= dt <= now
    mon = _MONTHS[dt.month - 1]
    if recent:
        return f"{mon} {dt.day:2d} {dt.hour:02d}:{dt.minute:02d}"
    return f"{mon} {dt.day:2d}  {dt.year}"


def _entry_nlink(e: DiredEntry) -> int:
    return 2 + e.nsubdirs if e.is_dir else 1


def _entry_size(e: DiredEntry) -> int:
    return _DIR_SIZE if e.is_dir else e.size


def _render_rows(
    entries: list[DiredEntry],
    now: datetime,
    *,
    min_nlink_w: int = 1,
    min_size_w: int = 1,
) -> list[str]:
    """``ls -l``-style rows for *entries* (in the given order), without
    the two leading mark cells. Numeric columns are right-aligned to the
    widest value across *entries* (at least ``min_nlink_w``/``min_size_w``
    — used to keep a single inserted row on the listing's grid)."""
    nlink_w = max((len(str(_entry_nlink(e))) for e in entries), default=1)
    size_w = max((len(str(_entry_size(e))) for e in entries), default=1)
    nlink_w = max(nlink_w, min_nlink_w)
    size_w = max(size_w, min_size_w)
    rows = []
    for e in entries:
        perms = _DIR_PERMS if e.is_dir else _FILE_PERMS
        rows.append(
            f"{perms} {_entry_nlink(e):>{nlink_w}} {_OWNER} {_GROUP} "
            f"{_entry_size(e):>{size_w}} {_format_mtime(e.mtime, now)} {e.name}"
        )
    return rows


def _listing_entries(
    provider: DiredProvider, path: str, entries: list[DiredEntry]
) -> list[DiredEntry]:
    """The full row list: ``.``, ``..``, then *entries* sorted by name."""
    self_meta = provider.metadata(path)
    parent_meta = provider.metadata(_parent_path(path))
    dot = DiredEntry(
        name=".",
        is_dir=True,
        mtime=self_meta.mtime,
        nsubdirs=self_meta.nsubdirs,
    )
    dotdot = DiredEntry(
        name="..",
        is_dir=True,
        mtime=parent_meta.mtime,
        nsubdirs=parent_meta.nsubdirs,
    )
    return [dot, dotdot] + sorted(entries, key=lambda e: e.name)


def _render_listing(
    provider: DiredProvider,
    path: str,
    entries: list[DiredEntry],
    *,
    marks: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[str]:
    """Build the full buffer line list for a dired buffer.

    ``marks`` maps entry names to their mark characters (``D``/``C``/…)
    so a re-list can preserve them, like Emacs's ``dired-revert``.
    """
    now = now or datetime.now()
    ordered = _listing_entries(provider, path, entries)
    rows = _render_rows(ordered, now)
    lines = [f"  {path}: ({DIRED_FREE_SPACE} available)"]
    for entry, row in zip(ordered, rows, strict=True):
        mark = " "
        if marks and entry.name not in (".", ".."):
            mark = marks.get(entry.name, " ")
        lines.append(f"{mark} {row}")
    lines.append("")  # trailing newline, like ls output
    return lines


# ------------------------------------------------------------------
# Buffer-line inspection
# ------------------------------------------------------------------


def _entry_match(buf: Buffer, line: int) -> re.Match[str] | None:
    if line <= 0 or line >= buf.line_count:
        return None
    return _ENTRY_RE.match(buf.lines[line])


def _entry_name_at(buf: Buffer, line: int) -> str | None:
    """The entry name on buffer *line*, or None for header/blank lines."""
    m = _entry_match(buf, line)
    return m.group("name") if m is not None else None


def _entry_at_point(buf: Buffer) -> str | None:
    return _entry_name_at(buf, buf.point.line)


def _is_dir_line(buf: Buffer, line: int) -> bool:
    text = buf.lines[line]
    return len(text) > 2 and text[2] == "d"


def _move_to_filename(buf: Buffer) -> None:
    """Place point on the filename of the current line (column 0 when
    the line carries no filename — the header and the trailing blank)."""
    m = _entry_match(buf, buf.point.line)
    col = m.start("name") if m is not None else 0
    buf.point.move_to(buf.point.line, col)


def _collect_marks(buf: Buffer) -> dict[str, str]:
    """Current mark characters by entry name (skips unmarked lines)."""
    marks: dict[str, str] = {}
    for i in range(1, buf.line_count):
        m = _entry_match(buf, i)
        if m is None or m.group("name") in (".", ".."):
            continue
        if m.group("mark") != " ":
            marks[m.group("name")] = m.group("mark")
    return marks


def _rewrite_buffer(buf: Buffer, fn: Callable[[], None]) -> None:
    """Run a programmatic buffer mutation with the read-only flag lifted."""
    buf.read_only = False
    try:
        fn()
    finally:
        buf.read_only = True


# ------------------------------------------------------------------
# Mode + buffer setup
# ------------------------------------------------------------------

defmode(
    "dired-mode",
    is_major=True,
    doc="Major mode for directory listings over the virtual filesystem.",
    indicator="Dired by name",
    # dired sets mode-line-buffer-identification to "%17b" (probed).
    buffer_id_width=17,
)


def _dired_keymap(editor: Editor) -> Keymap:
    km = Keymap("dired-mode-map", parent=editor.global_keymap)
    km.bind("n", "dired-next-line")
    km.bind(" ", "dired-next-line")
    km.bind("p", "dired-previous-line")
    km.bind("Enter", "dired-find-file")
    km.bind("e", "dired-find-file")
    km.bind("f", "dired-find-file")
    km.bind("^", "dired-up-directory")
    km.bind("g", _dired_revert)
    km.bind("d", "dired-flag-file-deletion")
    km.bind("u", "dired-unmark")
    km.bind("x", "dired-do-flagged-delete")
    km.bind("+", "dired-create-directory")
    km.bind("R", "dired-do-rename")
    km.bind("C", "dired-do-copy")
    km.bind("q", "quit-window")
    return km


def _unique_buffer_name(ed: Editor, base: str) -> str:
    taken = {b.name for b in ed.buffers}
    if base not in taken:
        return base
    n = 2
    while f"{base}<{n}>" in taken:
        n += 1
    return f"{base}<{n}>"


def _dired_buffer_for(ed: Editor, path: str) -> Buffer | None:
    for buf in ed.buffers:
        st = getattr(buf, "_dired_state", None)
        if st is not None and st.path == path:
            return buf
    return None


def _initial_point(buf: Buffer) -> None:
    """First real entry (line 3: header, ``.``, ``..``, entries…); an
    empty directory leaves point on the trailing blank line (probed)."""
    if buf.line_count > 4:
        buf.point.move_to(3, 0)
    else:
        buf.point.move_to(buf.line_count - 1, 0)
    _move_to_filename(buf)


def open_dired(ed: Editor, path: str, *, set_point_on: str | None = None) -> bool:
    """Open (or revisit) a dired buffer on *path*.

    ``set_point_on`` names a child entry to land on (used by
    ``dired-up-directory``, which leaves point on the directory the user
    came from). Returns False when dired is unavailable or *path* is not
    a listable directory (an explanatory message is set either way).
    """
    provider: DiredProvider | None = getattr(ed, "dired_provider", None)
    if provider is None:
        ed.message = "Dired not available in this context"
        return False
    path = _normalize(path, relative_to=ed.default_directory or "/")

    existing = _dired_buffer_for(ed, path)
    if existing is not None:
        state: DiredState = existing._dired_state  # type: ignore[attr-defined]
        ed.switch_to_buffer(existing.name)
        try:
            entries = provider.list_dir(path)
        except (OSError, ValueError) as e:
            ed.message = str(e)
            return True
        if _fingerprint(entries) != state.fingerprint:
            ed.message = "Directory has changed on disk; type g to update Dired"
        if set_point_on is not None:
            _goto_entry(existing, set_point_on)
        return True

    try:
        entries = provider.list_dir(path)
    except (OSError, ValueError) as e:
        ed.message = str(e)
        return False

    buf = ed.create_buffer(name=_unique_buffer_name(ed, _basename(path)))
    state = DiredState(path=path)
    buf._dired_state = state  # type: ignore[attr-defined]
    buf.keymap = _dired_keymap(ed)
    ed.set_major_mode("dired-mode")

    buf.lines = _render_listing(provider, path, entries)
    state.fingerprint = _fingerprint(entries)
    buf.mark_saved()
    buf.read_only = True

    _initial_point(buf)
    if set_point_on is not None:
        _goto_entry(buf, set_point_on)
    return True


def _goto_entry(buf: Buffer, name: str) -> bool:
    for i in range(1, buf.line_count):
        m = _entry_match(buf, i)
        if m is not None and m.group("name") == name:
            buf.point.move_to(i, m.start("name"))
            return True
    return False


def _require_dired(ed: Editor) -> tuple[Buffer, DiredState] | None:
    buf = ed.buffer
    state = getattr(buf, "_dired_state", None)
    if state is None:
        ed.message = "Not a Dired buffer"
        return None
    return buf, state


def _provider(ed: Editor) -> DiredProvider:
    provider: DiredProvider | None = getattr(ed, "dired_provider", None)
    assert provider is not None, "dired buffer without a provider"
    return provider


def _on_minibuffer_cancel(ed: Editor, cleanup: Callable[[], None]) -> None:
    """Run *cleanup* if the just-started minibuffer is cancelled (C-g /
    ESC). Wraps ``process_key`` — the pattern established by the
    query-replace ``e`` sub-phase (6l-4)."""
    mb = ed.minibuffer
    if mb is None:
        return
    orig = mb.process_key

    def wrapped(key: str) -> bool:
        still_active = orig(key)
        if not still_active and mb.cancelled:
            cleanup()
        return still_active

    mb.process_key = wrapped  # type: ignore[method-assign]


# ------------------------------------------------------------------
# Commands — navigation
# ------------------------------------------------------------------


@defcommand("dired", "Open a directory listing (C-x d).")
def dired(ed: Editor, prefix: int | None) -> None:
    initial = ed.default_directory
    if initial and not initial.endswith("/"):
        initial += "/"

    def callback(path: str) -> None:
        open_dired(ed, path)

    ed.start_minibuffer(
        "Dired (directory): ",
        callback,
        completer=ed.path_completer,
        initial=initial,
        history="file-name",
    )


@defcommand("dired-next-line", "Move down one line, onto the filename (n).")
def dired_next_line(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, _ = ctx
    buf.forward_line(prefix or 1)
    _move_to_filename(buf)


@defcommand("dired-previous-line", "Move up one line, onto the filename (p).")
def dired_previous_line(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, _ = ctx
    buf.backward_line(prefix or 1)
    _move_to_filename(buf)


@defcommand("dired-find-file", "Visit the file or directory at point (RET).")
def dired_find_file(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, state = ctx
    name = _entry_at_point(buf)
    if name is None:
        ed.message = "No file on this line"
        return
    if name == ".":
        open_dired(ed, state.path)
        return
    if name == "..":
        open_dired(ed, _parent_path(state.path))
        return
    path = _join(state.path, name)
    if _is_dir_line(buf, buf.point.line):
        open_dired(ed, path)
        return
    # Visit the file — the find-file open path (already-open check via
    # filepath, content via the host's open_callback).
    for b in ed.buffers:
        if b.filepath == path:
            ed.switch_to_buffer(b.name)
            return
    content = ed.open_callback(path) if ed.open_callback is not None else ""
    ed.create_buffer(name=name, text=content, filepath=path)
    from recursive_neon.editor.default_commands import _auto_detect_mode

    _auto_detect_mode(ed, path)


@defcommand("dired-up-directory", "Visit the parent directory (^).")
def dired_up_directory(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    _, state = ctx
    open_dired(ed, _parent_path(state.path), set_point_on=_basename(state.path))


def _dired_revert(ed: Editor, prefix: int | None) -> None:
    """Re-read the directory (g) — marks and point file preserved."""
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, state = ctx
    provider = _provider(ed)
    try:
        entries = provider.list_dir(state.path)
    except (OSError, ValueError) as e:
        ed.message = str(e)
        return
    marks = _collect_marks(buf)
    current = _entry_at_point(buf)
    old_line = buf.point.line
    lines = _render_listing(provider, state.path, entries, marks=marks)

    def apply() -> None:
        buf.lines = lines
        state.fingerprint = _fingerprint(entries)
        if current is None or not _goto_entry(buf, current):
            buf.point.move_to(min(old_line, buf.line_count - 1), 0)
            _move_to_filename(buf)

    _rewrite_buffer(buf, apply)


# ------------------------------------------------------------------
# Commands — flagging and deletion
# ------------------------------------------------------------------


def _set_mark_char(buf: Buffer, line: int, mark: str) -> None:
    def apply() -> None:
        buf.lines[line] = mark + buf.lines[line][1:]
        buf.modified = True

    _rewrite_buffer(buf, apply)


def _mark_command(ed: Editor, mark: str | None) -> None:
    """Shared body of ``d`` (mark ``D``) and ``u`` (mark cleared).

    Emacs silently skips lines it cannot mark — the probe shows ``d`` on
    ``..`` just moving down with no message — and so do we, including
    the header line. On the trailing blank line nothing moves.
    """
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, _ = ctx
    name = _entry_at_point(buf)
    if name is not None and name not in (".", ".."):
        _set_mark_char(buf, buf.point.line, mark if mark is not None else " ")
    if buf.point.line < buf.line_count - 1:
        buf.forward_line(1)
    _move_to_filename(buf)


@defcommand("dired-flag-file-deletion", "Flag the entry at point for deletion (d).")
def dired_flag_file_deletion(ed: Editor, prefix: int | None) -> None:
    _mark_command(ed, "D")


@defcommand("dired-unmark", "Remove the mark on the entry at point (u).")
def dired_unmark(ed: Editor, prefix: int | None) -> None:
    _mark_command(ed, None)


def _read_yes_or_no(
    ed: Editor,
    question: str,
    on_yes: Callable[[], None],
    on_no: Callable[[], None] | None = None,
    on_quit: Callable[[], None] | None = None,
) -> None:
    """Emacs's ``yes-or-no-p``: only a literal yes/no answer exits; any
    other input re-prompts. C-g cancels (running *on_quit* first)."""

    def on_submit(text: str) -> None:
        answer = text.strip().lower()
        if answer == "yes":
            on_yes()
        elif answer == "no":
            if on_no is not None:
                on_no()
        else:
            _read_yes_or_no(ed, question, on_yes, on_no, on_quit)

    ed.start_minibuffer(question, on_submit)
    if on_quit is not None:
        _on_minibuffer_cancel(ed, on_quit)


_DELETIONS_BUFFER = " *Deletions*"


def _show_deletions_popup(ed: Editor, names: list[str]) -> None:
    """List the flagged names in a `` *Deletions*`` popup window.

    Matches the Emacs probe: read-only + modified (modeline ``%*``),
    Fundamental mode, shown without stealing focus. Geometry differs
    (Emacs shrinks the window to fit; we split evenly) — pinned by unit
    tests, not parity checkpoints.
    """
    previous = ed.buffer
    if not ed.switch_to_buffer(_DELETIONS_BUFFER):
        ed.create_buffer(name=_DELETIONS_BUFFER)
    buf = ed.buffer
    buf.read_only = False
    buf.lines = list(names)
    buf.point.move_to(0, 0)
    buf.read_only = True
    buf.modified = True
    ed.set_major_mode("fundamental-mode")
    for i, b in enumerate(ed._buffers):
        if b is previous:
            ed._current_index = i
            break
    if ed._window_tree is not None:
        ed.display_buffer_other_window(_DELETIONS_BUFFER)


def _dismiss_deletions_popup(ed: Editor) -> None:
    tree = ed._window_tree
    if tree is not None and not tree.is_single():
        for win in tree.windows():
            if win.buffer.name == _DELETIONS_BUFFER:
                prev_active = tree.active
                tree.active = win
                tree.delete_window()
                if prev_active in tree.windows():
                    tree.active = prev_active
                break
    if any(b.name == _DELETIONS_BUFFER for b in ed.buffers):
        ed.remove_buffer(_DELETIONS_BUFFER)
        ed.message = ""


@defcommand("dired-do-flagged-delete", "Delete the entries flagged with D (x).")
def dired_do_flagged_delete(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, state = ctx
    flagged: list[tuple[int, str]] = []
    for i in range(1, buf.line_count):
        m = _entry_match(buf, i)
        if (
            m is not None
            and m.group("mark") == "D"
            and m.group("name") not in (".", "..")
        ):
            flagged.append((i, m.group("name")))
    if not flagged:
        ed.message = "(No deletions requested)"
        return

    provider = _provider(ed)
    old_line = buf.point.line

    def do_delete() -> None:
        _dismiss_deletions_popup(ed)
        deleted: list[int] = []
        error: str | None = None
        for i, name in flagged:
            try:
                provider.delete(_join(state.path, name))
            except (OSError, ValueError) as e:
                error = str(e)
                break
            deleted.append(i)

        def apply() -> None:
            for i in sorted(deleted, reverse=True):
                del buf.lines[i]
            if not buf.lines:
                buf.lines = [""]
            # Point rides the surviving text: lines deleted above it
            # shift it up, so it stays on the same file (probed — after
            # deleting the entry above, Emacs's point is still on the
            # file it was on, one screen row higher).
            new_line = old_line - sum(1 for i in deleted if i < old_line)
            buf.point.move_to(min(new_line, buf.line_count - 1), 0)
            _move_to_filename(buf)

        _rewrite_buffer(buf, apply)
        with suppress(OSError, ValueError):
            state.fingerprint = _fingerprint(provider.list_dir(state.path))
        ed.message = error if error is not None else "Deleting...done"

    def do_abort() -> None:
        _dismiss_deletions_popup(ed)
        ed.message = "(No deletions performed)"

    if len(flagged) == 1:
        question = f"Delete {flagged[0][1]} (yes or no) "
    else:
        _show_deletions_popup(ed, [name for _, name in flagged])
        question = f"Delete D [{len(flagged)} files] (yes or no) "
    _read_yes_or_no(
        ed,
        question,
        do_delete,
        do_abort,
        on_quit=lambda: _dismiss_deletions_popup(ed),
    )


# ------------------------------------------------------------------
# Commands — create / rename / copy
# ------------------------------------------------------------------


def _insert_entry_line(
    ed: Editor,
    buf: Buffer,
    state: DiredState,
    name: str,
    *,
    mark: str = " ",
    at_line: int | None = None,
) -> None:
    """Insert a freshly-rendered entry line for *name* at the line
    containing point (Emacs's ``dired-add-entry``) and leave point on it.

    The row's numeric columns are aligned to the listing's current grid
    (Emacs 29's ``dired-align-file``); a value wider than the grid
    stretches only this row until ``g`` re-lists.
    """
    provider = _provider(ed)
    try:
        meta = provider.metadata(_join(state.path, name))
    except (OSError, ValueError):
        meta = DiredEntry(name=name, is_dir=False)
    meta.name = name
    nlink_w = size_w = 1
    for i in range(1, buf.line_count):
        m = _entry_match(buf, i)
        if m is not None:
            nlink_w = max(nlink_w, len(m.group("nlink")))
            size_w = max(size_w, len(m.group("size")))
    row = _render_rows([meta], datetime.now(), min_nlink_w=nlink_w, min_size_w=size_w)[
        0
    ]

    line = buf.point.line if at_line is None else at_line
    name_at = _entry_name_at(buf, line)
    if name_at is None and line >= buf.line_count - 1:
        line = buf.line_count - 1  # trailing blank: insert before it
    elif name_at is None or name_at in (".", ".."):
        line = min(3, buf.line_count - 1)  # header/dot region: first entry

    def apply() -> None:
        buf.lines.insert(line, f"{mark} {row}")
        buf.modified = True
        buf.point.move_to(line, 0)
        _move_to_filename(buf)

    _rewrite_buffer(buf, apply)
    with suppress(OSError, ValueError):
        state.fingerprint = _fingerprint(provider.list_dir(state.path))


@defcommand("dired-create-directory", "Create a directory (+).")
def dired_create_directory(ed: Editor, prefix: int | None) -> None:
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, state = ctx

    def callback(text: str) -> None:
        path = _normalize(text, relative_to=state.path)
        if path == state.path:
            return
        try:
            _provider(ed).create_dir(path)
        except (OSError, ValueError) as e:
            ed.message = str(e)
            return
        if _parent_path(path) == state.path:
            _insert_entry_line(ed, buf, state, _basename(path))

    ed.start_minibuffer(
        "Create directory: ",
        callback,
        completer=ed.path_completer,
        initial=state.path + ("" if state.path.endswith("/") else "/"),
        history="file-name",
    )


def _transfer_command(
    ed: Editor,
    *,
    verb: str,
    do: Callable[[str, str], str],
    done_message: str,
    keep_mark: bool,
    confirm_recursive: bool,
) -> None:
    """Shared body of ``dired-do-rename`` (R) and ``dired-do-copy`` (C)."""
    ctx = _require_dired(ed)
    if ctx is None:
        return
    buf, state = ctx
    name = _entry_at_point(buf)
    if name is None or name in (".", ".."):
        ed.message = "No file on this line"
        return
    old_full = _join(state.path, name)
    old_line = buf.point.line
    old_mark = buf.lines[old_line][0]
    is_dir = _is_dir_line(buf, old_line)

    def perform(new_full: str) -> None:
        try:
            result_path = do(old_full, new_full)
        except (OSError, ValueError) as e:
            ed.message = str(e)
            return
        if keep_mark:  # rename: drop the old line, re-add in place

            def remove() -> None:
                del buf.lines[old_line]
                buf.modified = True
                buf.point.move_to(min(old_line, buf.line_count - 1), 0)
                _move_to_filename(buf)

            _rewrite_buffer(buf, remove)
            mark = old_mark
        else:
            mark = "C"  # dired-keep-marker-copy
        if _parent_path(result_path) == state.path:
            _insert_entry_line(
                ed, buf, state, _basename(result_path), mark=mark, at_line=old_line
            )
        ed.message = done_message

    def callback(text: str) -> None:
        new_full = _normalize(text, relative_to=state.path)
        if confirm_recursive and is_dir:
            _read_yes_or_no(
                ed,
                f"{verb} {old_full} recursively? (yes or no) ",
                lambda: perform(new_full),
            )
        else:
            perform(new_full)

    ed.start_minibuffer(
        f"{verb} {name} to: ",
        callback,
        completer=ed.path_completer,
        initial=state.path + ("" if state.path.endswith("/") else "/"),
        history="file-name",
    )


@defcommand("dired-do-rename", "Rename (move) the entry at point (R).")
def dired_do_rename(ed: Editor, prefix: int | None) -> None:
    if getattr(ed.buffer, "_dired_state", None) is None:
        ed.message = "Not a Dired buffer"
        return
    _transfer_command(
        ed,
        verb="Rename",
        do=_provider(ed).rename,
        done_message="Move: 1 file done",
        keep_mark=True,
        confirm_recursive=False,
    )


@defcommand("dired-do-copy", "Copy the entry at point (C).")
def dired_do_copy(ed: Editor, prefix: int | None) -> None:
    if getattr(ed.buffer, "_dired_state", None) is None:
        ed.message = "Not a Dired buffer"
        return
    _transfer_command(
        ed,
        verb="Copy",
        do=_provider(ed).copy,
        done_message="Copy: 1 file done",
        keep_mark=False,
        confirm_recursive=True,
    )


def maybe_open_dired_for_path(ed: Editor, path: str) -> bool:
    """find-file hook: open dired when *path* is an existing directory.

    Returns True when the path was handled (Emacs's ``find-file`` on a
    directory runs dired). No-ops when no provider is wired.
    """
    provider: DiredProvider | None = getattr(ed, "dired_provider", None)
    if provider is None:
        return False
    normalized = _normalize(path, relative_to=ed.default_directory or "/")
    if provider.is_dir(normalized) is not True:
        return False
    return open_dired(ed, normalized)
