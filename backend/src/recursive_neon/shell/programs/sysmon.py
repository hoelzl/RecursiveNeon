"""
sysmon — system monitor TUI.

Displays a fake htop-style process list reading from the game's
ProcessTable.  The player can sort by CPU, memory, name, or PID.

Launched via the ``sysmon`` shell command.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from recursive_neon.models.process import ProcessInfo, ProcessTable
from recursive_neon.shell.output import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.tui import ScreenBuffer

SortKey = Literal["pid", "cpu", "mem", "name"]

# Status → color mapping
_STATUS_STYLE: dict[str, str] = {
    "running": GREEN,
    "sleeping": DIM,
    "zombie": RED,
    "stopped": YELLOW,
}


def _render_bar(value: float, width: int = 20) -> str:
    """Render a percentage bar like ``[████░░░░]``."""
    clamped = max(0.0, min(100.0, value))
    filled = int(clamped / 100.0 * width)
    empty = width - filled
    if clamped > 80:
        color = RED
    elif clamped > 50:
        color = YELLOW
    else:
        color = GREEN
    return f"[{color}{'█' * filled}{DIM}{'░' * empty}{RESET}]"


def _format_uptime(start_time: datetime) -> str:
    """Format uptime as ``Xd HH:MM:SS``."""
    delta = datetime.now(tz=UTC) - start_time
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if days > 0:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class SysMonApp:
    """TUI app for the system monitor."""

    tick_interval_ms: int = 1000

    def __init__(
        self,
        process_table: ProcessTable,
        start_time: datetime | None = None,
    ) -> None:
        self.process_table = process_table
        self.start_time = start_time or datetime.now(tz=UTC)
        self.sort_key: SortKey = "pid"
        self.width = 80
        self.height = 24
        self.scroll_offset = 0

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key in ("q", "Escape", "C-c"):
            return None
        if key == "c":
            self.sort_key = "cpu"
            self.scroll_offset = 0
        elif key == "m":
            self.sort_key = "mem"
            self.scroll_offset = 0
        elif key == "n":
            self.sort_key = "name"
            self.scroll_offset = 0
        elif key == "p":
            self.sort_key = "pid"
            self.scroll_offset = 0
        elif key == "ArrowDown":
            self.scroll_offset += 1
        elif key == "ArrowUp":
            self.scroll_offset = max(0, self.scroll_offset - 1)
        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    def on_tick(self, dt_ms: int) -> ScreenBuffer | None:
        return self._render()

    # ── rendering ─────────────────────────────────────────────────────

    def _sorted_processes(self) -> list[ProcessInfo]:
        procs = self.process_table.list_all()
        if self.sort_key == "cpu":
            procs.sort(key=lambda p: p.cpu, reverse=True)
        elif self.sort_key == "mem":
            procs.sort(key=lambda p: p.memory, reverse=True)
        elif self.sort_key == "name":
            procs.sort(key=lambda p: p.name.lower())
        # "pid" is already sorted by default from ProcessTable.list()
        return procs

    def _render(self) -> ScreenBuffer:
        screen = ScreenBuffer.create(self.width, self.height)
        screen.cursor_visible = False

        # Title
        screen.center_text(0, "=== SYSTEM MONITOR ===", style=f"{BOLD}{CYAN}")

        # Summary stats
        total_cpu = self.process_table.total_cpu()
        total_mem = self.process_table.total_memory()
        proc_count = self.process_table.count
        uptime = _format_uptime(self.start_time)

        screen.set_line(
            2,
            f"  Uptime: {BOLD}{uptime}{RESET}   Processes: {BOLD}{proc_count}{RESET}",
        )

        # CPU and memory bars
        cpu_bar = _render_bar(total_cpu)
        mem_bar = _render_bar(total_mem)
        screen.set_line(
            3,
            f"  CPU {cpu_bar} {total_cpu:5.1f}%   MEM {mem_bar} {total_mem:5.1f}%",
        )

        # Column header
        header_row = 5
        sort_indicators = {"pid": "PID", "cpu": "CPU%", "mem": "MEM%", "name": "NAME"}
        header = (
            f"  {BOLD}"
            f"{'PID':>5}  "
            f"{'NAME':<20} "
            f"{'USER':<8} "
            f"{'CPU%':>5} "
            f"{'MEM%':>5}  "
            f"{'STATUS':<10}"
            f"{RESET}"
        )
        screen.set_line(header_row, header)
        screen.set_line(header_row + 1, f"  {'─' * (self.width - 4)}")

        # Process rows
        procs = self._sorted_processes()
        first_proc_row = header_row + 2
        available_rows = self.height - first_proc_row - 2  # leave room for controls

        # Clamp scroll
        max_scroll = max(0, len(procs) - available_rows)
        self.scroll_offset = min(self.scroll_offset, max_scroll)

        visible = procs[self.scroll_offset : self.scroll_offset + available_rows]
        for i, proc in enumerate(visible):
            row = first_proc_row + i
            status_style = _STATUS_STYLE.get(proc.status, "")
            tag_hint = ""
            if "security" in proc.tags:
                tag_hint = f" {RED}●{RESET}"
            elif "network" in proc.tags:
                tag_hint = f" {CYAN}●{RESET}"
            elif "database" in proc.tags:
                tag_hint = f" {YELLOW}●{RESET}"

            line = (
                f"  {proc.pid:5d}  "
                f"{proc.name:<20} "
                f"{proc.user:<8} "
                f"{proc.cpu:5.1f} "
                f"{proc.memory:5.1f}  "
                f"{status_style}{proc.status:<10}{RESET}"
                f"{tag_hint}"
            )
            screen.set_line(row, line)

        # Scroll indicator
        if len(procs) > available_rows:
            shown = f"{self.scroll_offset + 1}-{min(self.scroll_offset + available_rows, len(procs))}/{len(procs)}"
            screen.set_line(
                self.height - 3,
                f"  {DIM}{shown}{RESET}",
            )

        # Sort indicator + controls
        active_sort = sort_indicators[self.sort_key]
        screen.set_line(
            self.height - 2,
            f"  {DIM}Sort: {RESET}{BOLD}{active_sort}{RESET}  "
            f"{DIM}[p]ID  [c]PU  [m]EM  [n]ame  "
            f"[↑↓] Scroll  [q] Quit{RESET}",
        )

        return screen


# ── Shell registration ────────────────────────────────────────────────


def register_sysmon_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "sysmon",
        _run_sysmon,
        "System monitor — view running processes\n\n"
        "Usage: sysmon\n\n"
        "Displays a live process list for the current system.\n"
        "Sort by CPU, memory, name, or PID.\n\n"
        "Keys:\n"
        "  p  Sort by PID (default)\n"
        "  c  Sort by CPU usage\n"
        "  m  Sort by memory usage\n"
        "  n  Sort by name\n"
        "  q  Quit",
    )


async def _run_sysmon(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("sysmon: requires a terminal that supports TUI mode")
        return 1
    app = SysMonApp(
        process_table=ctx.services.process_table,
        start_time=ctx.services.start_time,
    )
    return await ctx.run_tui(app)
