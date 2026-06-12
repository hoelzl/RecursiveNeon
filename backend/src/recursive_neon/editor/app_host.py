"""
TuiApp window host — run the game's TUI apps inside an editor window.

The "never leave the editor" enabler (docs/EDITOR_SHELL_ROADMAP.md step
2): ``codebreaker``, ``sysmon``, ``portscan``, ``fsbrowse`` and
``memdump`` become playable in a normal editor window instead of taking
over the whole screen. There is no VT100 emulation — the game has no
PTYs. Every app is a :class:`~recursive_neon.shell.tui.TuiApp` that
renders a ``ScreenBuffer`` directly, so hosting one means blitting its
rows (text + ANSI SGR runs) into a read-only attributed buffer that the
ordinary window pipeline renders.

Key routing follows GNU Emacs's ``term`` char mode (probed against
Emacs 29.3): while the hosted buffer's window is selected, every key
goes to the child app, except ``C-c`` which acts as the escape prefix —
``C-c <key>`` runs what ``C-x <key>`` would (``term-raw-escape-map``
clones the ``C-x`` map: ``C-c o`` switches windows, ``C-c 2`` splits,
``C-c b`` prompts for a buffer), and ``C-c C-c`` sends a literal
``C-c`` to the app. When another window is selected the app keeps
rendering (ticks still arrive) but receives no keys.

The child's size is the *window's* text area, not the screen:
``Buffer.on_window_size`` (called by ``EditorView`` whenever it lays
out a window showing the buffer) re-sends ``TuiApp.on_resize`` when the
window geometry changes. Periodic apps (sysmon) are driven by
``EditorView.on_tick``.

App construction goes through ``editor.tui_app_factories`` — a
``name → () -> TuiApp`` mapping injected by the hosting environment
(``shell/programs/edit.py``), the same pattern as ``shell_factory``.
Standalone editors have no factories and the commands report the apps
as unavailable.

Not parity-verifiable (the apps are ours, not Emacs's); behaviour is
pinned by ``tests/unit/editor/test_app_host.py``. The modeline shows
``(TUI run)`` — for our apps there is no Emacs ground truth to match,
the indicator just follows term-mode's ``(Term: char run)`` shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from recursive_neon.editor.commands import defcommand
from recursive_neon.editor.keymap import Keymap
from recursive_neon.editor.modes import defmode

if TYPE_CHECKING:
    from recursive_neon.editor.buffer import Buffer
    from recursive_neon.editor.editor import Editor
    from recursive_neon.shell.tui import ScreenBuffer


HOSTED_APP_NAMES = ("codebreaker", "sysmon", "portscan", "fsbrowse", "memdump")


@dataclass
class AppHostState:
    """State attached to a hosted-app buffer as ``buf._app_host_state``."""

    app: Any
    """The hosted TuiApp."""

    name: str
    """The app's command name (``"codebreaker"`` …) for messages."""

    width: int = 0
    height: int = 0
    """The text-area size last reported to the app."""

    finished: bool = False
    """True once ``on_key`` returned None — the buffer keeps the final
    screen, keys stop being captured, ``q`` quits the window."""

    prefix_pending: bool = False
    """A ``C-c`` was typed; the next key resolves via the C-x map."""


defmode(
    "tui-host-mode",
    is_major=True,
    doc="Major mode hosting a TUI app inside an editor window.",
    indicator="TUI run",
)


def _host_keymap(editor: Editor) -> Keymap:
    # Only consulted once the app has finished (capture handles live
    # keys); ``q`` then dismisses the leftover screen like any popup.
    km = Keymap("tui-host-mode-map", parent=editor.global_keymap)
    km.bind("q", "quit-window")
    return km


def _window_text_size(ed: Editor) -> tuple[int, int]:
    tree = ed._window_tree
    if tree is None:  # headless (unit tests without a TUI)
        return (80, 22)
    win = tree.active
    return (win._width, win.text_height)


def _blit(buf: Buffer, state: AppHostState, screen: ScreenBuffer) -> None:
    """Write the app's screen into the buffer through the attribute layer."""
    from recursive_neon.editor.ansi_parser import parse_ansi

    buf.read_only = False
    buf._undo_recording = False
    try:
        buf.lines = [""]
        buf._line_attrs = [[]]
        buf.point.move_to(0, 0)
        buf.insert_string_attributed(parse_ansi("\n".join(screen.lines)))
        # Leave point where the app put its cursor, clamped to content.
        line = min(max(screen.cursor_row, 0), buf.line_count - 1)
        col = min(max(screen.cursor_col, 0), len(buf.lines[line]))
        buf.point.move_to(line, col)
        buf.modified = True  # term-style %* modeline
    finally:
        buf._undo_recording = True
        buf.read_only = True


def _make_resize_hook(ed: Editor, buf: Buffer, state: AppHostState) -> Callable:
    def on_window_size(width: int, height: int) -> None:
        if state.finished or (width, height) == (state.width, state.height):
            return
        state.width, state.height = width, height
        screen = state.app.on_resize(width, height)
        if screen is not None:
            _blit(buf, state, screen)

    return on_window_size


def open_hosted_app(ed: Editor, name: str) -> bool:
    """Open (or switch back to) the hosted-app buffer for *name*.

    A finished app is restarted in place with a fresh instance, like
    re-running the shell command.
    """
    factories: dict[str, Callable[[], Any]] | None = getattr(
        ed, "tui_app_factories", None
    )
    factory = factories.get(name) if factories else None
    if factory is None:
        ed.message = f"{name} not available in this context"
        return False

    bufname = f"*{name}*"
    existing = next((b for b in ed.buffers if b.name == bufname), None)
    if existing is not None:
        ed.switch_to_buffer(bufname)
        state: AppHostState = existing._app_host_state  # type: ignore[attr-defined]
        if not state.finished:
            return True
        # Restart in place.
        state.app = factory()
        state.finished = False
        state.width, state.height = _window_text_size(ed)
        _blit(existing, state, state.app.on_start(state.width, state.height))
        return True

    app = factory()
    buf = ed.create_buffer(name=bufname)
    state = AppHostState(app=app, name=name)
    buf._app_host_state = state  # type: ignore[attr-defined]
    buf.keymap = _host_keymap(ed)
    ed.set_major_mode("tui-host-mode")
    buf.enable_attrs()
    state.width, state.height = _window_text_size(ed)
    _blit(buf, state, app.on_start(state.width, state.height))
    buf.on_window_size = _make_resize_hook(ed, buf, state)  # type: ignore[attr-defined]
    buf.mark_saved()
    buf.modified = True  # the first blit counts, like term's %*
    return True


# ------------------------------------------------------------------
# Key capture (called from Editor.process_key)
# ------------------------------------------------------------------


def host_handle_key(ed: Editor, key: str) -> bool:
    """Route *key* for the hosted app in the current buffer.

    Returns True when the key was consumed. Mirrors Emacs term char
    mode: everything goes to the app except the ``C-c`` escape prefix.
    """
    buf = ed.buffer
    state: AppHostState | None = getattr(buf, "_app_host_state", None)
    if state is None or state.finished:
        return False

    if state.prefix_pending:
        state.prefix_pending = False
        ed.message = ""
        if key == "C-c":  # C-c C-c → literal C-c to the app
            _forward_key(ed, buf, state, "C-c")
            return True
        if key == "C-g":
            ed._execute_command_by_name("keyboard-quit")
            return True
        cx = ed.global_keymap.lookup("C-x")
        target = cx.lookup(key) if isinstance(cx, Keymap) else None
        if isinstance(target, Keymap):
            # Two-level prefix (C-c 4 C-f, C-c r SPC …): hand the inner
            # map to the editor's ordinary pending-prefix machinery.
            ed._pending_keymap = target
            ed._prefix_keys = f"C-c {key}"
            ed.message = f"C-c {key}-"
            return True
        if isinstance(target, str):
            ed._execute_command_by_name(target)
            return True
        ed.message = f"C-c {key} is undefined"
        return True

    if key == "C-c":
        state.prefix_pending = True
        ed.message = "C-c-"
        return True

    _forward_key(ed, buf, state, key)
    return True


def _forward_key(ed: Editor, buf: Buffer, state: AppHostState, key: str) -> None:
    try:
        screen = state.app.on_key(key)
    except Exception as e:  # an app crash must not take the editor down
        state.finished = True
        ed.message = f"Error in {state.name}: {e}"
        return
    if screen is None:
        state.finished = True
        ed.message = f"[Process {state.name} finished]"
        return
    _blit(buf, state, screen)


# ------------------------------------------------------------------
# Tick driving (called from EditorView.on_tick)
# ------------------------------------------------------------------


def live_hosted_states(ed: Editor) -> list[tuple[Buffer, AppHostState]]:
    """All unfinished hosted apps, with their buffers."""
    out: list[tuple[Buffer, AppHostState]] = []
    for buf in ed.buffers:
        state = getattr(buf, "_app_host_state", None)
        if state is not None and not state.finished:
            out.append((buf, state))
    return out


def tick_hosted_apps(ed: Editor, dt_ms: int) -> bool:
    """Run ``on_tick`` for every live hosted app that wants ticks.

    Returns True when any app produced a new screen (the caller
    re-renders). Apps tick even when their window is not selected — a
    sysmon in the other window keeps updating, like a real terminal.
    """
    changed = False
    for buf, state in live_hosted_states(ed):
        if getattr(state.app, "tick_interval_ms", 0) <= 0:
            continue
        try:
            screen = state.app.on_tick(dt_ms)
        except Exception as e:
            state.finished = True
            ed.message = f"Error in {state.name}: {e}"
            changed = True
            continue
        if screen is not None:
            _blit(buf, state, screen)
            changed = True
    return changed


def min_tick_interval_ms(ed: Editor) -> int:
    """The smallest tick interval requested by a live hosted app (0 when
    none wants ticks) — drives ``EditorView.tick_interval_ms``."""
    intervals = [
        getattr(state.app, "tick_interval_ms", 0) for _, state in live_hosted_states(ed)
    ]
    positive = [i for i in intervals if i > 0]
    return min(positive) if positive else 0


# ------------------------------------------------------------------
# Entry-point commands (M-x codebreaker, M-x sysmon, …)
# ------------------------------------------------------------------


def _register_app_command(name: str) -> None:
    @defcommand(name, f"Run {name} in the current window (M-x {name}).")
    def _cmd(ed: Editor, prefix: int | None, _name: str = name) -> None:
        open_hosted_app(ed, _name)


for _name in HOSTED_APP_NAMES:
    _register_app_command(_name)
