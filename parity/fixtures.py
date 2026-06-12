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
