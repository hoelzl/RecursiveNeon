"""PTY harness for driving an editor and capturing screen snapshots.

Wraps pexpect (for the pty) and pyte (for terminal emulation). Reads bytes
from the child until output settles, then exposes the resulting screen as
a structured ``Snapshot``.

Snapshots are intentionally text-only (no SGR attributes). Attribute-level
comparison is too noisy for an initial parity harness and would obscure the
"feels off" gaps we care about (echo area text, modeline format, completion
lists, cursor position).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Sequence

import pexpect
import pyte

from parity.keys import kbd


@dataclass(frozen=True)
class Snapshot:
    label: str
    lines: tuple[str, ...]
    cursor: tuple[int, int]  # (x, y) — column, row, 0-indexed
    cols: int
    rows: int

    @property
    def echo_area(self) -> str:
        """The bottom row, where Emacs renders the minibuffer / echo area."""
        return self.lines[-1].rstrip()

    @property
    def modeline(self) -> str:
        """The row above the echo area, typically the modeline."""
        return self.lines[-2].rstrip()

    @property
    def body(self) -> tuple[str, ...]:
        """All rows above the modeline."""
        return self.lines[:-2]

    def text(self, *, trim_trailing_blank_rows: bool = False) -> str:
        rows = list(self.lines)
        if trim_trailing_blank_rows:
            while rows and not rows[-1].strip():
                rows.pop()
        # Right-strip each row but preserve column structure inside.
        return "\n".join(r.rstrip() for r in rows)


class Driver:
    """Spawns a child process under a pty and feeds its output to pyte."""

    def __init__(
        self,
        cmd: str,
        args: Sequence[str] = (),
        *,
        cols: int = 80,
        rows: int = 24,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.cols = cols
        self.rows = rows
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        full_env = os.environ.copy()
        full_env.setdefault("TERM", "xterm-256color")
        full_env.setdefault("LC_ALL", "C.UTF-8")
        full_env.setdefault("LANG", "C.UTF-8")
        if env:
            full_env.update(env)
        self.child = pexpect.spawn(
            cmd,
            args=list(args),
            dimensions=(rows, cols),
            encoding=None,
            env=full_env,
            cwd=cwd,
            timeout=timeout,
        )
        self._closed = False

    def settle(self, *, max_wait: float = 5.0, settle_ms: int = 800) -> None:
        """Drain output until ``settle_ms`` passes with no new bytes, or
        until ``max_wait`` elapses overall.
        """
        deadline = time.time() + max_wait
        last_change = time.time()
        while time.time() < deadline:
            try:
                data = self.child.read_nonblocking(size=4096, timeout=0.05)
            except pexpect.TIMEOUT:
                if (time.time() - last_change) * 1000 >= settle_ms:
                    return
                continue
            except pexpect.EOF:
                return
            if data:
                self.stream.feed(data)
                last_change = time.time()

    def wait_for(
        self,
        needle: str,
        *,
        row: int | None = None,
        max_wait: float = 20.0,
        settle_ms: int = 400,
    ) -> bool:
        """Drain output until ``needle`` appears on screen, then settle.

        Unlike :meth:`settle` (which returns after a fixed window of
        *silence*), this waits for a readiness *condition*. That matters on
        hosts where a child has long silent gaps during startup — e.g. when
        neon-edit's source is imported over a slow filesystem (a Windows
        checkout driven through WSL), the ~4s cold-import produces no output
        and a pure-silence settle would return before the shell is ready.

        If ``row`` is given, only that screen row is searched (negative
        indices allowed, e.g. ``-2`` for the modeline). Returns True if the
        needle was found before ``max_wait`` elapsed. Either way, a short
        trailing :meth:`settle` drains any remaining paint.
        """
        deadline = time.time() + max_wait
        found = False
        while time.time() < deadline:
            try:
                data = self.child.read_nonblocking(size=4096, timeout=0.1)
            except pexpect.TIMEOUT:
                data = b""
            except pexpect.EOF:
                break
            if data:
                self.stream.feed(data)
            haystack = (
                self.screen.display if row is None else [self.screen.display[row]]
            )
            if any(needle in r for r in haystack):
                found = True
                break
        remaining = max(0.5, deadline - time.time())
        self.settle(settle_ms=settle_ms, max_wait=remaining)
        return found

    def send(self, keys: str) -> None:
        """Send an Emacs-style key description (see :mod:`parity.keys`)."""
        self.child.send(kbd(keys))

    def send_raw(self, data: bytes) -> None:
        self.child.send(data)

    def send_text(self, text: str) -> None:
        self.child.send(text.encode("utf-8"))

    def sendline(self, line: str) -> None:
        self.child.send(line.encode("utf-8") + b"\r")

    def snapshot(self, label: str) -> Snapshot:
        return Snapshot(
            label=label,
            lines=tuple(self.screen.display),
            cursor=(self.screen.cursor.x, self.screen.cursor.y),
            cols=self.cols,
            rows=self.rows,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.child.close(force=True)
        except Exception:
            pass

    def __enter__(self) -> "Driver":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


@dataclass
class TargetSpec:
    """Recipe for spawning one editor instance, ready for the scenario script.

    ``launch`` returns a started :class:`Driver` with the editor open on
    the scenario's test file and any setup keystrokes already settled.
    """

    name: str
    launch: "callable[[], Driver]"


@dataclass
class StepResult:
    label: str
    snapshots: dict[str, Snapshot] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    name: str
    description: str
    steps: list[StepResult] = field(default_factory=list)
