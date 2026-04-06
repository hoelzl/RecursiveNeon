"""Tests for save-hook event publishing (Phase 7e-3).

Covers the integration between save-buffer, Buffer.on_save, and
GameEventBus event publishing.
"""

from __future__ import annotations

import pytest

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.services.game_event_bus import GameEventBus


@pytest.fixture
def editor() -> Editor:
    km = build_default_keymap()
    return Editor(global_keymap=km)


class TestSaveBufferPublishesEvent:
    def test_save_publishes_event(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.save_callback = lambda buf: True
        editor.buffer.filepath = "test.txt"

        received = []
        bus.subscribe("editor.buffer_saved", lambda t, d: received.append(d))

        editor.execute_command("save-buffer")
        assert len(received) == 1
        assert received[0]["buffer_name"] == "*scratch*"
        assert received[0]["filepath"] == "test.txt"
        assert received[0]["contents"] == editor.buffer.text

    def test_no_event_on_failed_save(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.save_callback = lambda buf: False

        received = []
        bus.subscribe("editor.buffer_saved", lambda t, d: received.append(d))

        editor.execute_command("save-buffer")
        assert len(received) == 0

    def test_no_event_without_bus(self, editor: Editor):
        # Should not crash when event_bus is None
        editor.save_callback = lambda buf: True
        editor.buffer.filepath = "test.txt"
        editor.execute_command("save-buffer")  # no error

    def test_on_save_hook_publishes_event(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.buffer.on_save = lambda buf: True
        editor.buffer.filepath = "note.txt"

        received = []
        bus.subscribe("editor.buffer_saved", lambda t, d: received.append(d))

        editor.execute_command("save-buffer")
        assert len(received) == 1

    def test_on_save_takes_priority_over_save_callback(self, editor: Editor):
        callback_calls = []
        on_save_calls = []
        editor.save_callback = lambda buf: (callback_calls.append(1), True)[-1]
        editor.buffer.on_save = lambda buf: (on_save_calls.append(1), True)[-1]

        editor.execute_command("save-buffer")
        assert len(on_save_calls) == 1
        assert len(callback_calls) == 0

    def test_fallback_to_save_callback_when_on_save_fails(self, editor: Editor):
        editor.buffer.on_save = lambda buf: False
        editor.save_callback = lambda buf: True
        editor.buffer.filepath = "test.txt"

        bus = GameEventBus()
        editor.event_bus = bus
        received = []
        bus.subscribe("editor.buffer_saved", lambda t, d: received.append(d))

        editor.execute_command("save-buffer")
        # on_save returned False, so save_callback should be called
        # Actually, when on_save returns True we stop — when False we fall through
        # Let's verify the fallback works
        assert len(received) == 1  # save_callback succeeded

    def test_multiple_subscribers_all_receive(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.save_callback = lambda buf: True
        editor.buffer.filepath = "test.txt"

        a, b = [], []
        bus.subscribe("editor.buffer_saved", lambda t, d: a.append(d))
        bus.subscribe("editor.buffer_saved", lambda t, d: b.append(d))

        editor.execute_command("save-buffer")
        assert len(a) == 1
        assert len(b) == 1

    def test_unsubscribed_handler_not_called(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.save_callback = lambda buf: True
        editor.buffer.filepath = "test.txt"

        calls = []
        handler = lambda t, d: calls.append(1)  # noqa: E731
        bus.subscribe("editor.buffer_saved", handler)
        bus.unsubscribe("editor.buffer_saved", handler)

        editor.execute_command("save-buffer")
        assert len(calls) == 0


class TestWriteFilePublishesEvent:
    def test_write_file_publishes_event(self, editor: Editor):
        bus = GameEventBus()
        editor.event_bus = bus
        editor.save_callback = lambda buf: True

        received = []
        bus.subscribe("editor.buffer_saved", lambda t, d: received.append(d))

        editor.execute_command("write-file")
        assert editor.minibuffer is not None
        editor.minibuffer.text = "/new/path.txt"
        editor.minibuffer.cursor = len("/new/path.txt")
        editor.minibuffer.process_key("Enter")

        assert len(received) == 1
        assert received[0]["filepath"] == "/new/path.txt"
