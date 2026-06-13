"""Shared helpers for scenario authors.

Most scenarios follow the same shape:

  1. Stage a file with known content on disk (so Emacs can open it).
  2. Stage an identical file inside the neon-edit shell session (via
     ``echo … > path`` lines, so the virtual filesystem matches).
  3. Launch both editors, run a script, snapshot at named checkpoints.

The :class:`FileFixture` context manager and :func:`make_targets` factory
package those three steps so individual scenario modules can focus on the
script and snapshot logic.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from parity.harness import TargetSpec
from parity.targets import make_emacs_target, make_neon_target, write_file_via_echo


@dataclass
class FileFixture:
    disk_path: Path
    basename: str
    tmp_dir: Path


@contextmanager
def staged_file(
    *, basename: str, content: str, prefix: str = "parity-"
) -> Iterator[FileFixture]:
    """Stage ``content`` on disk at a tempdir + basename.

    Yields a :class:`FileFixture`; the tempdir is removed on exit.
    """
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        tmp_path = Path(tmp)
        disk = tmp_path / basename
        disk.write_text(content)
        yield FileFixture(disk_path=disk, basename=basename, tmp_dir=tmp_path)


@dataclass
class TreeFixture:
    """A staged directory tree, mirrored on disk and in the neon VFS."""

    disk_root: Path
    dirname: str
    tmp_dir: Path


@contextmanager
def staged_tree(
    *,
    dirname: str,
    files: dict[str, str],
    empty_dirs: tuple[str, ...] = (),
    prefix: str = "parity-",
) -> Iterator[TreeFixture]:
    """Stage a directory tree for dired scenarios.

    ``files`` maps tree-relative paths (``"sub/gamma.txt"``) to contents;
    parent directories are created implicitly, ``empty_dirs`` explicitly.
    The same tree is created on disk (for Emacs) and — via
    :func:`tree_setup_lines` — inside the neon shell session.
    """
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        tmp_path = Path(tmp)
        root = tmp_path / dirname
        root.mkdir()
        for rel in empty_dirs:
            (root / rel).mkdir(parents=True, exist_ok=True)
        for rel, content in files.items():
            disk = root / rel
            disk.parent.mkdir(parents=True, exist_ok=True)
            disk.write_text(content)
        yield TreeFixture(disk_root=root, dirname=dirname, tmp_dir=tmp_path)


def tree_setup_lines(
    fixture: TreeFixture,
    files: dict[str, str],
    empty_dirs: tuple[str, ...] = (),
) -> list[str]:
    """Shell commands that recreate the staged tree in the neon VFS."""
    lines = [f"mkdir {fixture.dirname}"]
    made: set[str] = set()
    for rel in empty_dirs:
        parts = rel.split("/")
        for i in range(1, len(parts) + 1):
            sub = "/".join(parts[:i])
            if sub not in made:
                lines.append(f"mkdir {fixture.dirname}/{sub}")
                made.add(sub)
    for rel, content in files.items():
        parts = rel.split("/")
        for i in range(1, len(parts)):
            sub = "/".join(parts[:i])
            if sub not in made:
                lines.append(f"mkdir {fixture.dirname}/{sub}")
                made.add(sub)
        lines.extend(write_file_via_echo(f"{fixture.dirname}/{rel}", content))
    return lines


def make_tree_targets(
    fixture: TreeFixture,
    files: dict[str, str],
    *,
    empty_dirs: tuple[str, ...] = (),
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
) -> tuple[TargetSpec, TargetSpec]:
    """An (emacs, neon) pair, both opening a dired listing of the tree.

    Emacs opens the staged disk directory from the command line; neon
    recreates the tree in its VFS and runs ``edit <dirname>``. Readiness
    is detected via the dired modeline (``(Dired by name)`` never
    appears in the setup-command output, unlike the directory name).
    """
    emacs = make_emacs_target(
        str(fixture.disk_root),
        cols=cols,
        rows=rows,
        settle_ms=settle_ms,
        cwd=str(fixture.tmp_dir),
    )
    neon = make_neon_target(
        setup_lines=tree_setup_lines(fixture, files, empty_dirs),
        edit_command=f"edit {fixture.dirname}",
        ready_marker="(Dired by name)",
        cols=cols,
        rows=rows,
        settle_ms=settle_ms,
        cwd=str(fixture.tmp_dir),
    )
    return emacs, neon


def make_targets(
    fixture: FileFixture,
    *,
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
) -> tuple[TargetSpec, TargetSpec]:
    """Build an (emacs, neon) target pair both pointed at ``fixture``."""
    emacs = make_emacs_target(
        str(fixture.disk_path),
        cols=cols,
        rows=rows,
        settle_ms=settle_ms,
        cwd=str(fixture.tmp_dir),
    )
    neon = make_neon_target(
        setup_lines=write_file_via_echo(
            fixture.basename, fixture.disk_path.read_text()
        ),
        edit_command=f"edit {fixture.basename}",
        ready_marker=fixture.basename,
        cols=cols,
        rows=rows,
        settle_ms=settle_ms,
        cwd=str(fixture.tmp_dir),
    )
    return emacs, neon
