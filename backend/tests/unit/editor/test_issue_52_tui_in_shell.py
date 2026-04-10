"""Tests for GitHub issue #52: TUI apps in the editor shell.

Root cause: _comint_send_input uses asyncio.create_task to run shell
commands.  When the command launches a child TUI app, the child's
run_tui_app competed with the parent's for keystrokes from the same
raw_input source.

Fix: launch_child signals the parent loop to run the child inline
(single key consumer) instead of starting a concurrent key loop.
"""

from __future__ import annotations

import asyncio

import pytest

from recursive_neon.shell.tui import ScreenBuffer
from recursive_neon.shell.tui.runner import run_tui_app


class AsyncKeyQueue:
    """RawInputSource backed by an asyncio.Queue for controlled key feeding."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()

    def feed(self, key: str) -> None:
        self._queue.put_nowait(key)

    def feed_eof(self) -> None:
        self._queue.put_nowait(None)

    async def get_key(self, *, timeout: float | None = None) -> str | None:
        if timeout is not None:
            try:
                val = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            except TimeoutError:
                return None
        else:
            val = await self._queue.get()
        if val is None:
            raise EOFError
        return val


class DummyOutput:
    def __init__(self):
        self.chunks: list[str] = []

    def write(self, text: str) -> None:
        self.chunks.append(text)


class TrackingApp:
    """Simple TUI app that records keys and exits on Escape."""

    tick_interval_ms = 0

    def __init__(self, name: str) -> None:
        self.name = name
        self.keys: list[str] = []

    def on_start(self, w: int, h: int) -> ScreenBuffer:
        s = ScreenBuffer.create(w, h)
        s.set_line(0, self.name)
        return s

    def on_key(self, key: str) -> ScreenBuffer | None:
        if key == "Escape":
            return None
        self.keys.append(key)
        s = ScreenBuffer.create(80, 24)
        s.set_line(0, f"{self.name} got {key}")
        return s

    def on_resize(self, w: int, h: int) -> ScreenBuffer:
        return ScreenBuffer.create(w, h)


class TestIssue52RawConcurrency:
    """Show that two concurrent run_tui_app on the same raw_input
    splits keystrokes — the exact bug from issue #52."""

    @pytest.mark.asyncio
    async def test_concurrent_apps_split_keys(self):
        keys = AsyncKeyQueue()
        output = DummyOutput()

        app_a = TrackingApp("A")
        app_b = TrackingApp("B")

        task_a = asyncio.create_task(
            run_tui_app(app_a, keys, output, width=80, height=24)
        )
        task_b = asyncio.create_task(
            run_tui_app(app_b, keys, output, width=80, height=24)
        )
        await asyncio.sleep(0.05)

        for c in "abcdef":
            keys.feed(c)
            await asyncio.sleep(0.01)
        keys.feed("Escape")
        await asyncio.sleep(0.01)
        keys.feed("Escape")
        await asyncio.sleep(0.01)

        await asyncio.wait_for(
            asyncio.gather(task_a, task_b, return_exceptions=True),
            timeout=5.0,
        )

        # BUG: keys are split between the two apps
        assert len(app_a.keys) > 0
        assert len(app_b.keys) > 0
        assert len(app_a.keys) + len(app_b.keys) == 6


class TestIssue52Fix:
    """Verify that launch_child runs the child inline so it gets all keys."""

    @pytest.mark.asyncio
    async def test_child_via_launch_child_gets_all_keys(self):
        """When a background task uses launch_child, the parent loop
        runs the child inline — the child receives every keystroke."""
        keys = AsyncKeyQueue()
        output = DummyOutput()
        screens: list[str] = []

        def track_screen(msg: dict) -> None:
            lines = msg.get("lines", [])
            screens.append(lines[0] if lines else "")

        child_app = TrackingApp("CHILD")

        # Parent app that supports set_tui_launcher and on_after_key.
        # Simulates EditorView: on_after_key drains a callback queue
        # and yields so background tasks progress.
        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self.keys: list[str] = []
                self._after_queue: list = []
                self.tui_launcher = None

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                s = ScreenBuffer.create(w, h)
                s.set_line(0, "PARENT")
                return s

            def on_key(self, key):
                self.keys.append(key)
                if key == "Q":
                    return None
                s = ScreenBuffer.create(80, 24)
                s.set_line(0, f"PARENT got {key}")
                return s

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()

        # Start the parent via run_tui_app (which injects launch_child)
        parent_task = asyncio.create_task(
            run_tui_app(
                parent, keys, output, width=80, height=24, send_screen=track_screen
            )
        )
        await asyncio.sleep(0.05)

        # Simulate what _comint_send_input does: feed a key that triggers
        # a background task which calls launch_child
        async def spawn_child():
            async def run():
                await parent.tui_launcher(child_app)

            asyncio.create_task(run())

        # Feed the "trigger" key — parent processes it, on_after_key
        # runs the spawn callback which sets _pending_child
        parent._after_queue.append(spawn_child)
        keys.feed("x")  # triggers parent.on_key then on_after_key
        await asyncio.sleep(0.1)

        # Now the child should be running inline. Feed keys.
        for c in "abcdef":
            keys.feed(c)
            await asyncio.sleep(0.01)

        # Exit child
        keys.feed("Escape")
        await asyncio.sleep(0.1)

        # Exit parent
        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        # The child should have received ALL 6 keys
        assert child_app.keys == ["a", "b", "c", "d", "e", "f"], (
            f"Child got {child_app.keys}, expected all 6 keys. Parent got {parent.keys}"
        )

        # Parent should have received only the trigger key "x"
        # (not any of abcdef, and Q caused it to exit)
        assert "x" in parent.keys

        # Verify screen sequence: parent start, parent-x, child start,
        # child keys, then parent re-renders after child exits
        child_screens = [s for s in screens if "CHILD" in s]
        assert len(child_screens) >= 7  # start + 6 keys

    @pytest.mark.asyncio
    async def test_parent_resumes_after_child_exits(self):
        """After the child exits, the parent loop resumes normally."""
        keys = AsyncKeyQueue()
        output = DummyOutput()
        screens: list[str] = []

        def track_screen(msg: dict) -> None:
            lines = msg.get("lines", [])
            screens.append(lines[0] if lines else "")

        child_app = TrackingApp("CHILD")

        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self.keys: list[str] = []
                self._after_queue: list = []

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                s = ScreenBuffer.create(w, h)
                s.set_line(0, "PARENT")
                return s

            def on_key(self, key):
                self.keys.append(key)
                if key == "Q":
                    return None
                s = ScreenBuffer.create(80, 24)
                s.set_line(0, f"PARENT got {key}")
                return s

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()
        parent_task = asyncio.create_task(
            run_tui_app(
                parent, keys, output, width=80, height=24, send_screen=track_screen
            )
        )
        await asyncio.sleep(0.05)

        # Launch child via trigger key
        async def spawn_child():
            asyncio.create_task(parent.tui_launcher(child_app))

        parent._after_queue.append(spawn_child)
        keys.feed("x")
        await asyncio.sleep(0.1)

        # Child gets a key then exits
        keys.feed("a")
        await asyncio.sleep(0.01)
        keys.feed("Escape")
        await asyncio.sleep(0.1)

        # Now parent should be back in control — send more keys
        keys.feed("y")
        await asyncio.sleep(0.01)
        keys.feed("z")
        await asyncio.sleep(0.01)
        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        assert child_app.keys == ["a"]
        assert "y" in parent.keys
        assert "z" in parent.keys

    @pytest.mark.asyncio
    async def test_child_crash_parent_survives(self):
        """If a child app raises in on_key, the parent loop continues."""
        keys = AsyncKeyQueue()
        output = DummyOutput()
        screens: list[str] = []

        def track_screen(msg: dict) -> None:
            lines = msg.get("lines", [])
            screens.append(lines[0] if lines else "")

        class CrashingChild:
            tick_interval_ms = 0

            def on_start(self, w, h):
                s = ScreenBuffer.create(w, h)
                s.set_line(0, "CRASH_CHILD")
                return s

            def on_key(self, key):
                raise RuntimeError("child crashed!")

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

        child_app = CrashingChild()

        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self.keys: list[str] = []
                self._after_queue: list = []

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                s = ScreenBuffer.create(w, h)
                s.set_line(0, "PARENT")
                return s

            def on_key(self, key):
                self.keys.append(key)
                if key == "Q":
                    return None
                s = ScreenBuffer.create(80, 24)
                s.set_line(0, f"PARENT got {key}")
                return s

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()
        parent_task = asyncio.create_task(
            run_tui_app(
                parent, keys, output, width=80, height=24, send_screen=track_screen
            )
        )
        await asyncio.sleep(0.05)

        async def spawn_child():
            asyncio.create_task(parent.tui_launcher(child_app))

        parent._after_queue.append(spawn_child)
        keys.feed("x")
        await asyncio.sleep(0.1)

        # Feed a key that will cause the child to crash
        keys.feed("a")
        await asyncio.sleep(0.1)

        # Parent should still be alive — send more keys
        keys.feed("y")
        await asyncio.sleep(0.01)
        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        # Parent survived the child crash
        assert "y" in parent.keys

    @pytest.mark.asyncio
    async def test_child_receives_tui_launcher(self):
        """Child app gets set_tui_launcher called before on_start."""
        keys = AsyncKeyQueue()
        output = DummyOutput()
        screens: list[str] = []

        def track_screen(msg: dict) -> None:
            lines = msg.get("lines", [])
            screens.append(lines[0] if lines else "")

        class LauncherTrackingChild:
            tick_interval_ms = 0

            def __init__(self):
                self.got_launcher = False

            def set_tui_launcher(self, launcher):
                self.got_launcher = True

            def on_start(self, w, h):
                s = ScreenBuffer.create(w, h)
                s.set_line(0, "CHILD")
                return s

            def on_key(self, key):
                if key == "Escape":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

        child_app = LauncherTrackingChild()

        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self.keys: list[str] = []
                self._after_queue: list = []

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                return ScreenBuffer.create(w, h)

            def on_key(self, key):
                self.keys.append(key)
                if key == "Q":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()
        parent_task = asyncio.create_task(
            run_tui_app(
                parent, keys, output, width=80, height=24, send_screen=track_screen
            )
        )
        await asyncio.sleep(0.05)

        async def spawn_child():
            asyncio.create_task(parent.tui_launcher(child_app))

        parent._after_queue.append(spawn_child)
        keys.feed("x")
        await asyncio.sleep(0.1)

        keys.feed("Escape")
        await asyncio.sleep(0.1)

        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        assert child_app.got_launcher

    @pytest.mark.asyncio
    async def test_child_on_after_key_called(self):
        """Child app's on_after_key is drained after each keystroke."""
        keys = AsyncKeyQueue()
        output = DummyOutput()

        class AfterKeyChild:
            tick_interval_ms = 0

            def __init__(self):
                self.after_key_calls = 0

            def on_start(self, w, h):
                return ScreenBuffer.create(w, h)

            def on_key(self, key):
                if key == "Escape":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                self.after_key_calls += 1
                return None

        child_app = AfterKeyChild()

        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self._after_queue: list = []

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                return ScreenBuffer.create(w, h)

            def on_key(self, key):
                if key == "Q":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()
        parent_task = asyncio.create_task(
            run_tui_app(
                parent,
                keys,
                output,
                width=80,
                height=24,
                send_screen=lambda msg: None,
            )
        )
        await asyncio.sleep(0.05)

        async def spawn_child():
            asyncio.create_task(parent.tui_launcher(child_app))

        parent._after_queue.append(spawn_child)
        keys.feed("x")
        await asyncio.sleep(0.1)

        # Feed 3 keys to the child
        keys.feed("a")
        await asyncio.sleep(0.01)
        keys.feed("b")
        await asyncio.sleep(0.01)
        keys.feed("c")
        await asyncio.sleep(0.01)
        keys.feed("Escape")
        await asyncio.sleep(0.1)

        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        # on_after_key should have been called once per key
        assert child_app.after_key_calls == 3

    @pytest.mark.asyncio
    async def test_double_launch_child_raises(self):
        """Calling launch_child while one is pending raises RuntimeError."""
        keys = AsyncKeyQueue()
        output = DummyOutput()

        child_a = TrackingApp("A")
        child_b = TrackingApp("B")
        launch_errors: list[Exception] = []

        class ParentApp:
            tick_interval_ms = 0

            def __init__(self):
                self._after_queue: list = []

            def set_tui_launcher(self, launcher):
                self.tui_launcher = launcher

            def on_start(self, w, h):
                return ScreenBuffer.create(w, h)

            def on_key(self, key):
                if key == "Q":
                    return None
                return ScreenBuffer.create(80, 24)

            def on_resize(self, w, h):
                return ScreenBuffer.create(w, h)

            async def on_after_key(self):
                while self._after_queue:
                    cb = self._after_queue.pop(0)
                    await cb()
                await asyncio.sleep(0)
                return None

        parent = ParentApp()
        parent_task = asyncio.create_task(
            run_tui_app(
                parent,
                keys,
                output,
                width=80,
                height=24,
                send_screen=lambda msg: None,
            )
        )
        await asyncio.sleep(0.05)

        async def spawn_both():
            # Launch first child (this will block until child exits)
            asyncio.create_task(parent.tui_launcher(child_a))
            await asyncio.sleep(0)
            # Try to launch second child while first is pending
            try:
                await parent.tui_launcher(child_b)
            except RuntimeError as e:
                launch_errors.append(e)
            # Don't await task_a — it will complete when the child exits

        parent._after_queue.append(spawn_both)
        keys.feed("x")
        await asyncio.sleep(0.2)

        # Exit the first child and the parent
        keys.feed("Escape")
        await asyncio.sleep(0.1)
        keys.feed("Q")
        await asyncio.sleep(0.05)

        await asyncio.wait_for(parent_task, timeout=5.0)

        assert len(launch_errors) == 1
        assert "already pending" in str(launch_errors[0])
