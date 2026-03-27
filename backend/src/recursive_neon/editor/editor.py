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
        self._prefix_keys: str = ""  # display string for pending prefix (e.g., "C-x")

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

        # Path completer — returns completion candidates for a partial path.
        # Signature: (partial_path) -> list[str].
        self.path_completer: Callable[[str], list[str]] | None = None

        # Minibuffer — active when not None
        self.minibuffer: Minibuffer | None = None

        # Describe-key mode: when True, next keystroke is described
        self._describing_key: bool = False

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

    def remove_buffer(self, name: str) -> bool:
        """Remove a buffer by name.  Returns False if not found.

        If the removed buffer was current, switches to an adjacent buffer.
        The last buffer cannot be removed — a *scratch* buffer is created
        to replace it.
        """
        for i, buf in enumerate(self._buffers):
            if buf.name == name:
                self._buffers.pop(i)
                if not self._buffers:
                    self.create_buffer()  # always keep at least one
                elif self._current_index >= len(self._buffers):
                    self._current_index = len(self._buffers) - 1
                elif self._current_index > i:
                    self._current_index -= 1
                # Trigger on_focus for the new current buffer
                cur = self._buffers[self._current_index]
                if cur.on_focus is not None:
                    cur.on_focus()
                self.message = f"Killed buffer {name}"
                return True
        self.message = f"No buffer named {name}"
        return False

    def switch_to_buffer(self, name: str) -> bool:
        """Switch to an existing buffer by name.  Returns False if not found."""
        for i, buf in enumerate(self._buffers):
            if buf.name == name:
                self._current_index = i
                if buf.on_focus is not None:
                    buf.on_focus()
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
            old_mb = self.minibuffer
            still_active = old_mb.process_key(key)
            if not still_active:
                replay = old_mb.replay_key
                if old_mb.cancelled:
                    self.message = "Quit"
                # Only clear if the callback didn't start a new minibuffer
                if self.minibuffer is old_mb:
                    self.minibuffer = None
                # Re-dispatch replayed key (isearch exit-and-replay)
                if replay is not None:
                    self.process_key(replay)
            return

        # Describe-key mode: capture the next key and show its binding
        if self._describing_key:
            self._describing_key = False
            self._do_describe_key(key)
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
            self._prefix_keys = (
                f"{self._prefix_keys} {key}" if self._prefix_keys else key
            )
            self.message = f"{self._prefix_keys}-"
            return

        # Was this looked up in a prefix keymap?
        was_prefix = self._pending_keymap is not None
        prefix_display = self._prefix_keys
        self._pending_keymap = None
        self._prefix_keys = ""

        if isinstance(target, str):
            # Command name — execute it
            self._execute_command_by_name(target)
        elif callable(target):
            # Direct callable (e.g., buffer-local action)
            prefix = self._prefix_arg
            self._prefix_arg = None
            self.buffer.add_undo_boundary()
            target(self, prefix)
            self._last_command_name = ""
        elif not was_prefix and len(key) == 1 and key.isprintable():
            # Self-insert for printable characters (only when not
            # in a prefix key sequence — "z" after C-x is undefined,
            # not a self-insert)
            self._execute_command_by_name("self-insert-command", key=key)
        else:
            # Unknown key
            full_key = f"{prefix_display} {key}" if prefix_display else key
            self.message = f"{full_key} is undefined"
            self._prefix_arg = None

    def _resolve_keymap(self) -> Keymap:
        """Resolve the effective keymap for the current buffer.

        If the current buffer has a local keymap it takes priority.
        Its parent should be the global keymap (set up by the creator)
        so unbound keys fall through.
        """
        if self.buffer.keymap is not None:
            return self.buffer.keymap
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

    def _do_describe_key(self, key: str) -> None:
        """Look up what a key is bound to and show in *Help*."""
        keymap = self._resolve_keymap()
        target = keymap.lookup(key)

        if isinstance(target, Keymap):
            # It's a prefix key — wait for the next key to describe the full sequence
            self._describing_key_prefix = key
            self._describing_key_map = target
            self._describing_key = True  # re-enter describe-key mode
            self.message = f"Describe key: {key}-"
            return

        # Check if we're completing a prefix sequence
        prefix_str = getattr(self, "_describing_key_prefix", "")
        if prefix_str:
            key_str = f"{prefix_str} {key}"
            self._describing_key_prefix = ""
            # Look up in the stored prefix map
            prefix_map = getattr(self, "_describing_key_map", None)
            if prefix_map:
                target = prefix_map.lookup(key)
        else:
            key_str = key

        if isinstance(target, str):
            cmd = COMMANDS.get(target)
            doc = cmd.doc if cmd else ""
            lines = [
                f"{key_str} runs the command {target}",
                "",
                f"  {doc}" if doc else "",
            ]
            from recursive_neon.editor.default_commands import _show_help_buffer

            _show_help_buffer(self, "\n".join(lines))
        elif len(key) == 1 and key.isprintable():
            self.message = f"{key_str} runs self-insert-command"
        else:
            self.message = f"{key_str} is not bound"

    def quit(self) -> None:
        """Signal the editor to stop."""
        self.running = False
