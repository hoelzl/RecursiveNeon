"""
Editor — the central coordinator.

The Editor owns the buffer list, current buffer, global keymap, shared
kill ring, and drives the command dispatch loop.  It processes
keystrokes by resolving them through layered keymaps, handling prefix
key state, and executing the resulting command.

Undo boundaries are inserted automatically between commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from recursive_neon.editor.buffer import Buffer
from recursive_neon.editor.commands import COMMANDS
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.killring import KillRing
from recursive_neon.editor.minibuffer import CompleterFn, Minibuffer
from recursive_neon.editor.modes import MODES
from recursive_neon.editor.variables import VARIABLES

if TYPE_CHECKING:
    from recursive_neon.editor.default_commands import _QueryReplaceSession
    from recursive_neon.editor.viewport import Viewport
    from recursive_neon.editor.window import WindowTree


@dataclass
class _DescribeKeySession:
    """Capture-mode state for ``describe-key`` / ``describe-key-briefly``.

    The session is installed by the ``describe-key`` / ``describe-key-briefly``
    commands and consumed by :meth:`Editor.process_key` — the next keystroke
    (or key *pair*, for prefix keys) is looked up and described instead of
    being dispatched normally.  Re-armed by ``_do_describe_key`` when the
    first key is a prefix keymap (e.g. ``C-x``), so the two-key sequence
    ``C-x C-s`` is captured as one describe-key unit.
    """

    brief: bool = False
    """False = C-h k (show in *Help*), True = C-h c (show in message area)."""

    prefix: str = ""
    """Display string mid-two-key (e.g. ``"C-x"``).  Empty on entry."""

    prefix_map: Keymap | None = None
    """Keymap mid-two-key, used to resolve the follow-up keystroke."""


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
        self._prefix_has_digits: bool = False

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

        # Describe-key capture session.  When non-None, the next
        # keystroke is consumed and described instead of being
        # dispatched.  Holds brief/full flag plus any mid-two-key
        # prefix state (e.g., after "C-h k C-x", waiting for the
        # second key in the C-x keymap).  Cleared by
        # ``_reset_transient_state``.
        self._describe_key_session: _DescribeKeySession | None = None

        # Query-replace capture session.  When non-None (and not
        # ``paused_for_edit``), single keystrokes drive the query-replace
        # flow (y/n/q/./!/u/U/e/C-g/?).  Installed by the ``query-replace``
        # command after both entry prompts submit; cleared on session
        # exit or by ``_reset_transient_state``.  The type is forward-
        # referenced to avoid a circular import with ``default_commands``.
        self._query_replace_session: _QueryReplaceSession | None = None

        # ESC-as-Meta state machine.  A bare Escape keystroke sets
        # ``_meta_pending``; the next non-ESC key is then rewritten as
        # ``M-<key>`` (e.g., ESC f → M-f).  A second bare Escape
        # transitions to ``_escape_quit_pending``; a third triggers
        # ``keyboard-escape-quit``.  Mirrors real Emacs behaviour.
        self._meta_pending: bool = False
        self._escape_quit_pending: bool = False

        # Highlight overlay for isearch / query-replace.  When
        # ``highlight_term`` is non-None, ``EditorView`` scans visible
        # text for matches and emits StyleSpans via the post-compose
        # styling pass.  Ownership: whichever interactive command sets
        # the term is responsible for clearing it on exit; blanket
        # callers like ``_reset_transient_state`` clear it too.
        self.highlight_term: str | None = None
        self.highlight_case_fold: bool = False

        # Track whether the last command was issued by us so Buffer
        # can correlate consecutive operations (e.g., kill merging)
        self._last_command_name: str = ""

        # Viewport — set by EditorView when attached, None in headless mode
        self.viewport: Viewport | None = None

        # Recenter cycle index (center=0, top=1, bottom=2)
        self._recenter_index: int = 0

        # Window tree — set by EditorView, None in headless mode
        self._window_tree: WindowTree | None = None

        # Shell factory — set by the hosting environment to create Shell
        # instances for M-x shell.  Signature: () -> Shell.
        self.shell_factory: Callable[[], Any] | None = None

        # After-key async callback queue — commands that need async
        # execution (e.g., shell command dispatch) call ``after_key()``
        # to enqueue a callback.  ``EditorView.on_after_key()`` drains
        # the queue in FIFO order after each keystroke.
        self._after_key_queue: list[Callable[[], Awaitable[None]]] = []

        # Render request flag — set by background tasks (e.g., interactive
        # shell programs) to signal that the display needs updating.
        self._render_requested: bool = False

        # Background tasks — tracked for cleanup on editor exit.
        self._background_tasks: list[Any] = []  # list[asyncio.Task]

        # TUI app launcher — set by run_tui_app via EditorView.
        # Allows shell-mode to spawn nested TUI apps (e.g., codebreaker).
        self.tui_launcher: Callable | None = None

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
        # Assign the default major mode
        fundamental = MODES.get("fundamental-mode")
        if fundamental is not None:
            buf.major_mode = fundamental
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
        # Describe-key capture runs first: it consumes *any* key,
        # including Escape, so that C-h k ESC describes Escape rather
        # than triggering the ESC-as-Meta state machine.  Matches the
        # C-g handling convention from Phase 6l-1.  The session is
        # cleared before dispatching; ``_do_describe_key`` re-arms it
        # by constructing a fresh session when the first key is a
        # prefix keymap (so "C-h k C-x C-s" is captured as one unit).
        if self._describe_key_session is not None:
            session = self._describe_key_session
            self._describe_key_session = None
            if session.brief:
                self._do_describe_key_briefly(key, session)
            else:
                self._do_describe_key(key, session)
            return

        # Query-replace capture (6l-4): runs BEFORE the ESC state
        # machine so ESC inside a session triggers keyboard-escape-quit
        # (which cancels via _reset_transient_state) rather than being
        # rewritten as a Meta prefix.  The ``paused_for_edit`` guard
        # lets the nested ``e`` sub-phase minibuffer handle keys via
        # the minibuffer routing step below.
        if (
            self._query_replace_session is not None
            and not self._query_replace_session.paused_for_edit
        ):
            from recursive_neon.editor.default_commands import _qr_handle_key

            _qr_handle_key(self, key)
            return

        # ESC-as-Meta state machine.  Runs before minibuffer routing so
        # a bare Escape does not reach the minibuffer and so that
        # ESC ESC ESC can dismiss the minibuffer via
        # ``keyboard-escape-quit``.
        if key == "Escape":
            if self._escape_quit_pending:
                # Third ESC — run keyboard-escape-quit directly.  Clear
                # the pending flags first so ``_reset_transient_state``
                # starts from a clean slate.
                self._meta_pending = False
                self._escape_quit_pending = False
                self._execute_command_by_name("keyboard-escape-quit")
                return
            if self._meta_pending:
                # Second ESC — transition to escape-quit-pending.
                self._meta_pending = False
                self._escape_quit_pending = True
                self.message = "ESC ESC-"
                return
            # First ESC — enter meta-pending.
            self._meta_pending = True
            self.message = "ESC-"
            return

        if self._meta_pending or self._escape_quit_pending:
            # Previous key(s) were bare Escape and the user followed
            # up with something else.  C-g is a universal quit signal
            # and must not be rewritten to C-M-g — clear the pending
            # state and let it fall through to the C-g intercept below
            # (which runs ``keyboard-quit``).  Every other key becomes
            # M-<key>.  The follow-up character invalidates any
            # escape-quit-pending state — only the most-recent ESC
            # acts as the Meta prefix.
            self._meta_pending = False
            self._escape_quit_pending = False
            if key != "C-g":
                key = self._rewrite_as_meta(key)
            self.message = ""

        # Route to minibuffer if active
        if self.minibuffer is not None:
            old_mb = self.minibuffer
            still_active = old_mb.process_key(key)
            if not still_active:
                replay = old_mb.replay_key
                if old_mb.cancelled:
                    # Emacs behaviour: cancelling the minibuffer shows
                    # "Quit" but does *not* deactivate the mark or
                    # otherwise touch editor-global state.  The command
                    # that opened the minibuffer already consumed any
                    # prefix keymap / prefix-arg state.
                    self.message = "Quit"
                # Only clear if the callback didn't start a new minibuffer
                if self.minibuffer is old_mb:
                    self.minibuffer = None
                # Re-dispatch replayed key (isearch exit-and-replay)
                if replay is not None:
                    self.process_key(replay)
            return

        # C-g is special: it interrupts any in-progress command,
        # pending prefix keymap, or prefix argument and dispatches
        # ``keyboard-quit``.  In Emacs this is handled by the ``quit``
        # signal at the read-key-sequence level; here we intercept it
        # directly.  Must come *after* minibuffer / describe-key
        # handling so those contexts can consume C-g themselves.
        if key == "C-g":
            self._execute_command_by_name("keyboard-quit")
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

    @staticmethod
    def _rewrite_as_meta(key: str) -> str:
        """Rewrite *key* as its Meta-prefixed equivalent for ESC-as-Meta.

        Used when the editor has a pending bare-Escape and the user
        presses a non-ESC follow-up key.  Follows the conventional
        mapping:

        - ``"f"`` → ``"M-f"`` (printable → M-prefixed)
        - ``"Enter"`` → ``"M-Enter"`` (named key → M-prefixed)
        - ``"C-f"`` → ``"C-M-f"`` (Ctrl → C-M-)
        - ``"M-f"`` → ``"M-f"`` (already Meta — leave alone, e.g. the
          key reader already combined ESC+f into M-f at the byte level)
        - ``"C-M-f"`` → ``"C-M-f"`` (already C-M- — leave alone)
        """
        if key.startswith("M-") or key.startswith("C-M-"):
            return key
        if key.startswith("C-"):
            return f"C-M-{key[2:]}"
        return f"M-{key}"

    def _resolve_keymap(self) -> Keymap:
        """Resolve the effective keymap for the current buffer.

        Resolution order: buffer-local > minor modes (last added first)
        > major mode > global.  Each layer with a keymap is checked via
        its parent chain, so unbound keys fall through automatically.
        """
        if self.buffer.keymap is not None:
            return self.buffer.keymap
        buf = self.buffer
        # Check minor-mode keymaps (last added = highest priority)
        for mode in reversed(buf.minor_modes):
            if mode.keymap is not None:
                return mode.keymap
        # Check major-mode keymap
        if buf.major_mode is not None and buf.major_mode.keymap is not None:
            return buf.major_mode.keymap
        return self.global_keymap

    def _start_or_extend_prefix_arg(self) -> None:
        """Handle C-u: start or multiply the prefix argument."""
        if self._prefix_arg is None:
            self._prefix_arg = 4
        else:
            self._prefix_arg *= 4
        self._building_prefix = True
        self._prefix_has_digits = False
        self.message = f"C-u {self._prefix_arg}"

    def _extend_prefix_digit(self, digit: str) -> None:
        """Extend the prefix argument with a digit."""
        if self._prefix_arg is not None and self._building_prefix:
            # First digit replaces the default 4
            if self._prefix_arg == 4 and not self._prefix_has_digits:
                self._prefix_arg = int(digit)
                self._prefix_has_digits = True
            else:
                self._prefix_arg = self._prefix_arg * 10 + int(digit)
        self.message = f"C-u {self._prefix_arg}"

    def _execute_command_by_name(self, name: str, *, key: str | None = None) -> None:
        """Look up and execute a named command."""
        cmd = COMMANDS.get(name)
        if cmd is None:
            self.message = f"Unknown command: {name}"
            self._prefix_arg = None
            return

        # Insert undo boundary between distinct commands.
        #
        # Exception: ``undo`` is a chaining command.  ``Buffer.undo()``
        # tracks a consecutive-undo chain via ``last_command_type`` and
        # ``_undo_cursor``; calling ``add_undo_boundary`` between two
        # ``undo`` dispatches would break that chain (it clears both
        # fields as a side effect — see ``buffer.py::add_undo_boundary``)
        # and turn the second C-/ into a redo of the first.  Skipping
        # the boundary preserves the chain.  The boundary that
        # separates the previous command's entries from the undo's
        # reverse entries is added inside ``Buffer.undo()`` itself.
        buf = self.buffer
        if name != "undo" and (
            self._last_command_name != name or name != "self-insert-command"
        ):
            buf.add_undo_boundary()

        # Stash the key for self-insert-command
        self._current_key = key

        # Execute
        prefix = self._prefix_arg
        self._prefix_arg = None
        self._prefix_has_digits = False
        buf._read_only_error = False

        cmd.function(self, prefix)

        if buf._read_only_error:
            self.message = "Text is read-only"
            buf._read_only_error = False

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
        # Same ``undo``-is-chaining exception as _execute_command_by_name;
        # see that method for rationale.
        buf = self.buffer
        if name != "undo":
            buf.add_undo_boundary()
        buf._read_only_error = False
        cmd.function(self, prefix)
        if buf._read_only_error:
            self.message = "Text is read-only"
            buf._read_only_error = False
        self._last_command_name = name
        return True

    # ------------------------------------------------------------------
    # Async bridge
    # ------------------------------------------------------------------

    def after_key(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Queue an async callback to run after the current keystroke.

        Callbacks execute in FIFO order during ``EditorView.on_after_key()``.
        Errors in callbacks are caught and shown in the message area.
        """
        self._after_key_queue.append(callback)

    def request_render(self) -> None:
        """Signal that the display needs updating.

        Called from background tasks (e.g., interactive shell programs)
        to request a re-render at the next opportunity.
        """
        self._render_requested = True

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

    def _do_describe_key(self, key: str, session: _DescribeKeySession) -> None:
        """Look up what a key is bound to and show in *Help*.

        ``session`` carries any mid-two-key prefix state.  When the
        looked-up key is itself a prefix keymap, a fresh session is
        installed on ``self`` so the next keystroke completes the
        two-key lookup.
        """
        # Special case: bare Escape is the ESC-as-Meta prefix, not a
        # keymap binding.  Describe its role explicitly rather than
        # falling through to "Escape is not bound".
        if key == "Escape" and not session.prefix:
            from recursive_neon.editor.default_commands import _show_help_buffer

            lines = [
                "Escape acts as the Meta prefix (ESC-as-Meta).",
                "",
                "  ESC <key>   equivalent to M-<key> (e.g. ESC f runs forward-word)",
                "  ESC ESC ESC runs the command keyboard-escape-quit",
            ]
            _show_help_buffer(self, "\n".join(lines))
            return

        keymap = self._resolve_keymap()
        target = keymap.lookup(key)

        if isinstance(target, Keymap):
            # It's a prefix key — re-arm the session so the next key
            # completes the two-key sequence.
            self._describe_key_session = _DescribeKeySession(
                brief=False,
                prefix=key,
                prefix_map=target,
            )
            self.message = f"Describe key: {key}-"
            return

        # Check if we're completing a prefix sequence
        if session.prefix:
            key_str = f"{session.prefix} {key}"
            if session.prefix_map is not None:
                target = session.prefix_map.lookup(key)
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

    def _do_describe_key_briefly(self, key: str, session: _DescribeKeySession) -> None:
        """Look up what a key is bound to and show in the message area."""
        # Special case: bare Escape is the ESC-as-Meta prefix.
        if key == "Escape" and not session.prefix:
            self.message = "Escape is the Meta prefix (ESC-as-Meta); "
            self.message += "ESC ESC ESC runs keyboard-escape-quit"
            return

        keymap = self._resolve_keymap()
        target = keymap.lookup(key)

        if isinstance(target, Keymap):
            # Prefix key — re-arm the session for the follow-up key.
            self._describe_key_session = _DescribeKeySession(
                brief=True,
                prefix=key,
                prefix_map=target,
            )
            self.message = f"Describe key briefly: {key}-"
            return

        # Check if completing a prefix sequence
        if session.prefix:
            key_str = f"{session.prefix} {key}"
            if session.prefix_map is not None:
                target = session.prefix_map.lookup(key)
        else:
            key_str = key

        if isinstance(target, str):
            self.message = f"{key_str} runs {target}"
        elif len(key) == 1 and key.isprintable():
            self.message = f"{key_str} runs self-insert-command"
        else:
            self.message = f"{key_str} is not bound"

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    def get_variable(self, name: str) -> Any:
        """Look up a variable value using the cascade:

        buffer-local > minor-mode defaults > major-mode defaults > global default.
        Returns ``None`` if the variable is not registered.
        """
        buf = self.buffer
        # 1. Buffer-local override
        if name in buf.local_variables:
            return buf.local_variables[name]
        # 2. Minor modes (last added = highest priority)
        for mode in reversed(buf.minor_modes):
            if name in mode.variables:
                return mode.variables[name]
        # 3. Major mode
        if buf.major_mode is not None and name in buf.major_mode.variables:
            return buf.major_mode.variables[name]
        # 4. Global default
        var = VARIABLES.get(name)
        if var is not None:
            return var.default
        return None

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable's global default.  Validates the value."""
        var = VARIABLES.get(name)
        if var is None:
            self.message = f"Unknown variable: {name}"
            return
        var.default = var.validate(value)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def set_major_mode(self, mode_name: str) -> bool:
        """Set the major mode on the current buffer.

        Calls ``on_exit`` on the old mode and ``on_enter`` on the new one.
        Returns False if the mode is not found.
        """
        mode = MODES.get(mode_name)
        if mode is None or not mode.is_major:
            self.message = f"Unknown major mode: {mode_name}"
            return False
        buf = self.buffer
        # Exit old mode
        if buf.major_mode is not None and buf.major_mode.on_exit is not None:
            buf.major_mode.on_exit(self)
        buf.major_mode = mode
        # Enter new mode
        if mode.on_enter is not None:
            mode.on_enter(self)
        self.message = f"({mode.name})"
        return True

    def toggle_minor_mode(self, mode_name: str) -> bool:
        """Toggle a minor mode on the current buffer.

        If the mode is active, deactivate it (call ``on_exit``).
        If inactive, activate it (call ``on_enter``).
        Returns False if the mode is not found.
        """
        mode = MODES.get(mode_name)
        if mode is None or mode.is_major:
            self.message = f"Unknown minor mode: {mode_name}"
            return False
        buf = self.buffer
        # Check if already active
        for i, m in enumerate(buf.minor_modes):
            if m.name == mode_name:
                if m.on_exit is not None:
                    m.on_exit(self)
                buf.minor_modes.pop(i)
                self.message = f"{mode_name} disabled"
                return True
        # Activate
        buf.minor_modes.append(mode)
        if mode.on_enter is not None:
            mode.on_enter(self)
        self.message = f"{mode_name} enabled"
        return True

    def quit(self) -> None:
        """Signal the editor to stop."""
        self.running = False

    # ------------------------------------------------------------------
    # Transient state reset (shared by keyboard-quit and
    # keyboard-escape-quit)
    # ------------------------------------------------------------------

    def _reset_transient_state(self) -> None:
        """Clear all transient interactive state.

        Called by ``keyboard-quit`` (C-g) and ``keyboard-escape-quit``
        (ESC ESC ESC) to return the editor to a clean, idle state: no
        pending prefix keymap, no prefix argument being built, no
        describe-key capture in flight, no region.

        Note that a C-g keystroke cannot reach this helper while
        describe-key capture is active — in that case the key is
        consumed by ``_do_describe_key`` (matching Emacs).  The
        describe-key fields are cleared here for the sake of
        ``keyboard-escape-quit`` and other future callers that want a
        blanket reset.

        Does *not* touch the minibuffer — callers handle it explicitly
        because dismissal has a replay-key side effect.
        """
        # Clear the region / mark
        self.buffer.clear_mark()
        # Clear pending prefix keymap (mid C-x / C-h etc.)
        self._pending_keymap = None
        self._prefix_keys = ""
        # Clear prefix argument (C-u)
        self._prefix_arg = None
        self._building_prefix = False
        self._prefix_has_digits = False
        # Clear describe-key capture session (covers both C-h k and C-h c)
        self._describe_key_session = None
        # Clear query-replace capture session (6l-4)
        self._query_replace_session = None
        # Clear ESC-as-Meta state machine
        self._meta_pending = False
        self._escape_quit_pending = False
        # Clear highlight overlay (isearch / query-replace)
        self.highlight_term = None
        self.highlight_case_fold = False
