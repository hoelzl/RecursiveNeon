"""Tests for the TUI framework: ScreenBuffer, TuiApp runner."""

from __future__ import annotations

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.tui import ScreenBuffer

# ── ScreenBuffer ──────────────────────────────────────────────────────────


class TestScreenBuffer:
    def test_create_default_dimensions(self):
        screen = ScreenBuffer.create()
        assert screen.width == 80
        assert screen.height == 24
        assert len(screen.lines) == 24
        assert all(line == "" for line in screen.lines)

    def test_create_custom_dimensions(self):
        screen = ScreenBuffer.create(40, 10)
        assert screen.width == 40
        assert screen.height == 10
        assert len(screen.lines) == 10

    def test_set_line(self):
        screen = ScreenBuffer.create(80, 5)
        screen.set_line(0, "hello")
        screen.set_line(4, "world")
        assert screen.lines[0] == "hello"
        assert screen.lines[4] == "world"

    def test_set_line_out_of_bounds(self):
        screen = ScreenBuffer.create(80, 5)
        # Should silently ignore out-of-bounds
        screen.set_line(-1, "nope")
        screen.set_line(5, "nope")
        assert all(line == "" for line in screen.lines)

    def test_clear(self):
        screen = ScreenBuffer.create(80, 5)
        screen.set_line(0, "data")
        screen.set_line(2, "more data")
        screen.clear()
        assert all(line == "" for line in screen.lines)
        assert len(screen.lines) == 5

    def test_center_text(self):
        screen = ScreenBuffer.create(20, 3)
        screen.center_text(1, "hi")
        # "hi" is 2 chars, padding = (20-2)//2 = 9
        assert screen.lines[1] == " " * 9 + "hi"

    def test_center_text_with_style(self):
        screen = ScreenBuffer.create(20, 3)
        screen.center_text(1, "hi", style="\033[1m")
        assert "\033[1m" in screen.lines[1]
        assert "hi" in screen.lines[1]
        assert "\033[0m" in screen.lines[1]

    def test_center_text_out_of_bounds(self):
        screen = ScreenBuffer.create(20, 3)
        screen.center_text(-1, "nope")
        screen.center_text(3, "nope")
        assert all(line == "" for line in screen.lines)

    def test_to_message(self):
        screen = ScreenBuffer.create(10, 3)
        screen.set_line(0, "test")
        screen.cursor_row = 1
        screen.cursor_col = 5
        msg = screen.to_message()
        assert msg["type"] == "screen"
        assert msg["lines"] == ["test", "", ""]
        assert msg["cursor"] == [1, 5]
        assert msg["cursor_visible"] is True

    def test_to_message_cursor_hidden(self):
        screen = ScreenBuffer.create(10, 3)
        screen.cursor_visible = False
        msg = screen.to_message()
        assert msg["cursor_visible"] is False

    def test_render_ansi(self):
        screen = ScreenBuffer.create(10, 3)
        screen.set_line(0, "line0")
        screen.set_line(1, "line1")
        screen.cursor_row = 1
        screen.cursor_col = 3
        result = screen.render_ansi()
        # Should contain clear + home
        assert "\033[2J\033[H" in result
        # Should position each line
        assert "\033[1;1Hline0" in result
        assert "\033[2;1Hline1" in result
        # Should position cursor at row 2, col 4 (1-based)
        assert "\033[2;4H" in result

    def test_render_ansi_cursor_hidden(self):
        screen = ScreenBuffer.create(10, 3)
        screen.cursor_visible = False
        screen.cursor_row = 1
        screen.cursor_col = 1
        result = screen.render_ansi()
        # Should not include cursor positioning at end
        # (the line positioning still happens, but no final cursor move)
        assert result.endswith("\033[3;1H")  # last line position


# ── TUI Runner ────────────────────────────────────────────────────────────


class MockRawInput:
    """A RawInputSource that yields a predefined key sequence."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = iter(keys)

    async def get_key(self) -> str:
        try:
            return next(self._keys)
        except StopIteration:
            raise EOFError from None


class SimpleTuiApp:
    """Minimal TUI app for testing the runner."""

    def __init__(self, exit_on: str = "Escape") -> None:
        self.exit_on = exit_on
        self.key_log: list[str] = []
        self.started = False
        self.resized = False

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self.started = True
        self.width = width
        self.height = height
        screen = ScreenBuffer.create(width, height)
        screen.set_line(0, "Hello TUI")
        return screen

    def on_key(self, key: str) -> ScreenBuffer | None:
        self.key_log.append(key)
        if key == self.exit_on:
            return None
        screen = ScreenBuffer.create(self.width, self.height)
        screen.set_line(0, f"Key: {key}")
        return screen

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        self.resized = True
        self.width = width
        self.height = height
        screen = ScreenBuffer.create(width, height)
        screen.set_line(0, "Resized")
        return screen


@pytest.mark.asyncio
class TestTuiRunner:
    async def test_run_tui_app_lifecycle(self):
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput(["a", "b", "Escape"])
        output = CapturedOutput()

        exit_code = await run_tui_app(app, raw_input, output)

        assert exit_code == 0
        assert app.started
        assert app.key_log == ["a", "b", "Escape"]

    async def test_app_exit_on_none(self):
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp(exit_on="q")
        raw_input = MockRawInput(["x", "y", "q"])
        output = CapturedOutput()

        await run_tui_app(app, raw_input, output)
        assert app.key_log == ["x", "y", "q"]

    async def test_eof_handled_gracefully(self):
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput(["a"])  # Will raise EOFError after "a"
        output = CapturedOutput()

        exit_code = await run_tui_app(app, raw_input, output)
        assert exit_code == 0
        assert app.key_log == ["a"]

    async def test_mode_callbacks_called(self):
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput(["Escape"])
        output = CapturedOutput()

        calls: list[str] = []

        exit_code = await run_tui_app(
            app,
            raw_input,
            output,
            enter_raw=lambda: calls.append("enter"),
            exit_raw=lambda: calls.append("exit"),
        )

        assert exit_code == 0
        assert calls == ["enter", "exit"]

    async def test_exit_raw_called_on_eof(self):
        """exit_raw is called even if the input source hits EOF."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput([])  # Immediate EOF
        output = CapturedOutput()

        calls: list[str] = []

        await run_tui_app(
            app,
            raw_input,
            output,
            enter_raw=lambda: calls.append("enter"),
            exit_raw=lambda: calls.append("exit"),
        )

        assert "exit" in calls

    async def test_send_screen_callback(self):
        """When send_screen is provided, screens go through it, not ANSI."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput(["a", "Escape"])
        output = CapturedOutput()

        screens: list[dict] = []

        await run_tui_app(
            app,
            raw_input,
            output,
            send_screen=lambda msg: screens.append(msg),
        )

        # Initial screen + one key screen = 2 screens
        assert len(screens) == 2
        assert all(s["type"] == "screen" for s in screens)
        assert screens[0]["lines"][0] == "Hello TUI"
        assert screens[1]["lines"][0] == "Key: a"

    async def test_ansi_rendering_when_no_send_screen(self):
        """Without send_screen, screens are rendered as ANSI to output."""
        from recursive_neon.shell.tui.runner import run_tui_app

        app = SimpleTuiApp()
        raw_input = MockRawInput(["Escape"])
        output = CapturedOutput()

        await run_tui_app(app, raw_input, output)

        # Output should contain ANSI clear/position codes
        text = output.text
        assert "\033[2J\033[H" in text
