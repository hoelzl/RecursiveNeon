"""
Minibuffer — one-line input area for interactive prompts.

The minibuffer is used for M-x (command-by-name), C-x C-f (find file),
C-x C-w (write file), C-x b (switch buffer), and incremental search.

It supports:
- Basic text editing (insert, backspace, C-a/C-e, C-k)
- Tab completion (cycles through candidates)
- A callback invoked on Enter
- C-g cancels

The minibuffer is NOT a full Buffer — it's a lightweight input widget
that intercepts keystrokes when active.
"""

from __future__ import annotations

from typing import Callable

# Completer: given the current input text, returns a list of candidates
CompleterFn = Callable[[str], list[str]]


class Minibuffer:
    """One-line text input with prompt, editing, and completion."""

    def __init__(
        self,
        prompt: str,
        callback: Callable[[str], None],
        *,
        completer: CompleterFn | None = None,
        initial: str = "",
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        self.prompt = prompt
        self.callback = callback
        self.completer = completer
        self.on_change = on_change  # called on each keystroke (for isearch)
        self.text = initial
        self.cursor: int = len(initial)
        self._completions: list[str] = []
        self._completion_index: int = -1
        self._cancelled: bool = False
        self._last_was_tab: bool = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def display(self) -> str:
        """The full display string (prompt + input text)."""
        return self.prompt + self.text

    def process_key(self, key: str) -> bool:
        """Process a keystroke.

        Returns True if the minibuffer is still active, False if it
        should be dismissed (Enter or C-g).
        """
        if key != "Tab":
            self._completions = []
            self._completion_index = -1

        if key == "Enter":
            self.callback(self.text)
            return False

        if key == "C-g" or key == "Escape":
            self._cancelled = True
            return False

        if key == "Tab":
            self._complete()
            return True

        if key == "Backspace":
            if self.cursor > 0:
                self.text = self.text[: self.cursor - 1] + self.text[self.cursor :]
                self.cursor -= 1
                self._notify_change()
            return True

        if key == "C-a" or key == "Home":
            self.cursor = 0
            return True

        if key == "C-e" or key == "End":
            self.cursor = len(self.text)
            return True

        if key == "C-k":
            self.text = self.text[: self.cursor]
            self._notify_change()
            return True

        if key == "C-d" or key == "Delete":
            if self.cursor < len(self.text):
                self.text = self.text[: self.cursor] + self.text[self.cursor + 1 :]
                self._notify_change()
            return True

        if key == "ArrowLeft" or key == "C-b":
            if self.cursor > 0:
                self.cursor -= 1
            return True

        if key == "ArrowRight" or key == "C-f":
            if self.cursor < len(self.text):
                self.cursor += 1
            return True

        # Self-insert for printable characters
        if len(key) == 1 and key.isprintable():
            self.text = self.text[: self.cursor] + key + self.text[self.cursor :]
            self.cursor += 1
            self._notify_change()
            return True

        # Unknown key — ignore
        return True

    def _complete(self) -> None:
        """Cycle through tab completions."""
        if self.completer is None:
            return

        if not self._completions:
            self._completions = self.completer(self.text)
            self._completion_index = -1

        if not self._completions:
            return

        self._completion_index = (self._completion_index + 1) % len(self._completions)
        self.text = self._completions[self._completion_index]
        self.cursor = len(self.text)

    def _notify_change(self) -> None:
        """Call the on_change callback if set."""
        if self.on_change is not None:
            self.on_change(self.text)
