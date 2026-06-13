"""Tests for the dired host wiring in ``shell/programs/edit.py``:
``VfsDiredProvider`` (DiredProvider over the real AppService) and the
``edit <directory>`` entry point.

The editor-side behaviour (rendering, commands, prompts) is covered by
``tests/unit/editor/test_dired.py`` against a fake provider; these tests
pin the AppService translation layer.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from recursive_neon.shell.output import CapturedOutput
from recursive_neon.shell.programs import ProgramContext
from recursive_neon.shell.programs.edit import VfsDiredProvider, _run_edit


class _CapturingRunTui:
    """Mock ``run_tui`` that captures the view and returns immediately."""

    def __init__(self) -> None:
        self.view: Any = None

    async def __call__(self, view: Any) -> int:
        self.view = view
        return 0


@pytest.fixture
def fs(test_container):
    """A small known tree under the root: /work/{alpha.txt,beta.py,sub/}."""
    app = test_container.app_service
    root = test_container.game_state.filesystem.root_id
    work = app.create_directory({"name": "work", "parent_id": root})
    app.create_file(
        {"name": "alpha.txt", "parent_id": work.id, "content": "alpha line\n"}
    )
    app.create_file(
        {"name": "beta.py", "parent_id": work.id, "content": "print('beta')\n"}
    )
    sub = app.create_directory({"name": "sub", "parent_id": work.id})
    app.create_file({"name": "gamma.txt", "parent_id": sub.id, "content": "gamma\n"})
    return app


@pytest.fixture
def provider(test_container, fs, make_ctx):
    return VfsDiredProvider(make_ctx(["edit"]))


class TestVfsDiredProvider:
    def test_list_dir(self, provider) -> None:
        entries = {e.name: e for e in provider.list_dir("/work")}
        assert set(entries) == {"alpha.txt", "beta.py", "sub"}
        assert not entries["alpha.txt"].is_dir
        assert entries["alpha.txt"].size == 11  # utf-8 bytes
        assert entries["sub"].is_dir
        assert entries["sub"].nsubdirs == 0

    def test_metadata_counts_subdirs(self, provider) -> None:
        meta = provider.metadata("/work")
        assert meta.is_dir and meta.nsubdirs == 1

    def test_list_dir_errors(self, provider) -> None:
        with pytest.raises(FileNotFoundError):
            provider.list_dir("/nope")
        with pytest.raises(NotADirectoryError):
            provider.list_dir("/work/alpha.txt")

    def test_is_dir(self, provider) -> None:
        assert provider.is_dir("/work") is True
        assert provider.is_dir("/work/alpha.txt") is False
        assert provider.is_dir("/missing") is None

    def test_create_dir_and_collision(self, provider) -> None:
        provider.create_dir("/work/newdir")
        assert provider.is_dir("/work/newdir") is True
        with pytest.raises(FileExistsError):
            provider.create_dir("/work/newdir")

    def test_delete_recursive(self, provider) -> None:
        provider.delete("/work/sub")
        assert provider.is_dir("/work/sub") is None

    def test_rename_within_directory(self, provider) -> None:
        result = provider.rename("/work/beta.py", "/work/mid.txt")
        assert result == "/work/mid.txt"
        names = {e.name for e in provider.list_dir("/work")}
        assert "mid.txt" in names and "beta.py" not in names

    def test_rename_into_existing_directory(self, provider) -> None:
        result = provider.rename("/work/beta.py", "/work/sub")
        assert result == "/work/sub/beta.py"
        assert {e.name for e in provider.list_dir("/work/sub")} == {
            "gamma.txt",
            "beta.py",
        }

    def test_copy_file(self, provider) -> None:
        result = provider.copy("/work/alpha.txt", "/work/copy1.txt")
        assert result == "/work/copy1.txt"
        entries = {e.name: e for e in provider.list_dir("/work")}
        assert entries["copy1.txt"].size == entries["alpha.txt"].size

    def test_copy_directory_recursively(self, provider) -> None:
        provider.copy("/work/sub", "/work/sub2")
        assert {e.name for e in provider.list_dir("/work/sub2")} == {"gamma.txt"}


class TestEditDirectoryArgument:
    def _run_edit_on(self, test_container, args: list[str]) -> Any:
        root_id = test_container.game_state.filesystem.root_id
        run_tui = _CapturingRunTui()
        ctx = ProgramContext(
            args=args,
            stdout=CapturedOutput(),
            stderr=CapturedOutput(),
            env={"USER": "test", "HOME": "/", "HOSTNAME": "test-host"},
            services=test_container,
            cwd_id=root_id,
            run_tui=run_tui,
        )
        code = asyncio.run(_run_edit(ctx))
        assert code == 0
        return run_tui.view

    def test_edit_directory_opens_dired(self, test_container, fs) -> None:
        view = self._run_edit_on(test_container, ["edit", "work"])
        ed = view.editor
        assert ed.buffer.name == "work"
        # The active window must show the dired buffer too — on_key only
        # syncs window↔buffer for switches made during a keystroke, so
        # the host syncs explicitly (the first render was wrong before).
        assert view._tree.active.buffer is ed.buffer
        state = getattr(ed.buffer, "_dired_state", None)
        assert state is not None and state.path == "/work"
        assert ed.buffer.lines[0].startswith("  /work:")
        assert ed.buffer.read_only
        assert any(ln.endswith(" alpha.txt") for ln in ed.buffer.lines)

    def test_edit_file_still_opens_file(self, test_container, fs) -> None:
        view = self._run_edit_on(test_container, ["edit", "work/alpha.txt"])
        ed = view.editor
        assert ed.buffer.name == "alpha.txt"
        assert ed.buffer.text == "alpha line\n"
        assert getattr(ed.buffer, "_dired_state", None) is None

    def test_provider_always_wired(self, test_container, fs) -> None:
        view = self._run_edit_on(test_container, ["edit"])
        assert isinstance(view.editor.dired_provider, VfsDiredProvider)

    def test_tui_app_factories_wired(self, test_container, fs) -> None:
        """edit wires factories for all five hostable TUI apps, and each
        factory builds a working app (editor/app_host.py)."""
        view = self._run_edit_on(test_container, ["edit"])
        factories = view.editor.tui_app_factories
        assert set(factories) == {
            "codebreaker",
            "sysmon",
            "portscan",
            "fsbrowse",
            "memdump",
        }
        for name, factory in factories.items():
            app = factory()
            screen = app.on_start(80, 22)
            assert screen.height == 22, name

    def test_mx_sysmon_hosts_in_editor_window(self, test_container, fs) -> None:
        """End-to-end: M-x sysmon inside an edit session opens the hosted
        buffer with the real app rendered at window size."""
        view = self._run_edit_on(test_container, ["edit"])
        screen = view.on_start(80, 24)
        for key in ["M-x"] + list("sysmon") + ["Enter"]:
            screen = view.on_key(key) or screen
        ed = view.editor
        assert ed.buffer.name == "*sysmon*"
        assert ed.buffer.read_only
        state = ed.buffer._app_host_state
        assert state.height == 22 and not state.finished
        assert view.tick_interval_ms == state.app.tick_interval_ms
