"""Tests for TUI app passthrough from shell buffer (Phase 7a-5)."""

from __future__ import annotations

import pytest

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.tui import ScreenBuffer, TuiApp
from recursive_neon.shell.tui.runner import run_tui_app


class FakeRawInput:
    """RawInputSource that feeds a sequence of keys."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = list(keys)

    async def get_key(self, *, timeout: float | None = None) -> str | None:
        if not self._keys:
            raise EOFError
        return self._keys.pop(0)


class FakeOutput:
    def __init__(self):
        self.chunks: list[str] = []

    def write(self, text: str) -> None:
        self.chunks.append(text)


class SimpleApp:
    """A TUI app that shows 'Hello' and exits on 'q'."""

    def on_start(self, width: int, height: int) -> ScreenBuffer:
        self._screen = ScreenBuffer.create(width, height)
        self._screen.set_line(0, "Hello from SimpleApp")
        return self._screen

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key == "q":
            return None  # exit
        return self._screen

    def on_resize(self, width: int, height: int) -> ScreenBuffer:
        return self._screen


class TestLauncherInjection:
    @pytest.mark.asyncio
    async def test_run_tui_app_injects_launcher(self):
        """run_tui_app injects set_tui_launcher on apps that support it."""
        ed = Editor()
        ed.global_keymap = build_default_keymap()
        view = EditorView(ed)

        # run_tui_app should call set_tui_launcher on EditorView
        raw = FakeRawInput(["C-x", "C-c"])  # quit editor
        output = FakeOutput()

        # The editor's on_key("C-x") then "C-c" triggers save-buffers-kill-emacs
        # which sets running=False → on_key returns None → loop exits
        ed.running = False  # shortcut: just exit immediately
        await run_tui_app(view, raw, output, width=80, height=24)

        assert view._tui_launcher is not None
        assert ed.tui_launcher is not None

    @pytest.mark.asyncio
    async def test_launcher_runs_child_app(self):
        """The injected launcher can run a child TUI app."""
        child_started = []
        child_keys = []

        class ChildApp:
            def on_start(self, w, h):
                child_started.append(True)
                return ScreenBuffer.create(w, h)

            def on_key(self, key):
                child_keys.append(key)
                if key == "q":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

        # Simulate what run_tui_app does for the parent
        output = FakeOutput()

        async def launch_child(child: TuiApp) -> int:
            child_raw = FakeRawInput(["a", "b", "q"])
            return await run_tui_app(child, child_raw, output, width=80, height=24)

        result = await launch_child(ChildApp())
        assert child_started == [True]
        assert child_keys == ["a", "b", "q"]
        assert result == 0


class TestShellModeWiring:
    @pytest.mark.asyncio
    async def test_shell_run_tui_factory_set(self, mock_llm):
        """setup_shell_buffer sets _run_tui_factory on the shell."""
        from recursive_neon.config import settings
        from recursive_neon.dependencies import ServiceFactory
        from recursive_neon.editor.shell_mode import setup_shell_buffer
        from recursive_neon.shell.shell import Shell

        container = ServiceFactory.create_test_container(
            mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
        )
        container.app_service.load_initial_filesystem(
            initial_fs_dir=str(settings.initial_fs_path)
        )
        shell = Shell(container)
        ed = Editor()
        ed.global_keymap = build_default_keymap()
        buf = ed.create_buffer("*shell*", "")
        setup_shell_buffer(ed, buf, shell)

        assert shell._run_tui_factory is not None

        # Without a tui_launcher, the factory's run_tui should raise
        run_tui = shell._run_tui_factory()
        with pytest.raises(RuntimeError, match="not available"):
            await run_tui(SimpleApp())

    @pytest.mark.asyncio
    async def test_shell_run_tui_delegates_to_launcher(self, mock_llm):
        """When tui_launcher is set, shell's run_tui delegates to it."""
        from recursive_neon.config import settings
        from recursive_neon.dependencies import ServiceFactory
        from recursive_neon.editor.shell_mode import setup_shell_buffer
        from recursive_neon.shell.shell import Shell

        container = ServiceFactory.create_test_container(
            mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
        )
        container.app_service.load_initial_filesystem(
            initial_fs_dir=str(settings.initial_fs_path)
        )
        shell = Shell(container)
        ed = Editor()
        ed.global_keymap = build_default_keymap()
        buf = ed.create_buffer("*shell*", "")
        setup_shell_buffer(ed, buf, shell)

        launched = []

        async def mock_launcher(app):
            launched.append(app)
            return 0

        ed.tui_launcher = mock_launcher

        run_tui = shell._run_tui_factory()
        app = SimpleApp()
        result = await run_tui(app)
        assert result == 0
        assert launched == [app]
