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
3. Send a no-op ``C-f C-b`` after settle. Emacs only renders the *file*
   buffer after the first input event; without the kick, the initial
   screen still shows ``*scratch*`` even though point is in the file.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from parity.harness import Driver, TargetSpec


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
BACKEND_SRC = REPO_ROOT / "backend" / "src"


def make_emacs_target(
    file_path: str,
    *,
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
) -> TargetSpec:
    """Open ``file_path`` in Emacs ``-Q`` with a quiet startup."""

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
        d = Driver("emacs", args=args, cols=cols, rows=rows)
        d.settle(settle_ms=settle_ms, max_wait=6.0)
        # Kick Emacs to flush its initial render of the file buffer.
        d.send("C-f C-b")
        d.settle(settle_ms=settle_ms, max_wait=4.0)
        return d

    return TargetSpec(name="emacs", launch=launch)


def make_neon_target(
    *,
    setup_lines: list[str],
    edit_command: str,
    cols: int = 80,
    rows: int = 24,
    settle_ms: int = 1200,
    cwd: str = "/tmp",
) -> TargetSpec:
    """Launch ``python -m recursive_neon.shell``, run setup, then ``edit``.

    Each entry of ``setup_lines`` is a shell command (sent verbatim plus a
    Return). ``edit_command`` is the full ``edit ...`` invocation.
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
        d.settle(settle_ms=settle_ms, max_wait=8.0)
        for line in setup_lines:
            d.sendline(line)
            d.settle(settle_ms=500, max_wait=3.0)
        d.sendline(edit_command)
        # First settle drains the shell prompt + "[entering raw mode]" handoff
        # plus the editor's initial paint.
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
