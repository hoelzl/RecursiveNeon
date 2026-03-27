"""
Process models for the simulated system.

Represents the processes "running" on the in-game computer.  The
ProcessTable is populated at startup with default system daemons and
can be mutated by gameplay logic (e.g., player tools spawn processes,
NPCs add/remove security monitors).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProcessStatus = Literal["running", "sleeping", "zombie", "stopped"]


class ProcessInfo(BaseModel):
    """A single process on the simulated system."""

    pid: int
    name: str
    user: str = "root"
    cpu: float = 0.0  # percentage 0–100
    memory: float = 0.0  # percentage 0–100
    status: ProcessStatus = "running"
    tags: list[str] = Field(default_factory=list)


class ProcessTable:
    """Holds the live process list for the simulated system.

    The table is runtime-only state — not persisted to disk.  It is
    seeded with default processes on startup and can be mutated by
    gameplay events.
    """

    def __init__(self) -> None:
        self._processes: dict[int, ProcessInfo] = {}
        self._next_pid: int = 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, pid: int) -> ProcessInfo | None:
        return self._processes.get(pid)

    def list_all(self) -> list[ProcessInfo]:
        """All processes, sorted by PID."""
        return sorted(self._processes.values(), key=lambda p: p.pid)

    def find_by_tag(self, tag: str) -> list[ProcessInfo]:
        return [p for p in self._processes.values() if tag in p.tags]

    def find_by_name(self, name: str) -> list[ProcessInfo]:
        return [p for p in self._processes.values() if p.name == name]

    @property
    def count(self) -> int:
        return len(self._processes)

    def total_cpu(self) -> float:
        return sum(p.cpu for p in self._processes.values())

    def total_memory(self) -> float:
        return sum(p.memory for p in self._processes.values())

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add(
        self,
        name: str,
        user: str = "root",
        cpu: float = 0.0,
        memory: float = 0.0,
        status: ProcessStatus = "running",
        tags: list[str] | None = None,
    ) -> ProcessInfo:
        """Add a process and return it."""
        proc = ProcessInfo(
            pid=self._next_pid,
            name=name,
            user=user,
            cpu=cpu,
            memory=memory,
            status=status,
            tags=tags or [],
        )
        self._processes[proc.pid] = proc
        self._next_pid += 1
        return proc

    def remove(self, pid: int) -> bool:
        """Remove a process by PID.  Returns True if it existed."""
        return self._processes.pop(pid, None) is not None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def with_defaults(cls) -> ProcessTable:
        """Create a table pre-populated with realistic system processes."""
        t = cls()
        # Core system
        t.add("init", "root", 0.0, 0.1, "sleeping")
        t.add("[kernel]", "root", 0.1, 0.0, "sleeping")
        t.add("sshd", "root", 0.1, 0.3, "sleeping", ["network"])
        t.add("crond", "root", 0.0, 0.1, "sleeping")
        t.add("rsyslogd", "root", 0.1, 0.2, "running")
        # Database
        t.add("postgres", "admin", 2.3, 4.1, "sleeping", ["database"])
        t.add("postgres: worker", "admin", 1.2, 2.8, "sleeping", ["database"])
        # Web stack
        t.add("nginx", "www", 0.3, 1.2, "sleeping", ["network"])
        t.add("node: api-server", "app", 3.5, 8.2, "running", ["network"])
        # Security — gameplay-relevant
        t.add("watchdog", "root", 0.2, 0.1, "running", ["security"])
        t.add("audit_logger", "root", 0.1, 0.3, "running", ["security"])
        return t
