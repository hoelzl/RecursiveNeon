"""
Kill ring — Emacs-style clipboard with rotation.

The kill ring stores recently killed (cut) text.  ``yank`` retrieves
the most recent entry; ``rotate`` cycles through older entries.
Consecutive kill commands merge their text into the top entry.
"""

from __future__ import annotations


class KillRing:
    """A circular list of killed text strings."""

    def __init__(self, max_size: int = 60) -> None:
        self.entries: list[str] = []
        self.max_size = max_size
        self._yank_index: int = 0

    @property
    def empty(self) -> bool:
        return len(self.entries) == 0

    def push(self, text: str) -> None:
        """Push new text onto the kill ring."""
        if not text:
            return
        self.entries.insert(0, text)
        if len(self.entries) > self.max_size:
            self.entries.pop()
        self._yank_index = 0

    def append_to_top(self, text: str, *, before: bool = False) -> None:
        """Append text to the most recent kill ring entry.

        Used for consecutive kill commands: ``before=False`` appends
        (kill-forward), ``before=True`` prepends (kill-backward).
        """
        if not text:
            return
        if self.entries:
            if before:
                self.entries[0] = text + self.entries[0]
            else:
                self.entries[0] = self.entries[0] + text
        else:
            self.push(text)

    def yank(self) -> str | None:
        """Return the most recent kill, or None if empty."""
        if not self.entries:
            return None
        self._yank_index = 0
        return self.entries[0]

    def rotate(self) -> str | None:
        """Rotate the yank pointer and return the next entry.

        Call after ``yank`` to cycle through older kills.  Returns
        None if the ring is empty.
        """
        if not self.entries:
            return None
        self._yank_index = (self._yank_index + 1) % len(self.entries)
        return self.entries[self._yank_index]

    @property
    def yank_index(self) -> int:
        return self._yank_index

    @property
    def top(self) -> str | None:
        """The most recent entry, or None."""
        return self.entries[0] if self.entries else None
