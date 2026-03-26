"""
Tests for the chat program — conversation sub-REPL.

Mocks prompt_toolkit.PromptSession to test the interactive loop.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from recursive_neon.shell.programs.chat import ChatProgram


@pytest.fixture
def chat(test_container):
    """Register default NPCs and return the ChatProgram."""
    test_container.npc_manager.create_default_npcs()
    return ChatProgram()


class TestChatListNPCs:
    """Test `chat` with no NPC argument lists available NPCs."""

    async def test_lists_npcs(self, chat, make_ctx, output):
        ctx = make_ctx(["chat"])
        code = await chat.run(ctx)
        assert code == 0
        assert "Aria" in output.text
        assert "Zero" in output.text
        assert "chat <npc_id>" in output.text

    async def test_lists_no_npcs(self, make_ctx, output):
        # Fresh ChatProgram with no NPCs registered
        ctx = make_ctx(["chat"])
        code = await ChatProgram().run(ctx)
        assert code == 0
        assert "No NPCs" in output.text


class TestChatUnknownNPC:
    """Test `chat <unknown_id>`."""

    async def test_unknown_npc(self, chat, make_ctx, output):
        ctx = make_ctx(["chat", "ghost_npc"])
        code = await chat.run(ctx)
        assert code == 1
        assert "unknown NPC" in output.error_text


class TestChatConversation:
    """Test the interactive chat conversation loop."""

    async def test_exit_command(self, chat, make_ctx, output):
        """User types '/exit' to leave chat."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "Connection closed" in output.text

    async def test_eof_exits(self, chat, make_ctx, output):
        """Ctrl+D (EOFError) exits chat."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=EOFError)
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "Connection closed" in output.text

    async def test_keyboard_interrupt_exits(self, chat, make_ctx, output):
        """Ctrl+C exits chat."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt)
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0

    async def test_chat_sends_message(self, chat, make_ctx, output, mock_llm):
        """A normal message gets sent to the NPC and response is displayed."""
        from langchain_core.messages import AIMessage

        response_text = "Welcome to the lobby!"
        mock_llm.ainvoke.return_value = AIMessage(content=response_text)

        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["Hello!", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)

        assert code == 0
        assert "Aria" in output.text
        assert response_text in output.text

    async def test_empty_input_skipped(self, chat, make_ctx, output):
        """Empty input lines are skipped."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["", "   ", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0

    async def test_slash_help(self, chat, make_ctx, output):
        """/help shows chat commands."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/help", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "/relationship" in output.text
        assert "/status" in output.text

    async def test_slash_relationship(self, chat, make_ctx, output):
        """/relationship shows level."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/relationship", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "Relationship" in output.text

    async def test_slash_status(self, chat, make_ctx, output):
        """/status shows NPC info."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/status", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "Aria" in output.text
        assert "Location" in output.text

    async def test_unknown_slash_command(self, chat, make_ctx, output):
        """/bogus shows error."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/bogus", "/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            code = await chat.run(ctx)
        assert code == 0
        assert "Unknown command" in output.error_text

    async def test_greeting_displayed(self, chat, make_ctx, output):
        """NPC greeting is shown when entering chat."""
        with patch("prompt_toolkit.PromptSession") as MockSession:
            session = MockSession.return_value
            session.prompt_async = AsyncMock(side_effect=["/exit"])
            ctx = make_ctx(["chat", "receptionist_aria"])
            await chat.run(ctx)
        assert "Welcome! How can I assist you today?" in output.text
