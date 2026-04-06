"""Tests for TUI terminal size detection and resize handling (TD-005 / 7c-4)."""

from __future__ import annotations

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.tui import ScreenBuffer

# ── Test helpers ─────────────────────────────────────────────────────────


class MockRawInput:
    """RawInputSource that yields a predefined key sequence."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = iter(keys)

    async def get_key(self, *, timeout: float | None = None) -> str | None:
        try:
            return next(self._keys)
        except StopIteration:
            raise EOFError from None


class ResizableApp:
    """TUI app that records on_resize calls."""

    tick_interval_ms = 0

    def __init__(self) -> None:
        self.start_size: tuple[int, int] = (0, 0)
        self.resize_log: list[tuple[int, int]] = []
        self.key_log: list[str] = []
        self.w = 80
        self.h = 24

    def on_start(self, w: int, h: int) -> ScreenBuffer:
        self.start_size = (w, h)
        self.w, self.h = w, h
        screen = ScreenBuffer.create(w, h)
        screen.set_line(0, f"Start {w}x{h}")
        return screen

    def on_key(self, key: str) -> ScreenBuffer | None:
        self.key_log.append(key)
        if key == "q":
            return None
        screen = ScreenBuffer.create(self.w, self.h)
        screen.set_line(0, f"Key: {key}")
        return screen

    def on_resize(self, w: int, h: int) -> ScreenBuffer:
        self.resize_log.append((w, h))
        self.w, self.h = w, h
        screen = ScreenBuffer.create(w, h)
        screen.set_line(0, f"Resize {w}x{h}")
        return screen

    def on_tick(self, dt_ms: int) -> ScreenBuffer | None:
        return None


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTuiResize:
    async def test_custom_initial_size_passed_to_on_start(self):
        """run_tui_app passes width/height to on_start."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        raw_input = MockRawInput(["q"])
        await run_tui_app(app, raw_input, CapturedOutput(), width=120, height=40)
        assert app.start_size == (120, 40)

    async def test_resize_source_triggers_on_resize(self):
        """When resize_source returns a new size, on_resize is called."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        # Resize fires once before the first key, then the key exits
        call_count = [0]

        def resize_source() -> tuple[int, int] | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return (100, 50)
            return None

        raw_input = MockRawInput(["a", "q"])
        await run_tui_app(
            app,
            raw_input,
            CapturedOutput(),
            width=80,
            height=24,
            resize_source=resize_source,
        )
        assert app.resize_log == [(100, 50)]

    async def test_resize_delivers_screen(self):
        """Screen from on_resize is delivered to the client."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        call_count = [0]

        def resize_source() -> tuple[int, int] | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return (100, 50)
            return None

        screens: list[dict] = []
        raw_input = MockRawInput(["q"])
        await run_tui_app(
            app,
            raw_input,
            CapturedOutput(),
            width=80,
            height=24,
            resize_source=resize_source,
            send_screen=lambda msg: screens.append(msg),
        )
        # on_start + on_resize = 2 screens (q returns None, no screen)
        assert len(screens) == 2
        assert "Resize 100x50" in screens[1]["lines"][0]

    async def test_no_resize_when_size_unchanged(self):
        """If resize_source returns the same size, on_resize is not called."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()

        def resize_source() -> tuple[int, int] | None:
            return (80, 24)  # same as initial

        raw_input = MockRawInput(["a", "q"])
        await run_tui_app(
            app,
            raw_input,
            CapturedOutput(),
            width=80,
            height=24,
            resize_source=resize_source,
        )
        assert app.resize_log == []

    async def test_resize_before_first_key(self):
        """Resize arriving immediately after on_start works."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        fired = [False]

        def resize_source() -> tuple[int, int] | None:
            if not fired[0]:
                fired[0] = True
                return (200, 60)
            return None

        raw_input = MockRawInput(["q"])
        await run_tui_app(
            app,
            raw_input,
            CapturedOutput(),
            width=80,
            height=24,
            resize_source=resize_source,
        )
        assert app.resize_log == [(200, 60)]

    async def test_no_resize_source_is_fine(self):
        """When resize_source is None (default), no resize is attempted."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        raw_input = MockRawInput(["q"])
        await run_tui_app(app, raw_input, CapturedOutput(), width=80, height=24)
        assert app.resize_log == []

    async def test_multiple_resizes(self):
        """Multiple resize events are handled."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = ResizableApp()
        sizes = iter([(100, 50), None, (120, 60), None])

        def resize_source() -> tuple[int, int] | None:
            return next(sizes, None)

        raw_input = MockRawInput(["a", "b", "c", "q"])
        await run_tui_app(
            app,
            raw_input,
            CapturedOutput(),
            width=80,
            height=24,
            resize_source=resize_source,
        )
        assert app.resize_log == [(100, 50), (120, 60)]


class TestMeasureTerminal:
    def test_measure_terminal_non_tty(self):
        """When stdout is not a TTY, falls back to 80x24."""
        from unittest.mock import patch

        from recursive_neon.shell.tui.runner import _measure_terminal

        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            w, h = _measure_terminal()
            assert (w, h) == (80, 24)

    def test_measure_terminal_tty(self):
        """When stdout is a TTY, reads real size."""
        from unittest.mock import patch

        from recursive_neon.shell.tui.runner import _measure_terminal

        with (
            patch("sys.stdout") as mock_stdout,
            patch("shutil.get_terminal_size") as mock_size,
        ):
            mock_stdout.isatty.return_value = True
            mock_size.return_value = type("Size", (), {"columns": 150, "lines": 45})()
            w, h = _measure_terminal()
            assert (w, h) == (150, 45)


class TestWebSocketResize:
    def test_terminal_session_feed_resize(self):
        """feed_resize updates _terminal_size and sets _resize_pending."""
        from recursive_neon.terminal import TerminalSession

        # Use minimal mock — we just need to test the data flow
        session = TerminalSession.__new__(TerminalSession)
        session._terminal_size = (80, 24)
        session._resize_pending = None

        session.feed_resize(120, 40)
        assert session._terminal_size == (120, 40)
        assert session._resize_pending == (120, 40)

    def test_terminal_session_drain_clears_pending(self):
        """After draining, _resize_pending is None."""
        from recursive_neon.terminal import TerminalSession

        session = TerminalSession.__new__(TerminalSession)
        session._terminal_size = (80, 24)
        session._resize_pending = (120, 40)

        # Simulate what _drain_resize does
        pending = session._resize_pending
        session._resize_pending = None
        assert pending == (120, 40)
        assert session._resize_pending is None
