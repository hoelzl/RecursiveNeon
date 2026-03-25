"""
CodeBreaker — a Mastermind-style TUI minigame.

Crack the 4-symbol code from 6 possible symbols in 10 attempts.
After each guess, feedback shows exact (correct position) and
partial (right symbol, wrong position) matches.

Launched via the ``codebreaker`` shell command.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from recursive_neon.shell.output import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    YELLOW,
)
from recursive_neon.shell.programs import ProgramContext, ProgramRegistry
from recursive_neon.shell.tui import ScreenBuffer

SYMBOLS = ["R", "G", "B", "Y", "M", "C"]
CODE_LENGTH = 4
MAX_GUESSES = 10

# ANSI colors for each symbol — cyberpunk palette
SYMBOL_COLORS = {
    "R": RED,
    "G": GREEN,
    "B": "\033[94m",  # bright blue
    "Y": YELLOW,
    "M": MAGENTA,
    "C": CYAN,
}


@dataclass
class CodeBreakerState:
    """Mutable game state for CodeBreaker."""

    secret: list[str]
    guesses: list[list[str]] = field(default_factory=list)
    feedback: list[tuple[int, int]] = field(default_factory=list)
    current_input: list[str] = field(default_factory=list)
    cursor_pos: int = 0
    game_over: bool = False
    won: bool = False
    message: str = ""

    @classmethod
    def new_game(cls) -> CodeBreakerState:
        return cls(secret=[random.choice(SYMBOLS) for _ in range(CODE_LENGTH)])

    def check_guess(self, guess: list[str]) -> tuple[int, int]:
        """Return (exact_matches, partial_matches)."""
        exact = sum(1 for a, b in zip(self.secret, guess, strict=True) if a == b)

        secret_counts: dict[str, int] = {}
        guess_counts: dict[str, int] = {}
        for i in range(CODE_LENGTH):
            if self.secret[i] != guess[i]:
                secret_counts[self.secret[i]] = secret_counts.get(self.secret[i], 0) + 1
                guess_counts[guess[i]] = guess_counts.get(guess[i], 0) + 1

        partial = sum(
            min(secret_counts.get(s, 0), guess_counts.get(s, 0))
            for s in set(guess_counts)
        )
        return exact, partial


class CodeBreakerApp:
    """TUI app for the CodeBreaker minigame."""

    def __init__(self, secret: list[str] | None = None) -> None:
        if secret is not None:
            self.state = CodeBreakerState(secret=list(secret))
        else:
            self.state = CodeBreakerState.new_game()
        self.width = 80
        self.height = 24

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        self.state.message = "Select symbols with arrow keys, Enter to submit"
        return self._render()

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key in ("Escape", "C-c"):
            return None

        if self.state.game_over:
            if key == "Enter":
                self.state = CodeBreakerState.new_game()
                self.state.message = "New game! Select symbols."
            elif key in ("q", "Escape"):
                return None
            return self._render()

        if key == "ArrowLeft":
            self.state.cursor_pos = max(0, self.state.cursor_pos - 1)
        elif key == "ArrowRight":
            self.state.cursor_pos = min(CODE_LENGTH - 1, self.state.cursor_pos + 1)
        elif key == "ArrowUp":
            self._cycle_symbol(1)
        elif key == "ArrowDown":
            self._cycle_symbol(-1)
        elif key.upper() in SYMBOLS:
            self._set_symbol(key.upper())
        elif key == "Enter":
            self._submit_guess()
        elif key == "Backspace":
            self._clear_current()

        return self._render()

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.width = width
        self.height = height
        return self._render()

    # ── internal ──────────────────────────────────────────────────────

    def _render(self) -> ScreenBuffer:
        """Build the full screen."""
        screen = ScreenBuffer.create(self.width, self.height)

        # Title
        screen.center_text(0, "=== CODEBREAKER ===", style=f"{BOLD}{CYAN}")
        screen.center_text(
            1,
            f"Crack the {CODE_LENGTH}-symbol code  |  "
            f"{len(SYMBOLS)} symbols  |  {MAX_GUESSES} attempts",
            style=DIM,
        )

        # Symbol legend with colors
        legend_parts = []
        for s in SYMBOLS:
            color = SYMBOL_COLORS.get(s, "")
            legend_parts.append(f"{color}{BOLD}{s}{RESET}")
        screen.set_line(3, "  Symbols: " + "  ".join(legend_parts))

        # Previous guesses
        row = 5
        for i, (guess, (exact, partial)) in enumerate(
            zip(self.state.guesses, self.state.feedback, strict=True)
        ):
            guess_parts = []
            for s in guess:
                color = SYMBOL_COLORS.get(s, "")
                guess_parts.append(f"{color}{BOLD}{s}{RESET}")
            guess_str = " ".join(guess_parts)

            dots = (
                f"{GREEN}●{RESET}" * exact
                + f"{YELLOW}○{RESET}" * partial
                + f"{DIM}·{RESET}" * (CODE_LENGTH - exact - partial)
            )
            screen.set_line(row + i, f"  {i + 1:2d}. [{guess_str}]  {dots}")

        # Current input row
        input_row = row + len(self.state.guesses)
        slots: list[str] = []
        for j in range(CODE_LENGTH):
            if j < len(self.state.current_input):
                s = self.state.current_input[j]
                color = SYMBOL_COLORS.get(s, "")
                display = f"{color}{BOLD}{s}{RESET}"
            else:
                display = f"{DIM}_{RESET}"

            if j == self.state.cursor_pos:
                display = f"\033[7m{display}\033[27m"  # reverse video

            slots.append(display)

        attempt_num = len(self.state.guesses) + 1
        screen.set_line(input_row, f"  {attempt_num:2d}. [{' '.join(slots)}]")

        # Status message
        screen.set_line(self.height - 3, f"  {self.state.message}")

        # Controls
        screen.set_line(
            self.height - 2,
            f"  {DIM}[←→] Move  [↑↓] Cycle  "
            f"[R/G/B/Y/M/C] Set  [Enter] Submit  [Esc] Quit{RESET}",
        )

        return screen

    def _cycle_symbol(self, direction: int) -> None:
        while len(self.state.current_input) <= self.state.cursor_pos:
            self.state.current_input.append(SYMBOLS[0])
        current = self.state.current_input[self.state.cursor_pos]
        idx = SYMBOLS.index(current) if current in SYMBOLS else 0
        idx = (idx + direction) % len(SYMBOLS)
        self.state.current_input[self.state.cursor_pos] = SYMBOLS[idx]

    def _set_symbol(self, symbol: str) -> None:
        while len(self.state.current_input) <= self.state.cursor_pos:
            self.state.current_input.append(SYMBOLS[0])
        self.state.current_input[self.state.cursor_pos] = symbol
        if self.state.cursor_pos < CODE_LENGTH - 1:
            self.state.cursor_pos += 1

    def _clear_current(self) -> None:
        self.state.current_input = []
        self.state.cursor_pos = 0

    def _submit_guess(self) -> None:
        if len(self.state.current_input) < CODE_LENGTH:
            self.state.message = f"Need {CODE_LENGTH} symbols! Fill all slots."
            return

        guess = list(self.state.current_input[:CODE_LENGTH])
        exact, partial = self.state.check_guess(guess)
        self.state.guesses.append(guess)
        self.state.feedback.append((exact, partial))
        self.state.current_input = []
        self.state.cursor_pos = 0

        if exact == CODE_LENGTH:
            self.state.won = True
            self.state.game_over = True
            tries = len(self.state.guesses)
            self.state.message = (
                f"{GREEN}{BOLD}*** ACCESS GRANTED ***{RESET}  "
                f"Cracked in {tries} {'try' if tries == 1 else 'tries'}!  "
                f"[Enter] New Game  [Esc] Quit"
            )
        elif len(self.state.guesses) >= MAX_GUESSES:
            self.state.game_over = True
            secret_parts = []
            for s in self.state.secret:
                color = SYMBOL_COLORS.get(s, "")
                secret_parts.append(f"{color}{BOLD}{s}{RESET}")
            secret_str = " ".join(secret_parts)
            self.state.message = (
                f"{RED}{BOLD}*** ACCESS DENIED ***{RESET}  "
                f"Code was [{secret_str}]  "
                f"[Enter] New Game  [Esc] Quit"
            )
        else:
            remaining = MAX_GUESSES - len(self.state.guesses)
            self.state.message = (
                f"{exact} exact, {partial} partial.  "
                f"{remaining} {'attempt' if remaining == 1 else 'attempts'} left."
            )


# ── Shell registration ────────────────────────────────────────────────


def register_codebreaker_program(registry: ProgramRegistry) -> None:
    registry.register_fn(
        "codebreaker",
        _run_codebreaker,
        "CodeBreaker minigame — crack the access code!\n\n"
        "Usage: codebreaker\n\n"
        "A Mastermind-style puzzle. Guess the 4-symbol code\n"
        "from 6 possible symbols (R G B Y M C) in 10 attempts.\n"
        "After each guess, feedback shows:\n"
        "  ● exact match (right symbol, right position)\n"
        "  ○ partial match (right symbol, wrong position)\n"
        "  · no match",
    )


async def _run_codebreaker(ctx: ProgramContext) -> int:
    if ctx.run_tui is None:
        ctx.stderr.error("codebreaker: requires a terminal that supports TUI mode")
        return 1
    app = CodeBreakerApp()
    return await ctx.run_tui(app)
