"""
Editor — the central coordinator.

The Editor owns the buffer list, current buffer, global keymap, shared
kill ring, and drives the command dispatch loop.  It processes
keystrokes by resolving them through layered keymaps, handling prefix
key state, and executing the resulting command.

Undo boundaries are inserted automatically between commands.
"""

from __future__ import annotations

from typing import Callable

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.minibuffer import CompleterFn, Minibuffer


class Editor:
    """Top-level editor state and command dispatch."""

    def __init__(self, *, global_keymap: Keymap | None = None) -> None:
        # Buffer management
        self._buffers: list[Buffer] = []
        self._current_index: int = 0

        # Shared kill ring across all buffers
        self.kill_ring = KillRing()

        # Keymap — the global keymap is the root of the lookup chain
        self.global_keymap: Keymap = global_keymap or Keymap("global")

        # Prefix key state: when a prefix keymap is active, the next
        # key is looked up in it instead of the global keymap.
        self._pending_keymap: Keymap | None = None

        # Prefix argument (C-u): None = no prefix, int = numeric arg
        self._prefix_arg: int | None = None
        self._building_prefix: bool = False

        # Message to display (e.g., "C-x-" while waiting for second key)
        self.message: str = ""

        # Whether the editor should keep running
        self.running: bool = True

        # Save callback — set by the hosting environment (e.g., shell
        # program) to write buffer content to the virtual filesystem.
        # Signature: (buffer) -> bool (True if saved successfully).
        self.save_callback: Callable[[Buffer], bool] | None = None

        # Open callback — loads file content from the virtual filesystem.
        # Signature: (path) -> str (file content, or "" for new file).
        self.open_callback: Callable[[str], str] | None = None

        # Minibuffer — active when not None
        self.minibuffer: Minibuffer | None = None

        # Track whether the last command was issued by us so Buffer
        # can correlate consecutive operations (e.g., kill merging)
        self._last_command_name: str = ""

    # ------------------------------------------------------------------
    # Buffer management
    # ------------------------------------------------------------------

    @property
    def buffer(self) -> Buffer:
        """The current buffer."""
        if not self._buffers:
            self.create_buffer()
        return self._buffers[self._current_index]

    @property
    def buffers(self) -> list[Buffer]:
        return list(self._buffers)

    def create_buffer(
        self,
        name: str = "*scratch*",
        text: str = "",
        *,
        filepath: str | None = None,
    ) -> Buffer:
        """Create a new buffer and make it current."""
        buf = Buffer(name=name, text=text, filepath=filepath)
        buf.kill_ring = self.kill_ring  # share the kill ring
        self._buffers.append(buf)
        self._current_index = len(self._buffers) - 1
        return buf

    def switch_to_buffer(self, name: str) -> bool:
        """Switch to an existing buffer by name.  Returns False if not found."""
        for i, buf in enumerate(self._buffers):
            if buf.name == name:
                self._current_index = i
                return True
        return False

    # ------------------------------------------------------------------
    # Key processing
    # ------------------------------------------------------------------

    def process_key(self, key: str) -> None:
        """Process a single keystroke through the keymap and dispatch.

        Handles prefix keys (multi-key sequences), prefix argument
        (C-u), self-insert for printable characters, and command
        execution.  When the minibuffer is active, keystrokes are
        routed there instead.
        """
        # Route to minibuffer if active
        if self.minibuffer is not None:
            still_active = self.minibuffer.process_key(key)
            if not still_active:
                replay = self.minibuffer.replay_key
                if self.minibuffer.cancelled:
                    self.message = "Quit"
                self.minibuffer = None
                # Re-dispatch replayed key (isearch exit-and-replay)
                if replay is not None:
                    self.process_key(replay)
            return

        # Clear previous message (commands can set new ones)
        self.message = ""

        # Handle C-u prefix argument
        if key == "C-u" and not self._pending_keymap:
            self._start_or_extend_prefix_arg()
            return

        if self._building_prefix and key.isdigit():
            self._extend_prefix_digit(key)
            return

        self._building_prefix = False

        # Look up in the active keymap (pending prefix or global)
        keymap = self._pending_keymap or self._resolve_keymap()
        target = keymap.lookup(key)

        if isinstance(target, Keymap):
            # Prefix key — wait for the next keystroke
            self._pending_keymap = target
            self.message = f"{key}-"
            return

        # Was this looked up in a prefix keymap?
        was_prefix = self._pending_keymap is not None
        self._pending_keymap = None

        if isinstance(target, str):
            # Command name — execute it
            self._execute_command_by_name(target)
        elif not was_prefix and len(key) == 1 and key.isprintable():
            # Self-insert for printable characters (only when not
            # in a prefix key sequence — "z" after C-x is undefined,
            # not a self-insert)
            self._execute_command_by_name("self-insert-command", key=key)
        else:
            # Unknown key
            self.message = f"{key} is undefined"
            self._prefix_arg = None

    def _resolve_keymap(self) -> Keymap:
        """Resolve the effective keymap for the current buffer.

        For now this is just the global keymap.  Phase 6a-5 will add
        buffer-local and mode keymaps in front.
        """
        return self.global_keymap

    def _start_or_extend_prefix_arg(self) -> None:
        """Handle C-u: start or multiply the prefix argument."""
        if self._prefix_arg is None:
            self._prefix_arg = 4
        else:
            self._prefix_arg *= 4
        self._building_prefix = True
        self.message = f"C-u {self._prefix_arg}"

    def _extend_prefix_digit(self, digit: str) -> None:
        """Extend the prefix argument with a digit."""
        if self._prefix_arg is not None and self._building_prefix:
            # First digit replaces the default 4
            if self._prefix_arg == 4 and not hasattr(self, "_prefix_has_digits"):
                self._prefix_arg = int(digit)
                self._prefix_has_digits = True
            else:
                self._prefix_arg = self._prefix_arg * 10 + int(digit)
        self.message = f"C-u {self._prefix_arg}"

    def _execute_command_by_name(
        self, name: str, *, key: str | None = None
    ) -> None:
        """Look up and execute a named command."""
        cmd = COMMANDS.get(name)
        if cmd is None:
            self.message = f"Unknown command: {name}"
            self._prefix_arg = None
            return

        # Insert undo boundary between distinct commands
        buf = self.buffer
        if self._last_command_name != name or name != "self-insert-command":
            buf.add_undo_boundary()

        # Stash the key for self-insert-command
        self._current_key = key

        # Execute
        prefix = self._prefix_arg
        self._prefix_arg = None
        self._prefix_has_digits = False

        cmd.function(self, prefix)

        # Update command tracking
        self._last_command_name = name

    # ------------------------------------------------------------------
    # Command helpers
    # ------------------------------------------------------------------

    def execute_command(self, name: str, prefix: int | None = None) -> bool:
        """Execute a named command directly (for programmatic use).

        Returns True if the command was found and executed.
        """
        cmd = COMMANDS.get(name)
        if cmd is None:
            return False
        self.buffer.add_undo_boundary()
        cmd.function(self, prefix)
        self._last_command_name = name
        return True

    def start_minibuffer(
        self,
        prompt: str,
        callback: Callable[[str], None],
        *,
        completer: CompleterFn | None = None,
        initial: str = "",
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        """Activate the minibuffer with the given prompt and callback."""
        self.minibuffer = Minibuffer(
            prompt,
            callback,
            completer=completer,
            initial=initial,
            on_change=on_change,
        )

    def quit(self) -> None:
        """Signal the editor to stop."""
        self.running = False
