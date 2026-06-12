"""Target builders: launch Emacs or neon-edit ready for scripting.

Both editors are spawned in a pty sized 80x24. We always invoke Emacs with
``-Q`` (no init files, no site-lisp) so the comparison reflects the
out-of-the-box GNU Emacs behaviour, not whatever the local user has
configured.

To make the *initial* render comparable, both targets:

1. Disable the menu bar. Emacs in ``-Q`` defaults to TTY menu-bar on; neon-
   edit has no menu bar. We turn Emacs's off.
2. Inhibit the startup-message echo-area tip. Emacs prints a "For
   information about GNU Emacs..." line in the echo area on startup which
   has nothing to do with the buffer state and would obscure scenario
   diffs.
3. Send a no-op ``C-l`` after settle. Emacs only renders the *file*
   buffer after the first input event; without the kick, the initial
   screen still shows ``*scratch*`` even though point is in the file.
   ``C-l`` is the kick because it leaves no trace (no motion, no echo)
   even in an empty buffer.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from parity.harness import Driver, TargetSpec


REPO_ROOT = Path(__file__).resolve().parent.parent
# The Python interpreter used to run neon-edit's shell. Defaults to the
# project's POSIX virtualenv at ``<repo>/.venv/bin/python``. Override via
# ``NEON_PARITY_PYTHON`` when the harness runs on a host where ``.venv`` is
# not a POSIX venv — e.g. a Windows checkout driven through WSL, where
# ``.venv`` is a Windows venv (``Scripts/python.exe``, no ``bin/python``)
# and the Linux harness venv lives outside the repo.
VENV_PY = Path(
    os.environ.get("NEON_PARITY_PYTHON", str(REPO_ROOT / ".venv" / "bin" / "python"))
)
BACKEND_SRC = REPO_ROOT / "backend" / "src"


def emacs_binary() -> str:
    """The Emacs executable the harness compares against.

    Override via ``NEON_PARITY_EMACS`` to pin a specific build. The
    ground-truth version is printed by ``parity.run`` so reports are
    interpretable later — Emacs behaviour drifts across releases (e.g.
    the ``M-y`` → ``yank-from-kill-ring`` rebind in Emacs 28).
    """
    return os.environ.get("NEON_PARITY_EMACS", "emacs")


def make_emacs_target(
    file_path: str,
    *,
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
    cwd: str | None = None,
) -> TargetSpec:
    """Open ``file_path`` in Emacs ``-Q`` with a quiet startup.

    ``cwd`` should be the scenario's staging directory: it becomes the
    ``default-directory`` of non-file buffers (``*scratch*``), so a
    relative ``C-x C-f`` in a scenario resolves inside the staged
    sandbox rather than wherever the harness happens to run from
    (scenario 27 once stray-wrote a file into the repo root this way).
    """

    eval_forms = [
        "(menu-bar-mode -1)",
        "(setq inhibit-startup-screen t)",
        "(setq initial-scratch-message nil)",
        # Suppress the "For information about GNU Emacs..." echo-area hint.
        "(setq inhibit-startup-echo-area-message (user-login-name))",
        # Avoid prompting about local variables / unsafe init files.
        "(setq enable-local-variables nil)",
    ]
    args = ["-nw", "-Q"]
    for form in eval_forms:
        args += ["--eval", form]
    args.append(file_path)

    def launch() -> Driver:
        d = Driver(emacs_binary(), args=args, cols=cols, rows=rows, cwd=cwd)
        # Wait for the startup echo-area tip rather than relying on a
        # silence window: on slow hosts Emacs's startup has silent gaps
        # longer than ``settle_ms``, so a pure-silence settle can return
        # mid-startup — the C-l kick is then consumed *before* the tip is
        # displayed, leaving the tip on screen at snapshot time. The tip
        # is the *last* thing startup paints and, under ``-Q``, always
        # appears (``inhibit-startup-echo-area-message`` only takes
        # effect when literally set in an init file — startup.el greps
        # the init file for it — so the --eval above cannot suppress it).
        d.wait_for(
            "For information about GNU Emacs",
            row=-1,
            max_wait=30.0,
            settle_ms=settle_ms,
        )
        # Kick Emacs to flush its initial render of the file buffer (any
        # input event works); it also clears the tip. C-l (recenter) is
        # used because it leaves no trace: no point motion and no echo.
        # Exactly one C-l — repeats would cycle recenter-top-bottom and
        # scroll windows whose point sits below the first screen line.
        # The previous kick, C-f C-b, *errored* in an empty buffer
        # (echoing "End of buffer") and made the launch states differ
        # from neon-edit's, which gets no kick.
        d.send("C-l")
        d.settle(settle_ms=settle_ms, max_wait=4.0)
        return d

    return TargetSpec(name="emacs", launch=launch)


def make_neon_target(
    *,
    setup_lines: list[str],
    edit_command: str,
    ready_marker: str | None = None,
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
    cwd: str = "/tmp",
) -> TargetSpec:
    """Launch ``python -m recursive_neon.shell``, run setup, then ``edit``.

    Each entry of ``setup_lines`` is a shell command (sent verbatim plus a
    Return). ``edit_command`` is the full ``edit ...`` invocation.

    ``ready_marker`` is a substring expected to appear in the editor's
    modeline once the file is open (typically the file's basename). When
    given, the launch waits for it rather than relying on output silence —
    essential on hosts where neon-edit's cold import is slow enough that a
    pure-silence settle would return before the shell prompt or editor has
    painted (e.g. a Windows checkout driven through WSL).
    """

    env = {"PYTHONPATH": str(BACKEND_SRC)}

    def launch() -> Driver:
        d = Driver(
            str(VENV_PY),
            args=["-m", "recursive_neon.shell"],
            cols=cols,
            rows=rows,
            env=env,
            cwd=cwd,
        )
        # Wait for the shell prompt rather than a silence window: the cold
        # import can be several seconds of total silence on a slow FS.
        if not d.wait_for("neon-proxy:", max_wait=30.0, settle_ms=settle_ms):
            d.settle(settle_ms=settle_ms, max_wait=8.0)
        for line in setup_lines:
            d.sendline(line)
            d.settle(settle_ms=500, max_wait=3.0)
        d.sendline(edit_command)
        # Wait for the editor to take over: its modeline (the second-to-last
        # row) shows the file's basename once the buffer is open. Before that
        # the row is blank, so this reliably distinguishes "editor up" from
        # "still at the shell prompt" even though the basename also appears in
        # the echo setup lines higher on the screen.
        if ready_marker is not None:
            d.wait_for(ready_marker, row=-2, max_wait=30.0, settle_ms=settle_ms)
        else:
            # Fallback: drain the shell→editor handoff plus the initial paint.
            d.settle(settle_ms=settle_ms, max_wait=5.0)
        return d

    return TargetSpec(name="neon-edit", launch=launch)


def shell_quote(text: str) -> str:
    """Quote a string for inclusion in a neon-edit shell ``echo`` command."""
    return shlex.quote(text)


def write_file_via_echo(remote_path: str, text: str) -> list[str]:
    """Build neon-edit shell commands that produce ``text`` at ``remote_path``.

    Uses ``echo`` (which appends ``\\n``) for all lines except the last;
    the last line uses ``echo -n`` if and only if ``text`` does not end
    with ``\\n``. The result is byte-for-byte identical to writing ``text``
    to disk with Python's ``Path.write_text``.
    """
    if text == "":
        return [f": > {remote_path}"]

    has_trailing_newline = text.endswith("\n")
    lines = text.split("\n")
    if has_trailing_newline:
        # ``"a\nb\n".split("\n")`` → ``["a", "b", ""]``; drop the empty tail.
        lines = lines[:-1]

    out: list[str] = []
    redirect = ">"
    for i, line in enumerate(lines):
        is_last = i == len(lines) - 1
        prefix = "echo -n" if is_last and not has_trailing_newline else "echo"
        out.append(f"{prefix} {shell_quote(line)} {redirect} {remote_path}")
        redirect = ">>"
    return out
