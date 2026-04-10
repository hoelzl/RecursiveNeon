"""
memdump — memory dump minigame TUI.

Hex viewer of a generated memory region with hidden patterns.
Player searches for patterns using find-as-you-type highlighting
and must find all of them within a limited move budget.

Launched via the ``memdump`` shell command.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from recursive_neon.shell.output import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.tui import ScreenBuffer

# ── Constants ────────────────────────────────────────────────────────

MEM_SIZE = 256  # bytes
BYTES_PER_ROW = 16
NUM_ROWS = MEM_SIZE // BYTES_PER_ROW
MAX_MOVES = 40
BASE_ADDRESS = 0x0A00

# Patterns the player must find — cyberpunk themed
PATTERN_POOL = [
    "ROOT",
    "KEY",
    "ADMIN",
    "EXEC",
    "AUTH",
    "DAEMON",
    "PROXY",
    "CRYPT",
    "SHELL",
    "SUDO",
    "TRACE",
    "NODE",
    "PORT",
    "BOOT",
    "HACK",
]
NUM_PATTERNS = 3


# ── Data types ───────────────────────────────────────────────────────


class Phase(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class HiddenPattern:
    """A pattern embedded in the memory region."""

    text: str
    offset: int  # byte offset where the pattern starts
    found: bool = False


# ── Game state ───────────────────────────────────────────────────────


@dataclass
class MemDumpState:
    """Mutable game state for the memory dump minigame."""

    memory: bytearray
    patterns: list[HiddenPattern]
    phase: Phase = Phase.PLAYING
    search: str = ""
    moves_remaining: int = MAX_MOVES
    scroll_offset: int = 0  # row offset for scrolling
    message: str = ""

    @classmethod
    def new_game(cls, *, rng: random.Random | None = None) -> MemDumpState:
        r = rng or random.Random()
        return _generate_game(r)

    @classmethod
    def from_patterns(
        cls,
        patterns: list[tuple[str, int]],
        *,
        rng: random.Random | None = None,
    ) -> MemDumpState:
        """Create a game with specific patterns at specific offsets (for testing)."""
        r = rng or random.Random()
        mem = bytearray(r.getrandbits(8) for _ in range(MEM_SIZE))

        hidden: list[HiddenPattern] = []
        for text, offset in patterns:
            encoded = text.encode("ascii")
            if offset < 0 or offset + len(encoded) > MEM_SIZE:
                raise ValueError(
                    f"Pattern {text!r} at offset {offset} exceeds memory bounds"
                )
            mem[offset : offset + len(encoded)] = encoded
            hidden.append(HiddenPattern(text=text, offset=offset))

        return cls(
            memory=mem,
            patterns=hidden,
            message=f"Find {len(hidden)} hidden patterns",
        )

    @property
    def found_count(self) -> int:
        return sum(1 for p in self.patterns if p.found)

    @property
    def total_patterns(self) -> int:
        return len(self.patterns)

    def match_offsets(self) -> list[int]:
        """Return byte offsets where the current search string matches in memory."""
        if not self.search:
            return []
        needle = self.search.encode("ascii")
        offsets: list[int] = []
        for i in range(MEM_SIZE - len(needle) + 1):
            if self.memory[i : i + len(needle)] == needle:
                offsets.append(i)
        return offsets

    def pattern_offsets(self) -> set[int]:
        """Return all byte offsets that are part of a found pattern."""
        result: set[int] = set()
        for p in self.patterns:
            if p.found:
                for i in range(len(p.text)):
                    result.add(p.offset + i)
        return result


def _generate_game(rng: random.Random) -> MemDumpState:
    """Generate a new game with random memory and embedded patterns."""
    mem = bytearray(rng.getrandbits(8) for _ in range(MEM_SIZE))

    # Pick patterns
    chosen = rng.sample(PATTERN_POOL, NUM_PATTERNS)
    patterns: list[HiddenPattern] = []

    for text in chosen:
        encoded = text.encode("ascii")
        placed = False
        for _ in range(100):
            offset = rng.randint(0, MEM_SIZE - len(encoded))
            # Check no overlap with existing patterns
            conflict = False
            for existing in patterns:
                ex_start = existing.offset
                ex_end = ex_start + len(existing.text)
                new_end = offset + len(encoded)
                if not (new_end <= ex_start or offset >= ex_end):
                    conflict = True
                    break
            if not conflict:
                mem[offset : offset + len(encoded)] = encoded
                patterns.append(HiddenPattern(text=text, offset=offset))
                placed = True
                break
        if not placed:  # pragma: no cover
            # Fallback: scan from the end for a non-overlapping position
            for fallback_off in range(MEM_SIZE - len(encoded), -1, -1):
                fb_end = fallback_off + len(encoded)
                fb_conflict = False
                for existing in patterns:
                    ex_start = existing.offset
                    ex_end = ex_start + len(existing.text)
                    if not (fb_end <= ex_start or fallback_off >= ex_end):
                        fb_conflict = True
                        break
                if not fb_conflict:
                    offset = fallback_off
                    break
            else:
                offset = MEM_SIZE - len(encoded)
            mem[offset : offset + len(encoded)] = encoded
            patterns.append(HiddenPattern(text=text, offset=offset))

    return MemDumpState(
        memory=mem,
        patterns=patterns,
        message=f"Find {len(patterns)} hidden patterns",
    )


# ── TUI App ──────────────────────────────────────────────────────────


class MemDumpApp:
    """TUI app for the memory dump minigame."""

    tick_interval_ms: int = 0

    def __init__(self, state: MemDumpState | None = None) -> None:
        self.state = state or MemDumpState.new_game()
        self.width = 80
        self.height = 24

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key == "C-c":
            return None

        s = self.state

        # ── Won / Lost ───────────────────────────────────────────
        if s.phase in (Phase.WON, Phase.LOST):
            if key == "Enter":
                self.state = MemDumpState.new_game()
            elif key in ("q", "Escape"):
                return None
            return self._render()

        # ── Playing ──────────────────────────────────────────────

        # Deferred loss check: when the move budget is exhausted, only
        # Enter (free) is still allowed so the player can confirm a
        # pattern they just finished typing.
        if s.moves_remaining <= 0 and key != "Enter":
            if key in ("q", "Escape", "ArrowUp", "ArrowDown"):
                pass  # allow navigation / exit below
            else:
                self._check_loss()
                return self._render()

        if key in ("q", "Escape"):
            if s.search:
                # Clear search first
                s.search = ""
                s.message = ""
                return self._render()
            return None

        if key == "Enter":
            self._confirm_find()
        elif key == "Backspace":
            if s.search:
                s.search = s.search[:-1]
                s.moves_remaining -= 1
                s.message = ""
        elif key == "ArrowUp":
            s.scroll_offset = max(0, s.scroll_offset - 1)
        elif key == "ArrowDown":
            max_scroll = max(0, NUM_ROWS - self._visible_rows())
            s.scroll_offset = min(max_scroll, s.scroll_offset + 1)
        elif len(key) == 1 and key.isprintable():
            s.search += key
            s.moves_remaining -= 1
            s.message = ""

        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        max_scroll = max(0, NUM_ROWS - self._visible_rows())
        self.state.scroll_offset = min(self.state.scroll_offset, max_scroll)
        return self._render()

    # ── Actions ──────────────────────────────────────────────────

    def _confirm_find(self) -> None:
        s = self.state
        if not s.search:
            s.message = "Type a pattern to search for"
            return

        # Check if search matches any unfound pattern
        for p in s.patterns:
            if not p.found and p.text == s.search:
                p.found = True
                s.search = ""
                if s.found_count == s.total_patterns:
                    s.phase = Phase.WON
                    s.message = (
                        f"{GREEN}{BOLD}*** DATA EXTRACTED ***{RESET}  "
                        f"All patterns found!  "
                        f"[Enter] New Game  [Esc] Quit"
                    )
                else:
                    remaining = s.total_patterns - s.found_count
                    s.message = f"{GREEN}Pattern found!{RESET} {remaining} remaining"
                return

        # Check if it matches in memory but isn't a target pattern
        offsets = s.match_offsets()
        if offsets:
            s.message = f"{YELLOW}Not a target pattern{RESET}"
        else:
            s.message = f"{RED}No match in memory{RESET}"

    def _check_loss(self) -> None:
        s = self.state
        if s.moves_remaining <= 0 and s.found_count < s.total_patterns:
            s.phase = Phase.LOST
            unfound = [p.text for p in s.patterns if not p.found]
            s.message = (
                f"{RED}{BOLD}*** OUT OF MOVES ***{RESET}  "
                f"Missing: {', '.join(unfound)}  "
                f"[Enter] New Game  [Esc] Quit"
            )

    def _visible_rows(self) -> int:
        """Number of hex dump rows visible in the current terminal."""
        # Reserve: 2 title + 1 blank + hex rows + 1 blank + 2 search + 2 status + 2 controls
        return max(4, self.height - 10)

    # ── Rendering ────────────────────────────────────────────────

    def _render(self) -> ScreenBuffer:
        screen = ScreenBuffer.create(self.width, self.height)
        screen.cursor_visible = False
        s = self.state

        # Title
        screen.center_text(0, "=== MEMORY DUMP ===", style=f"{BOLD}{CYAN}")
        screen.center_text(
            1,
            f"Find {s.total_patterns} hidden patterns in the memory region",
            style=DIM,
        )

        # Hex dump
        hex_start_row = 3
        visible = self._visible_rows()
        match_offsets = s.match_offsets()
        match_set = self._build_match_set(match_offsets)
        found_set = s.pattern_offsets()

        for vi in range(visible):
            row_idx = s.scroll_offset + vi
            if row_idx >= NUM_ROWS:
                break
            screen_row = hex_start_row + vi
            line = self._render_hex_row(row_idx, match_set, found_set)
            screen.set_line(screen_row, line)

        # Scroll indicator
        if visible < NUM_ROWS:
            ind_row = hex_start_row + visible
            shown_end = min(s.scroll_offset + visible, NUM_ROWS)
            screen.set_line(
                ind_row,
                f"  {DIM}rows {s.scroll_offset + 1}-{shown_end}/{NUM_ROWS}{RESET}",
            )

        # Search bar
        search_row = self.height - 5
        cursor_char = "\u2588" if s.phase == Phase.PLAYING else ""  # █ block cursor
        screen.set_line(
            search_row,
            f"  Search: {BOLD}{s.search}{cursor_char}{RESET}",
        )

        # Found patterns
        found_row = self.height - 4
        found_names = [f"{GREEN}{p.text}{RESET}" for p in s.patterns if p.found]
        remaining = s.total_patterns - s.found_count
        found_str = ", ".join(found_names) if found_names else f"{DIM}none{RESET}"
        screen.set_line(
            found_row,
            f"  Found: {found_str}  "
            f"{DIM}({remaining} remaining){RESET}  "
            f"Moves: {self._moves_display()}",
        )

        # Message
        screen.set_line(self.height - 3, f"  {s.message}")

        # Controls
        if s.phase == Phase.PLAYING:
            controls = (
                "[type] Search  [Enter] Confirm  [Esc] Clear  [arrows] Scroll  [q] Quit"
            )
        else:
            controls = "[Enter] New Game  [Esc] Quit"
        screen.set_line(self.height - 2, f"  {DIM}{controls}{RESET}")

        return screen

    def _moves_display(self) -> str:
        s = self.state
        if s.moves_remaining > 15:
            color = GREEN
        elif s.moves_remaining > 5:
            color = YELLOW
        else:
            color = RED
        return f"{color}{BOLD}{s.moves_remaining}/{MAX_MOVES}{RESET}"

    def _build_match_set(self, offsets: list[int]) -> set[int]:
        """Build a set of all byte positions covered by current search matches."""
        if not self.state.search:
            return set()
        length = len(self.state.search)
        result: set[int] = set()
        for off in offsets:
            for i in range(length):
                result.add(off + i)
        return result

    def _render_hex_row(
        self,
        row_idx: int,
        match_set: set[int],
        found_set: set[int],
    ) -> str:
        """Render one row of the hex dump: address | hex bytes | ASCII."""
        base = row_idx * BYTES_PER_ROW
        addr = BASE_ADDRESS + base

        # Address column
        parts: list[str] = [f"  {DIM}{addr:04X}{RESET}  "]

        # Hex bytes
        hex_parts: list[str] = []
        for i in range(BYTES_PER_ROW):
            offset = base + i
            byte = self.state.memory[offset]
            style = self._byte_style(offset, match_set, found_set)

            hex_str = f"{byte:02X}"
            if style:
                hex_parts.append(f"{style}{hex_str}{RESET}")
            else:
                hex_parts.append(hex_str)

            # Extra space between groups of 8
            if i == 7:
                hex_parts.append("")

        parts.append(" ".join(hex_parts))

        # ASCII column
        parts.append("  |")
        for i in range(BYTES_PER_ROW):
            offset = base + i
            byte = self.state.memory[offset]
            ch = chr(byte) if 0x20 <= byte < 0x7F else "."
            style = self._byte_style(offset, match_set, found_set)
            if style:
                parts.append(f"{style}{ch}{RESET}")
            else:
                parts.append(ch)
        parts.append("|")

        return "".join(parts)

    def _byte_style(
        self,
        offset: int,
        match_set: set[int],
        found_set: set[int],
    ) -> str:
        """Return ANSI style for a byte at the given offset."""
        if offset in match_set:
            return f"{BOLD}{YELLOW}\033[7m"  # reverse video highlight
        if offset in found_set:
            return f"{GREEN}"
        return ""


# ── Shell registration ────────────────────────────────────────────────


def register_memdump_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "memdump",
        _run_memdump,
        "Memory dump minigame — find hidden patterns!\n\n"
        "Usage: memdump\n\n"
        "Analyse a hex memory dump to find hidden data patterns.\n"
        "Type to search — matches highlight in real-time.\n"
        "Press Enter to confirm when you've found a target pattern.\n\n"
        "Keys:\n"
        "  [type]     Search for patterns\n"
        "  Enter      Confirm found pattern\n"
        "  Backspace  Delete last character\n"
        "  Esc        Clear search\n"
        "  Up/Down    Scroll hex dump\n"
        "  q          Quit",
    )


async def _run_memdump(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("memdump: requires a terminal that supports TUI mode")
        return 1
    app = MemDumpApp()
    return await ctx.run_tui(app)
