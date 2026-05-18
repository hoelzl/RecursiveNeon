"""
Minibuffer — one-line input area for interactive prompts.

The minibuffer is used for M-x (command-by-name), C-x C-f (find file),
C-x C-w (write file), C-x b (switch buffer), and incremental search.

It supports:
- Basic text editing (insert, backspace, C-a/C-e, C-k)
- Tab completion: expand to the longest common prefix of all matches,
  matching GNU Emacs's ``minibuffer-complete``. The full candidate list
  is kept in ``last_completions`` so a future ``*Completions*`` popup
  can render it.
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
        # Last completion attempt's candidate list and a transient status
        # message (e.g. "No match", "Complete, but not unique"). Cleared
        # on the next non-TAB key.
        self.last_completions: list[str] = []
        self.completion_status: str = ""
        self._cancelled: bool = False
        # When set, the Editor should re-dispatch this key after closing
        self.replay_key: str | None = None
        # Per-key handlers for isearch-style overrides (e.g., C-s = repeat)
        self.key_handlers: dict[str, Callable[[], None]] = {}

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def display(self) -> str:
        """The full display string (prompt + input text + status).

        Appends ``" [<status>]"`` when a TAB completion produced a
        transient message — Emacs's TTY puts this hint in the echo area
        alongside the minibuffer; we glue it to the same row.
        """
        suffix = f" [{self.completion_status}]" if self.completion_status else ""
        return self.prompt + self.text + suffix

    def process_key(self, key: str) -> bool:
        """Process a keystroke.

        Returns True if the minibuffer is still active, False if it
        should be dismissed (Enter or C-g).
        """
        if key != "Tab":
            # Any non-TAB key clears the post-completion status hint and
            # discards the previous candidate list.
            self.last_completions = []
            self.completion_status = ""

        # Per-session key handlers (e.g., C-s for isearch-repeat)
        if key in self.key_handlers:
            self.key_handlers[key]()
            return True

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

        # Unknown key: in on_change mode (isearch), exit and replay
        if self.on_change is not None:
            self.callback(self.text)
            self.replay_key = key
            return False

        # Otherwise ignore unknown keys
        return True

    def _complete(self) -> None:
        """Complete to the longest common prefix of matching candidates.

        GNU Emacs's ``minibuffer-complete`` semantics:

        * 0 matches → status ``"No match"``; text unchanged.
        * 1 match  → replace text with the match.
        * 1+ matches sharing a prefix longer than the current text →
          extend text to that prefix.
        * 1+ matches with no further common prefix → status
          ``"Complete, but not unique"``; the full candidate list is kept
          on ``last_completions`` so a future ``*Completions*`` popup can
          render it.
        """
        if self.completer is None:
            return
        matches = self.completer(self.text)
        if not matches:
            self.last_completions = []
            self.completion_status = "No match"
            return
        if len(matches) == 1:
            self.text = matches[0]
            self.cursor = len(self.text)
            self.last_completions = []
            self.completion_status = ""
            return
        common = _common_prefix(matches)
        if len(common) > len(self.text):
            self.text = common
            self.cursor = len(self.text)
            self.last_completions = matches
            self.completion_status = ""
        else:
            # Already at the common prefix.
            self.last_completions = matches
            self.completion_status = "Complete, but not unique"

    def _notify_change(self) -> None:
        """Call the on_change callback if set."""
        if self.on_change is not None:
            self.on_change(self.text)


def _common_prefix(strings: list[str]) -> str:
    """Longest common prefix of a non-empty list of strings."""
    if not strings:
        return ""
    s_min = min(strings)
    s_max = max(strings)
    i = 0
    n = min(len(s_min), len(s_max))
    while i < n and s_min[i] == s_max[i]:
        i += 1
    return s_min[:i]
