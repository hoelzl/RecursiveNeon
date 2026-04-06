"""
TUI app lifecycle manager.

``run_tui_app()`` is the bridge between the shell and a TUI app:
it handles mode switching, keystroke routing, tick callbacks, resize
events, and screen delivery.  Programs call ``await ctx.run_tui(app)``
which delegates here.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys
import time
from typing import Callable

from recursive_neon.shell.output import Output
from recursive_neon.shell.tui import RawInputSource, ScreenBuffer, TuiApp

logger = logging.getLogger(__name__)


def _measure_terminal() -> tuple[int, int]:
    """Return ``(width, height)`` of the real terminal.

    Falls back to ``(80, 24)`` when stdout is not a TTY (piped / captured
    output should stay deterministic for tests).
    """
    if not sys.stdout.isatty():
        return (80, 24)
    size = shutil.get_terminal_size(fallback=(80, 24))
    return (size.columns, size.lines)


async def run_tui_app(
    app: TuiApp,
    raw_input: RawInputSource,
    output: Output,
    *,
    enter_raw: Callable[[], None] | None = None,
    exit_raw: Callable[[], None] | None = None,
    send_screen: Callable[[dict], None] | None = None,
    width: int = 80,
    height: int = 24,
    resize_source: Callable[[], tuple[int, int] | None] | None = None,
) -> int:
    """Run a TUI app to completion.

    Args:
        app: The TUI application to run.
        raw_input: Source for individual keystrokes.
        output: Output stream (used for direct ANSI rendering in CLI mode).
        enter_raw: Called to signal the client to enter raw mode.
        exit_raw: Called to signal the client to return to cooked mode.
        send_screen: Called with a screen message dict (WebSocket path).
            If *None*, screens are rendered via ANSI to *output*.
        width: Initial terminal width.
        height: Initial terminal height.
        resize_source: Callable that returns a ``(w, h)`` tuple if a resize
            event is pending, or ``None`` otherwise.  Called once per loop
            iteration (before processing a keystroke or tick).

    Returns:
        Exit code (always 0 for now).
    """

    cur_w, cur_h = width, height

    # --- Child TUI app management (issue #52) ---
    #
    # When a background task (e.g., shell command execution) launches a
    # child TUI app via launch_child(), the child signals the parent
    # loop to run it inline rather than starting a competing key loop.
    # This ensures only one consumer reads from raw_input at a time.
    _pending_child: list[tuple[TuiApp, asyncio.Event] | None] = [None]

    async def launch_child(child_app: TuiApp) -> int:
        """Request the parent loop to run *child_app* inline.

        Called from background tasks (e.g., shell-in-editor).  Sets a
        pending-child slot and blocks until the parent loop finishes
        running the child.
        """
        done = asyncio.Event()
        _pending_child[0] = (child_app, done)
        await done.wait()
        return 0

    if hasattr(app, "set_tui_launcher"):
        app.set_tui_launcher(launch_child)

    if enter_raw:
        enter_raw()

    screen = app.on_start(cur_w, cur_h)
    _deliver_screen(screen, output, send_screen)

    # Determine tick interval (0 = disabled)
    tick_interval_ms: int = getattr(app, "tick_interval_ms", 0)
    tick_timeout: float | None = (
        tick_interval_ms / 1000.0 if tick_interval_ms > 0 else None
    )
    last_tick = time.monotonic()

    try:
        while True:
            # --- Drain resize events ---
            if resize_source is not None:
                new_size = resize_source()
                if new_size is not None:
                    nw, nh = new_size
                    if (nw, nh) != (cur_w, cur_h):
                        cur_w, cur_h = nw, nh
                        try:
                            resize_screen = app.on_resize(cur_w, cur_h)
                            _deliver_screen(resize_screen, output, send_screen)
                        except Exception:
                            logger.exception("on_resize error")

            key = await raw_input.get_key(timeout=tick_timeout)

            if key is None:
                # Timeout — fire tick callback
                now = time.monotonic()
                dt_ms = int((now - last_tick) * 1000)
                last_tick = now
                on_tick = getattr(app, "on_tick", None)
                if on_tick is not None:
                    try:
                        tick_result = on_tick(dt_ms)
                    except Exception:
                        logger.exception("on_tick error")
                        tick_result = None
                    if tick_result is not None:
                        _deliver_screen(tick_result, output, send_screen)
                continue

            result = app.on_key(key)
            if result is None:
                break
            _deliver_screen(result, output, send_screen)
            # Optional async post-key processing (e.g., shell command execution)
            on_after = getattr(app, "on_after_key", None)
            if on_after is not None:
                after_result = await on_after()
                if after_result is not None:
                    _deliver_screen(after_result, output, send_screen)

            # --- Run pending child TUI app inline (issue #52) ---
            #
            # A background task (e.g., _comint_send_input) may have
            # launched a child TUI app via launch_child().  Run it here
            # in the parent's key loop so there is only one consumer of
            # raw_input at a time.
            if _pending_child[0] is not None:
                child_app, child_done = _pending_child[0]
                _pending_child[0] = None
                await _run_child_inline(
                    child_app,
                    child_done,
                    raw_input,
                    output,
                    send_screen=send_screen,
                    resize_source=resize_source,
                    width=cur_w,
                    height=cur_h,
                )
                # Yield so the background task can finish post-command
                # work (e.g., insert prompt into buffer).
                await asyncio.sleep(0)
                # Re-render parent after child exits
                if on_after is not None:
                    after_result = await on_after()
                    if after_result is not None:
                        _deliver_screen(after_result, output, send_screen)
    except EOFError:
        logger.debug("TUI raw input EOF — exiting app")
    finally:
        if exit_raw:
            exit_raw()
        # Clear screen to restore terminal
        output.write("\033[2J\033[H")

    return 0


async def _run_child_inline(
    child_app: TuiApp,
    child_done: asyncio.Event,
    raw_input: RawInputSource,
    output: Output,
    *,
    send_screen: Callable[[dict], None] | None = None,
    resize_source: Callable[[], tuple[int, int] | None] | None = None,
    width: int = 80,
    height: int = 24,
) -> None:
    """Run a child TUI app inside the parent's key loop.

    Called by ``run_tui_app`` when a background task has queued a child
    via ``launch_child()``.  Consumes all keystrokes until the child
    exits, then signals the background task to resume.
    """
    cur_w, cur_h = width, height

    screen = child_app.on_start(cur_w, cur_h)
    _deliver_screen(screen, output, send_screen)

    child_tick_ms: int = getattr(child_app, "tick_interval_ms", 0)
    child_timeout: float | None = child_tick_ms / 1000.0 if child_tick_ms > 0 else None
    last_tick = time.monotonic()

    try:
        while True:
            if resize_source is not None:
                new_size = resize_source()
                if new_size is not None:
                    nw, nh = new_size
                    if (nw, nh) != (cur_w, cur_h):
                        cur_w, cur_h = nw, nh
                        try:
                            resize_screen = child_app.on_resize(cur_w, cur_h)
                            _deliver_screen(resize_screen, output, send_screen)
                        except Exception:
                            logger.exception("child on_resize error")

            key = await raw_input.get_key(timeout=child_timeout)

            if key is None:
                now = time.monotonic()
                dt_ms = int((now - last_tick) * 1000)
                last_tick = now
                on_tick = getattr(child_app, "on_tick", None)
                if on_tick is not None:
                    try:
                        tick_result = on_tick(dt_ms)
                    except Exception:
                        logger.exception("child on_tick error")
                        tick_result = None
                    if tick_result is not None:
                        _deliver_screen(tick_result, output, send_screen)
                continue

            result = child_app.on_key(key)
            if result is None:
                break
            _deliver_screen(result, output, send_screen)
    finally:
        child_done.set()


def _deliver_screen(
    screen: ScreenBuffer,
    output: Output,
    send_screen: Callable[[dict], None] | None,
) -> None:
    """Push a screen buffer to the client."""
    if send_screen is not None:
        send_screen(screen.to_message())
    else:
        output.write(screen.render_ansi())
