"""
portscan — port scanner minigame TUI.

Scan a grid of network ports to discover which are open, closed, or
decoys, then deduce and enter the correct access sequence before
getting locked out.

Launched via the ``portscan`` shell command.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from recursive_neon.shell.output import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.tui import ScreenBuffer

# ── Constants ────────────────────────────────────────────────────────

GRID_COLS = 4
GRID_ROWS = 3
NUM_PORTS = GRID_COLS * GRID_ROWS  # 12
NUM_OPEN = 3
NUM_DECOY = 3
MAX_SCANS = 5
MAX_ATTEMPTS = 3
LOCKOUT_DURATION_MS = 3000


# ── Data types ───────────────────────────────────────────────────────


class PortType(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DECOY = "DECOY"


class Phase(Enum):
    SCANNING = "scanning"
    SEQUENCE = "sequence"
    LOCKOUT = "lockout"
    WON = "won"
    LOST = "lost"


# Port type → display style
_PORT_STYLE: dict[PortType, str] = {
    PortType.OPEN: f"{BOLD}{GREEN}",
    PortType.CLOSED: f"{DIM}",
    PortType.DECOY: f"{BOLD}{RED}",
}

# Port type → label shown after scan
_PORT_LABEL: dict[PortType, str] = {
    PortType.OPEN: "OPEN",
    PortType.CLOSED: "SHUT",
    PortType.DECOY: "TRAP",
}


@dataclass
class Port:
    """A single port in the grid."""

    number: int  # 1-based display number
    port_type: PortType
    scanned: bool = False


# ── Game state ───────────────────────────────────────────────────────


@dataclass
class PortScanState:
    """Mutable game state for the port scanner."""

    ports: list[Port] = field(default_factory=list)
    phase: Phase = Phase.SCANNING
    cursor: int = 0  # grid cursor for scanning phase
    scans_remaining: int = MAX_SCANS
    attempts_remaining: int = MAX_ATTEMPTS

    # Sequence entry
    sequence_slots: list[int | None] = field(default_factory=list)
    seq_cursor: int = 0

    # Lockout countdown
    lockout_remaining_ms: int = 0

    # The correct answer (sorted open port numbers)
    answer: list[int] = field(default_factory=list)

    message: str = ""

    @classmethod
    def new_game(
        cls,
        *,
        rng: random.Random | None = None,
    ) -> PortScanState:
        """Generate a new game with randomised port assignments."""
        r = rng or random.Random()

        types: list[PortType] = (
            [PortType.OPEN] * NUM_OPEN
            + [PortType.DECOY] * NUM_DECOY
            + [PortType.CLOSED] * (NUM_PORTS - NUM_OPEN - NUM_DECOY)
        )
        r.shuffle(types)

        ports = [Port(number=i + 1, port_type=t) for i, t in enumerate(types)]
        answer = sorted(p.number for p in ports if p.port_type == PortType.OPEN)

        state = cls(
            ports=ports,
            answer=answer,
            sequence_slots=[None] * NUM_OPEN,
        )
        state.message = "Scan ports to find the access sequence"
        return state

    @classmethod
    def from_types(cls, types: list[PortType]) -> PortScanState:
        """Create a state from an explicit type list (for testing)."""
        ports = [Port(number=i + 1, port_type=t) for i, t in enumerate(types)]
        answer = sorted(p.number for p in ports if p.port_type == PortType.OPEN)
        state = cls(
            ports=ports,
            answer=answer,
            sequence_slots=[None] * len(answer),
        )
        state.message = "Scan ports to find the access sequence"
        return state


# ── TUI App ──────────────────────────────────────────────────────────


class PortScanApp:
    """TUI app for the port scanner minigame."""

    tick_interval_ms: int = 100  # fast ticks for smooth countdown

    def __init__(self, state: PortScanState | None = None) -> None:
        self.state = state or PortScanState.new_game()
        self.width = 80
        self.height = 24

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key in ("C-c",):
            return None

        s = self.state

        # ── Won / Lost ───────────────────────────────────────────
        if s.phase in (Phase.WON, Phase.LOST):
            if key == "Enter":
                self.state = PortScanState.new_game()
            elif key in ("q", "Escape"):
                return None
            return self._render()

        # ── Lockout — ignore all keys ────────────────────────────
        if s.phase == Phase.LOCKOUT:
            return self._render()

        # ── Scanning phase ───────────────────────────────────────
        if s.phase == Phase.SCANNING:
            return self._handle_scanning(key)

        # ── Sequence entry ───────────────────────────────────────
        if s.phase == Phase.SEQUENCE:
            return self._handle_sequence(key)

        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    def on_tick(self, dt_ms: int) -> ScreenBuffer | None:
        s = self.state
        if s.phase != Phase.LOCKOUT:
            return None

        s.lockout_remaining_ms = max(0, s.lockout_remaining_ms - dt_ms)
        if s.lockout_remaining_ms <= 0:
            s.phase = Phase.SEQUENCE
            s.message = f"Enter the {NUM_OPEN}-port access sequence"
        return self._render()

    # ── Key handlers ─────────────────────────────────────────────

    def _handle_scanning(self, key: str) -> ScreenBuffer | None:
        s = self.state

        if key == "ArrowLeft":
            if s.cursor % GRID_COLS > 0:
                s.cursor -= 1
        elif key == "ArrowRight":
            if s.cursor % GRID_COLS < GRID_COLS - 1:
                s.cursor += 1
        elif key == "ArrowUp":
            if s.cursor >= GRID_COLS:
                s.cursor -= GRID_COLS
        elif key == "ArrowDown":
            if s.cursor + GRID_COLS < NUM_PORTS:
                s.cursor += GRID_COLS
        elif key in ("Enter", " "):
            self._scan_port()
        elif key == "Tab":
            # Switch to sequence entry if at least one scan done
            if s.scans_remaining < MAX_SCANS:
                s.phase = Phase.SEQUENCE
                s.seq_cursor = 0
                s.message = f"Enter the {NUM_OPEN}-port access sequence"
        elif key in ("q", "Escape"):
            return None

        return self._render()

    def _handle_sequence(self, key: str) -> ScreenBuffer | None:
        s = self.state

        if key == "ArrowLeft":
            s.seq_cursor = max(0, s.seq_cursor - 1)
        elif key == "ArrowRight":
            s.seq_cursor = min(len(s.sequence_slots) - 1, s.seq_cursor + 1)
        elif key in "0123456789":
            self._type_digit(key)
        elif key == "Backspace":
            s.sequence_slots[s.seq_cursor] = None
            s.message = ""
        elif key == "Enter":
            self._submit_sequence()
        elif key == "Tab":
            s.phase = Phase.SCANNING
            s.message = "Scan ports to find the access sequence"
        elif key in ("q", "Escape"):
            return None

        return self._render()

    # ── Actions ──────────────────────────────────────────────────

    def _scan_port(self) -> None:
        s = self.state
        port = s.ports[s.cursor]

        if port.scanned:
            s.message = f"Port {port.number} already scanned"
            return

        if s.scans_remaining <= 0:
            s.message = "No scans remaining! Press Tab to enter sequence"
            return

        port.scanned = True
        s.scans_remaining -= 1
        label = _PORT_LABEL[port.port_type]
        s.message = f"Port {port.number}: {label}"

    def _type_digit(self, digit: str) -> None:
        s = self.state
        current = s.sequence_slots[s.seq_cursor]
        val = int(digit) if current is None else current * 10 + int(digit)

        if val < 1 or val > NUM_PORTS:
            s.message = f"Port numbers are 1-{NUM_PORTS}"
            return

        s.sequence_slots[s.seq_cursor] = val
        # Auto-advance
        if s.seq_cursor < len(s.sequence_slots) - 1:
            s.seq_cursor += 1
        s.message = ""

    def _submit_sequence(self) -> None:
        s = self.state

        if any(v is None for v in s.sequence_slots):
            s.message = "Fill all slots before submitting"
            return

        guess = [v for v in s.sequence_slots if v is not None]

        if guess == s.answer:
            s.phase = Phase.WON
            s.message = (
                f"{GREEN}{BOLD}*** ACCESS GRANTED ***{RESET}  "
                f"Sequence cracked!  "
                f"[Enter] New Game  [Esc] Quit"
            )
            return

        s.attempts_remaining -= 1

        if s.attempts_remaining <= 0:
            s.phase = Phase.LOST
            answer_str = " ".join(str(n) for n in s.answer)
            s.message = (
                f"{RED}{BOLD}*** LOCKOUT ***{RESET}  "
                f"Sequence was [{answer_str}]  "
                f"[Enter] New Game  [Esc] Quit"
            )
            return

        # Wrong guess — lockout countdown
        in_answer = sum(1 for g in guess if g in s.answer)
        s.message = (
            f"{YELLOW}Wrong sequence!{RESET} "
            f"{in_answer}/{len(s.answer)} ports correct. "
            f"Lockout in progress..."
        )
        s.lockout_remaining_ms = LOCKOUT_DURATION_MS
        s.phase = Phase.LOCKOUT
        # Reset slots for next attempt
        s.sequence_slots = [None] * len(s.answer)
        s.seq_cursor = 0

    # ── Rendering ────────────────────────────────────────────────

    def _render(self) -> ScreenBuffer:
        screen = ScreenBuffer.create(self.width, self.height)
        screen.cursor_visible = False
        s = self.state

        # Title
        screen.center_text(0, "=== PORT SCANNER ===", style=f"{BOLD}{CYAN}")
        screen.center_text(
            1,
            f"Scan ports to find the {NUM_OPEN}-port access sequence",
            style=DIM,
        )

        # Port grid
        grid_start_row = 3
        cell_width = 8
        grid_pixel_width = GRID_COLS * cell_width
        grid_left = max(2, (self.width - grid_pixel_width) // 2)

        for row_idx in range(GRID_ROWS):
            row = grid_start_row + row_idx * 2
            for col_idx in range(GRID_COLS):
                port_idx = row_idx * GRID_COLS + col_idx
                port = s.ports[port_idx]

                is_cursor = port_idx == s.cursor and s.phase == Phase.SCANNING

                cell_text = self._render_port_cell(port, is_cursor)
                col = grid_left + col_idx * cell_width
                screen.set_region(row, col, cell_width, cell_text)

        # Stats bar
        stats_row = grid_start_row + GRID_ROWS * 2 + 1
        scans_color = (
            GREEN
            if s.scans_remaining > 1
            else (YELLOW if s.scans_remaining == 1 else RED)
        )
        attempts_color = (
            GREEN
            if s.attempts_remaining > 1
            else (YELLOW if s.attempts_remaining == 1 else RED)
        )
        screen.set_line(
            stats_row,
            f"  Scans: {scans_color}{BOLD}{s.scans_remaining}/{MAX_SCANS}{RESET}"
            f"    Attempts: {attempts_color}{BOLD}{s.attempts_remaining}/{MAX_ATTEMPTS}{RESET}",
        )

        # Phase-specific rendering
        seq_row = stats_row + 2

        if s.phase == Phase.SEQUENCE:
            self._render_sequence_entry(screen, seq_row)
        elif s.phase == Phase.LOCKOUT:
            secs = (s.lockout_remaining_ms + 999) // 1000
            bar_width = 20
            filled = int(s.lockout_remaining_ms / LOCKOUT_DURATION_MS * bar_width)
            bar = f"[{RED}{'#' * filled}{DIM}{'.' * (bar_width - filled)}{RESET}]"
            screen.set_line(
                seq_row,
                f"  {YELLOW}{BOLD}LOCKOUT{RESET} {bar} {secs}s",
            )
        elif s.phase == Phase.WON:
            screen.center_text(
                seq_row,
                "ACCESS GRANTED",
                style=f"{BOLD}{GREEN}",
            )
        elif s.phase == Phase.LOST:
            answer_str = " ".join(str(n) for n in s.answer)
            screen.center_text(
                seq_row,
                f"LOCKED OUT  [sequence: {answer_str}]",
                style=f"{BOLD}{RED}",
            )

        # Legend
        legend_row = self.height - 4
        screen.set_line(
            legend_row,
            f"  {GREEN}{BOLD}OPEN{RESET}=access port  "
            f"{DIM}SHUT{RESET}=closed  "
            f"{RED}{BOLD}TRAP{RESET}=decoy",
        )

        # Message
        screen.set_line(self.height - 3, f"  {s.message}")

        # Controls
        if s.phase == Phase.SCANNING:
            controls = "[arrows] Move  [Enter] Scan  [Tab] Enter sequence  [q] Quit"
        elif s.phase == Phase.SEQUENCE:
            controls = "[arrows] Move  [0-9] Type  [Backspace] Clear  [Enter] Submit  [Tab] Back  [q] Quit"
        elif s.phase == Phase.LOCKOUT:
            controls = "Please wait..."
        else:
            controls = "[Enter] New Game  [Esc] Quit"

        screen.set_line(
            self.height - 2,
            f"  {DIM}{controls}{RESET}",
        )

        return screen

    def _render_port_cell(self, port: Port, is_cursor: bool) -> str:
        """Render a single port cell."""
        if port.scanned:
            style = _PORT_STYLE[port.port_type]
            label = _PORT_LABEL[port.port_type]
            inner = f"{style}{label:^4}{RESET}"
        else:
            inner = f" {port.number:02d} "

        if is_cursor:
            return f"\033[7m[{inner}\033[7m]{RESET} "
        return f"[{inner}] "

    def _render_sequence_entry(self, screen: ScreenBuffer, row: int) -> None:
        """Render the sequence input slots."""
        s = self.state
        parts: list[str] = []
        for i, val in enumerate(s.sequence_slots):
            is_active = i == s.seq_cursor
            text = f"{val:02d}" if val is not None else "__"

            if is_active:
                parts.append(f"\033[7m[{text}]{RESET}")
            else:
                parts.append(f"[{text}]")

        screen.set_line(
            row,
            f"  Sequence: {' '.join(parts)}",
        )


# ── Shell registration ────────────────────────────────────────────────


def register_portscan_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "portscan",
        _run_portscan,
        "Port scanner minigame — find the access sequence!\n\n"
        "Usage: portscan\n\n"
        "Scan a grid of network ports to identify which are open,\n"
        "closed, or decoys, then enter the correct access sequence\n"
        "before getting locked out.\n\n"
        "Keys (scanning):\n"
        "  Arrows   Move cursor\n"
        "  Enter    Scan selected port\n"
        "  Tab      Switch to sequence entry\n"
        "  q        Quit\n\n"
        "Keys (sequence entry):\n"
        "  0-9      Enter port number\n"
        "  Bksp     Clear slot\n"
        "  Enter    Submit sequence\n"
        "  Tab      Back to scanning",
    )


async def _run_portscan(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("portscan: requires a terminal that supports TUI mode")
        return 1
    app = PortScanApp()
    return await ctx.run_tui(app)
