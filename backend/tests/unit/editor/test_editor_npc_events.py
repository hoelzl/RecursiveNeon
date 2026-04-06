"""Tests for NPC-triggered buffer events (Phase 7e-2).

Covers Editor.on_npc_event, *npc-<id>* buffer creation, message
appending, notification styles, and NPCManager.on_message_callback.
"""

from __future__ import annotations

import pytest

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.services.npc_manager import NPCManager


@pytest.fixture
def editor() -> Editor:
    km = build_default_keymap()
    return Editor(global_keymap=km)


class TestOnNpcEvent:
    def test_creates_buffer_on_first_event(self, editor: Editor):
        editor.on_npc_event("npc1", "Alice", "Hello!")
        buf = editor._find_buffer("*npc-npc1*")
        assert buf is not None
        assert "[Alice] Hello!" in buf.text

    def test_appends_to_existing_buffer(self, editor: Editor):
        editor.on_npc_event("npc1", "Alice", "First")
        editor.on_npc_event("npc1", "Alice", "Second")
        buf = editor._find_buffer("*npc-npc1*")
        assert "[Alice] First" in buf.text
        assert "[Alice] Second" in buf.text
        lines = buf.text.split("\n")
        assert len(lines) == 2

    def test_separate_buffers_per_npc(self, editor: Editor):
        editor.on_npc_event("a", "Alice", "Hi")
        editor.on_npc_event("b", "Bob", "Hey")
        assert editor._find_buffer("*npc-a*") is not None
        assert editor._find_buffer("*npc-b*") is not None
        assert "Alice" in editor._find_buffer("*npc-a*").text
        assert "Bob" in editor._find_buffer("*npc-b*").text

    def test_does_not_switch_current_buffer(self, editor: Editor):
        original = editor.buffer.name
        editor.on_npc_event("npc1", "Alice", "Don't switch!")
        assert editor.buffer.name == original

    def test_flash_notification(self, editor: Editor):
        editor._npc_notify = "flash"
        editor.on_npc_event("npc1", "Alice", "Important message")
        assert "[NPC: Alice]" in editor.message
        assert editor._render_requested

    def test_silent_notification(self, editor: Editor):
        editor._npc_notify = "silent"
        editor.message = ""
        editor.on_npc_event("npc1", "Alice", "Quiet message")
        buf = editor._find_buffer("*npc-npc1*")
        assert buf is not None
        # Message should not be set in silent mode
        assert editor.message == ""

    def test_concurrent_events_dont_corrupt(self, editor: Editor):
        for i in range(10):
            editor.on_npc_event("npc1", "Bot", f"Message {i}")
        buf = editor._find_buffer("*npc-npc1*")
        lines = buf.text.split("\n")
        assert len(lines) == 10

    def test_long_message_truncated_in_notification(self, editor: Editor):
        long_msg = "A" * 100
        editor.on_npc_event("npc1", "Alice", long_msg)
        # Message area should truncate
        assert len(editor.message) < 100


class TestNPCManagerCallback:
    def test_callback_field_exists(self, mock_llm):
        mgr = NPCManager(llm=mock_llm)
        assert mgr.on_message_callback is None

    @pytest.mark.asyncio
    async def test_callback_fired_after_chat(self, mock_llm, sample_npc):
        mgr = NPCManager(llm=mock_llm)
        mgr.register_npc(sample_npc)
        received = []
        mgr.on_message_callback = lambda npc_id, name, text: received.append(
            (npc_id, name, text)
        )
        await mgr.chat(sample_npc.id, "Hello")
        assert len(received) == 1
        assert received[0][0] == sample_npc.id
        assert received[0][1] == sample_npc.name

    @pytest.mark.asyncio
    async def test_callback_error_does_not_break_chat(self, mock_llm, sample_npc):
        mgr = NPCManager(llm=mock_llm)
        mgr.register_npc(sample_npc)

        def bad_callback(npc_id, name, text):
            raise RuntimeError("callback boom")

        mgr.on_message_callback = bad_callback
        # Should still return a response without raising
        resp = await mgr.chat(sample_npc.id, "Hello")
        assert resp.message  # response still delivered
