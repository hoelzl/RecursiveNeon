"""
TUI app lifecycle manager.

``run_tui_app()`` is the bridge between the shell and a TUI app:
it handles mode switching, keystroke routing, and screen delivery.
Programs call ``await ctx.run_tui(app)`` which delegates here.
"""

from __future__ import annotations

import logging
from typing import Callable

from recursive_neon.shell.output import Output
from recursive_neon.shell.tui import RawInputSource, ScreenBuffer, TuiApp

logger = logging.getLogger(__name__)


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

    Returns:
        Exit code (always 0 for now).
    """

    # Inject a child launcher so the app can spawn nested TUI apps
    # (e.g., running `codebreaker` from M-x shell).
    async def launch_child(child_app: TuiApp) -> int:
        return await run_tui_app(
            child_app,
            raw_input,
            output,
            width=width,
            height=height,
            send_screen=send_screen,
            # No enter_raw/exit_raw — parent is already in raw mode
        )

    if hasattr(app, "set_tui_launcher"):
        app.set_tui_launcher(launch_child)

    if enter_raw:
        enter_raw()

    screen = app.on_start(width, height)
    _deliver_screen(screen, output, send_screen)

    try:
        while True:
            key = await raw_input.get_key()
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
    except EOFError:
        logger.debug("TUI raw input EOF — exiting app")
    finally:
        if exit_raw:
            exit_raw()
        # Clear screen to restore terminal
        output.write("\033[2J\033[H")

    return 0


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
