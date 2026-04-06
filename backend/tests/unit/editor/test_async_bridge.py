"""Tests for the general after-key async bridge (Phase 7a-3)."""

from __future__ import annotations

import asyncio

import pytest

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.view import EditorView


def _make_editor() -> Editor:
    ed = Editor()
    ed.global_keymap = build_default_keymap()
    return ed


def _make_view(ed: Editor | None = None) -> EditorView:
    if ed is None:
        ed = _make_editor()
    view = EditorView(ed)
    view.on_start(80, 24)
    return view


class TestAfterKeyQueue:
    def test_after_key_enqueues(self):
        ed = _make_editor()
        assert len(ed._after_key_queue) == 0

        async def cb():
            pass

        ed.after_key(cb)
        assert len(ed._after_key_queue) == 1

    def test_multiple_enqueues(self):
        ed = _make_editor()

        async def cb():
            pass

        ed.after_key(cb)
        ed.after_key(cb)
        ed.after_key(cb)
        assert len(ed._after_key_queue) == 3


@pytest.mark.asyncio
class TestOnAfterKeyDrain:
    async def test_empty_queue_returns_none(self):
        view = _make_view()
        result = await view.on_after_key()
        assert result is None

    async def test_single_callback_runs(self):
        view = _make_view()
        ran = []

        async def cb():
            ran.append(True)

        view.editor.after_key(cb)
        result = await view.on_after_key()
        assert result is not None  # re-rendered
        assert ran == [True]
        assert len(view.editor._after_key_queue) == 0

    async def test_fifo_order(self):
        view = _make_view()
        order = []

        async def cb1():
            order.append(1)

        async def cb2():
            order.append(2)

        async def cb3():
            order.append(3)

        view.editor.after_key(cb1)
        view.editor.after_key(cb2)
        view.editor.after_key(cb3)
        await view.on_after_key()
        assert order == [1, 2, 3]

    async def test_error_isolation(self):
        view = _make_view()
        ran = []

        async def bad():
            raise ValueError("boom")

        async def good():
            ran.append(True)

        view.editor.after_key(bad)
        view.editor.after_key(good)
        result = await view.on_after_key()
        assert result is not None
        assert ran == [True]  # good callback still ran
        assert "boom" in view.editor.message

    async def test_callback_modifying_buffer(self):
        view = _make_view()
        ed = view.editor

        async def insert_text():
            ed.buffer.insert_string("hello from async")

        ed.after_key(insert_text)
        await view.on_after_key()
        assert "hello from async" in ed.buffer.text


@pytest.mark.asyncio
class TestRequestRender:
    async def test_render_requested_triggers_screen(self):
        view = _make_view()
        view.editor.request_render()
        assert view.editor._render_requested
        result = await view.on_after_key()
        assert result is not None
        assert not view.editor._render_requested  # cleared

    async def test_no_request_no_render(self):
        view = _make_view()
        result = await view.on_after_key()
        assert result is None


@pytest.mark.asyncio
class TestAsyncSleepYield:
    async def test_background_task_runs_during_yield(self):
        """A background task scheduled before on_after_key can run
        during the asyncio.sleep(0) yield."""
        view = _make_view()
        ed = view.editor
        completed = []

        async def background():
            completed.append("bg")
            ed.request_render()

        # Simulate a callback that spawns a background task
        async def spawn_bg():
            task = asyncio.create_task(background())
            ed._background_tasks.append(task)

        ed.after_key(spawn_bg)
        result = await view.on_after_key()
        # The background task should have completed during sleep(0)
        assert "bg" in completed
        assert result is not None  # render was requested
