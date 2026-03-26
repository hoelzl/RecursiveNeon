"""
Unit tests for NPCManager

These tests demonstrate the improved testability after refactoring for
dependency injection. The NPCManager can now be tested in complete isolation
without requiring a running Ollama server.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from recursive_neon.models.npc import NPC, NPCPersonality, NPCRole
from recursive_neon.services.npc_manager import NPCManager, _strip_think_tags


class TestNPCManagerWithDependencyInjection:
    """Test suite for NPCManager with mocked LLM dependency."""

    @pytest.fixture
    def mock_llm(self):
        """
        Create a mock LLM compatible with LangChain's Runnable interface.

        This mock replaces the real ChatOllama instance and provides
        invoke/ainvoke returning AIMessage objects.
        """
        from langchain_core.messages import AIMessage

        default_response = "Hello! I'm happy to help you."

        mock = Mock()
        mock.invoke = Mock(return_value=AIMessage(content=default_response))
        mock.ainvoke = AsyncMock(return_value=AIMessage(content=default_response))

        return mock

    @pytest.fixture
    def npc_manager(self, mock_llm):
        """Create an NPCManager instance with injected mock LLM."""
        return NPCManager(llm=mock_llm)

    @pytest.fixture
    def sample_npc(self):
        """Create a sample NPC for testing."""
        return NPC(
            id="test_npc",
            name="Test NPC",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="A helpful test NPC",
            occupation="Tester",
            location="Test Suite",
            greeting="Hello, test!",
            conversation_style="helpful and clear",
            topics_of_interest=["testing", "quality assurance"],
        )

    def test_initialization_with_injected_llm(self, npc_manager, mock_llm):
        """Test that NPCManager correctly uses injected LLM."""
        assert npc_manager.llm is mock_llm
        assert len(npc_manager.npcs) == 0

    def test_initialization_with_default_llm(self):
        """Test that NPCManager can still create default LLM for backward compatibility."""
        # This will create a real ChatOllama instance (may fail without Ollama running)
        # In a real test environment, you might skip this or mock ChatOllama
        manager = NPCManager()
        assert manager.llm is not None

    def test_register_npc(self, npc_manager, sample_npc):
        """Test registering an NPC stores it correctly."""
        npc_manager.register_npc(sample_npc)

        assert sample_npc.id in npc_manager.npcs
        assert npc_manager.npcs[sample_npc.id] == sample_npc

    def test_unregister_npc(self, npc_manager, sample_npc):
        """Test unregistering an NPC removes it from storage."""
        npc_manager.register_npc(sample_npc)
        npc_manager.unregister_npc(sample_npc.id)

        assert sample_npc.id not in npc_manager.npcs

    def test_get_npc_exists(self, npc_manager, sample_npc):
        """Test retrieving an existing NPC."""
        npc_manager.register_npc(sample_npc)
        retrieved = npc_manager.get_npc(sample_npc.id)

        assert retrieved == sample_npc

    def test_get_npc_not_exists(self, npc_manager):
        """Test retrieving a non-existent NPC returns None."""
        retrieved = npc_manager.get_npc("nonexistent_id")
        assert retrieved is None

    def test_list_npcs_empty(self, npc_manager):
        """Test listing NPCs when none are registered."""
        npcs = npc_manager.list_npcs()
        assert npcs == []

    def test_list_npcs_multiple(self, npc_manager, sample_npc):
        """Test listing multiple registered NPCs."""
        npc2 = NPC(
            id="test_npc_2",
            name="Second Test NPC",
            personality=NPCPersonality.PROFESSIONAL,
            role=NPCRole.MERCHANT,
            background="Another test NPC",
            occupation="Trader",
            location="Test Market",
            greeting="Greetings, customer.",
            conversation_style="professional and businesslike",
        )

        npc_manager.register_npc(sample_npc)
        npc_manager.register_npc(npc2)

        npcs = npc_manager.list_npcs()
        assert len(npcs) == 2
        assert sample_npc in npcs
        assert npc2 in npcs

    @pytest.mark.asyncio
    async def test_chat_success(self, npc_manager, sample_npc, mock_llm):
        """
        Test successful chat interaction with mocked LLM.

        This is the key test that demonstrates improved testability - we can
        test the chat logic without needing a real LLM.
        """
        from langchain_core.messages import AIMessage

        expected_response = "I can help you with that!"
        mock_llm.invoke.return_value = AIMessage(content=expected_response)

        npc_manager.register_npc(sample_npc)

        response = await npc_manager.chat(
            npc_id=sample_npc.id,
            message="Hello, can you help me?",
            player_id="test_player",
        )

        # Verify response structure
        assert response.npc_id == sample_npc.id
        assert response.npc_name == sample_npc.name
        assert (
            expected_response in response.message
        )  # Response might be trimmed/processed

        # Verify memory was updated
        assert len(sample_npc.memory.conversation_history) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_chat_npc_not_found(self, npc_manager):
        """Test chat with non-existent NPC raises ValueError."""
        with pytest.raises(ValueError, match="NPC not found"):
            await npc_manager.chat(
                npc_id="nonexistent_npc", message="Hello", player_id="test_player"
            )

    @pytest.mark.asyncio
    async def test_chat_updates_relationship(self, npc_manager, sample_npc, mock_llm):
        """Test that chat updates relationship level based on sentiment."""
        from langchain_core.messages import AIMessage

        response_text = "You're welcome!"
        mock_llm.invoke.return_value = AIMessage(content=response_text)

        npc_manager.register_npc(sample_npc)
        initial_relationship = sample_npc.memory.relationship_level

        # Send a polite message
        await npc_manager.chat(
            npc_id=sample_npc.id,
            message="Thank you so much for your help!",
            player_id="test_player",
        )

        # Relationship should have increased
        assert sample_npc.memory.relationship_level > initial_relationship

    @pytest.mark.asyncio
    async def test_chat_error_handling(self, npc_manager, sample_npc, mock_llm):
        """Test that chat errors propagate and conversation history is rolled back."""
        mock_llm.invoke.side_effect = Exception("LLM error")

        npc_manager.register_npc(sample_npc)
        history_before = len(sample_npc.memory.conversation_history)

        with pytest.raises(Exception, match="LLM error"):
            await npc_manager.chat(
                npc_id=sample_npc.id, message="Hello", player_id="test_player"
            )

        # User message should be rolled back so history is unchanged
        assert len(sample_npc.memory.conversation_history) == history_before

    def test_create_default_npcs(self, npc_manager):
        """Test creating default NPCs."""
        npcs = npc_manager.create_default_npcs()

        # Verify correct number of NPCs created
        assert len(npcs) == 5

        # Verify they were registered
        assert len(npc_manager.npcs) == 5

        # Verify NPC IDs are unique
        npc_ids = [npc.id for npc in npcs]
        assert len(npc_ids) == len(set(npc_ids))

    def test_get_stats(self, npc_manager, sample_npc):
        """Test retrieving manager statistics."""
        npc_manager.register_npc(sample_npc)
        stats = npc_manager.get_stats()

        assert stats["total_npcs"] == 1
        assert len(stats["npcs"]) == 1
        assert stats["npcs"][0]["id"] == sample_npc.id
        assert stats["npcs"][0]["name"] == sample_npc.name
        assert "conversation_length" in stats["npcs"][0]
        assert "relationship_level" in stats["npcs"][0]

    def test_factory_method(self):
        """Test the factory method for creating NPCManager with Ollama."""
        # This creates a real ChatOllama instance, so it might fail without Ollama
        # In practice, you'd mock ChatOllama or skip this test
        with patch(
            "recursive_neon.services.npc_manager.ChatOllama"
        ) as mock_ollama_class:
            mock_llm_instance = Mock()
            mock_ollama_class.return_value = mock_llm_instance

            manager = NPCManager.create_with_ollama(
                ollama_host="localhost", ollama_port=11434
            )

            # Verify ChatOllama was created with correct parameters
            mock_ollama_class.assert_called_once()
            call_kwargs = mock_ollama_class.call_args[1]
            assert "localhost:11434" in call_kwargs["base_url"]
            assert manager.llm is mock_llm_instance


class TestStripThinkTags:
    """Tests for think-tag stripping."""

    def test_strip_think_tags(self):
        assert _strip_think_tags("<think>reasoning</think>Hello!") == "Hello!"

    def test_strip_multiline_think(self):
        text = "<think>\nI should be friendly.\nLet me think...\n</think>Hi there!"
        assert _strip_think_tags(text) == "Hi there!"

    def test_strip_multiple_think_blocks(self):
        text = "<think>a</think>Hello <think>b</think>world"
        assert _strip_think_tags(text) == "Hello world"

    def test_no_think_tags(self):
        assert _strip_think_tags("Just normal text") == "Just normal text"

    def test_empty_string(self):
        assert _strip_think_tags("") == ""

    def test_empty_think_block(self):
        assert _strip_think_tags("<think></think>Result") == "Result"


class TestNPCMemoryInit:
    """Tests for NPC.memory.npc_id auto-sync."""

    def test_memory_npc_id_auto_set(self):
        """memory.npc_id is automatically set to self.id on construction."""
        npc = NPC(
            id="auto_id_test",
            name="Auto",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Tester",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
        )
        assert npc.memory.npc_id == "auto_id_test"

    def test_memory_npc_id_preserved_if_set(self):
        """If memory is provided with a npc_id, it's not overwritten."""
        from recursive_neon.models.npc import NPCMemory

        memory = NPCMemory(npc_id="explicit_id")
        npc = NPC(
            id="npc_id",
            name="Test",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Tester",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
            memory=memory,
        )
        # Provided non-empty npc_id is kept
        assert npc.memory.npc_id == "explicit_id"


class TestNPCMemoryTruncation:
    """Tests for conversation history truncation behavior."""

    def test_add_to_memory_respects_max_history(self):
        npc = NPC(
            id="trunc_test",
            name="T",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Test",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
        )
        for i in range(60):
            npc.add_to_memory("user", f"message {i}", max_history=50)
        assert len(npc.memory.conversation_history) == 50
        assert npc.memory.conversation_history[0].content == "message 10"

    def test_add_to_memory_default_max_history(self):
        npc = NPC(
            id="default_test",
            name="T",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Test",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
        )
        for i in range(55):
            npc.add_to_memory("user", f"msg {i}")
        # Default is 50
        assert len(npc.memory.conversation_history) == 50


class TestNPCSystemPrompt:
    """Tests for the refined NPC system prompt."""

    def test_prompt_includes_rules(self):
        npc = NPC(
            id="test",
            name="Test",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Tester",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
        )
        prompt = npc.get_system_prompt()
        assert "Never break character" in prompt
        assert "1-3 sentences" in prompt
        assert "No meta-commentary" in prompt


class TestNPCPersistence:
    """Tests for NPC save/load persistence."""

    # Uses shared mock_llm fixture from conftest.py

    def test_save_and_load_npcs(self, mock_llm, tmp_path):
        """NPCs with memory survive a save/load round-trip."""
        manager = NPCManager(llm=mock_llm)
        npc = NPC(
            id="test_persist",
            name="Persist NPC",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="Persistence test",
            occupation="Tester",
            location="Disk",
            greeting="Hi!",
            conversation_style="terse",
        )
        npc.memory.npc_id = npc.id
        npc.add_to_memory("user", "Hello")
        npc.add_to_memory("assistant", "Hi there!")
        npc.memory.relationship_level = 10
        manager.register_npc(npc)

        manager.save_npcs_to_disk(str(tmp_path))

        # Load into fresh manager
        fresh = NPCManager(llm=mock_llm)
        assert len(fresh.npcs) == 0
        assert fresh.load_npcs_from_disk(str(tmp_path)) is True
        assert len(fresh.npcs) == 1

        loaded = fresh.get_npc("test_persist")
        assert loaded is not None
        assert loaded.name == "Persist NPC"
        assert loaded.memory.relationship_level == 10
        assert len(loaded.memory.conversation_history) == 2
        assert loaded.memory.conversation_history[0].content == "Hello"

    def test_load_npcs_missing_file(self, mock_llm, tmp_path):
        """Returns False when no saved file exists."""
        manager = NPCManager(llm=mock_llm)
        assert manager.load_npcs_from_disk(str(tmp_path)) is False

    def test_save_default_npcs(self, mock_llm, tmp_path):
        """Default NPCs can be saved and reloaded."""
        manager = NPCManager(llm=mock_llm)
        manager.create_default_npcs()
        manager.save_npcs_to_disk(str(tmp_path))

        fresh = NPCManager(llm=mock_llm)
        assert fresh.load_npcs_from_disk(str(tmp_path)) is True
        assert len(fresh.npcs) == 5

    def test_load_corrupt_npcs_json(self, mock_llm, tmp_path):
        """Corrupt JSON returns False without crashing."""
        (tmp_path / "npcs.json").write_text("{bad", encoding="utf-8")
        manager = NPCManager(llm=mock_llm)
        assert manager.load_npcs_from_disk(str(tmp_path)) is False


class TestNPCManagerBackwardCompatibility:
    """Test that NPCManager maintains backward compatibility."""

    def test_legacy_initialization(self):
        """Test legacy initialization pattern still works."""
        with patch("recursive_neon.services.npc_manager.ChatOllama") as mock_ollama:
            mock_llm = Mock()
            mock_ollama.return_value = mock_llm

            # Old-style initialization
            manager = NPCManager(ollama_host="localhost", ollama_port=11434)

            # Should have created LLM internally
            assert manager.llm is mock_llm
            mock_ollama.assert_called_once()


class TestNPCChatConcurrency:
    """Tests for per-NPC chat lock (fix #9)."""

    async def test_concurrent_chat_serialized(self):
        """Two concurrent chat() calls for the same NPC produce clean history."""
        import asyncio

        from langchain_core.messages import AIMessage

        call_count = 0

        def slow_invoke(messages):
            nonlocal call_count
            call_count += 1
            return AIMessage(content=f"Response {call_count}")

        mock_llm = Mock()
        mock_llm.invoke = slow_invoke

        manager = NPCManager(llm=mock_llm)
        npc = NPC(
            id="concurrent_test",
            name="Conc",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="bg",
            occupation="Tester",
            location="Lab",
            greeting="Hi",
            conversation_style="casual",
        )
        manager.register_npc(npc)

        # Fire two concurrent chat calls
        r1, r2 = await asyncio.gather(
            manager.chat("concurrent_test", "Hello 1"),
            manager.chat("concurrent_test", "Hello 2"),
        )

        # Both should succeed
        assert r1.message.startswith("Response")
        assert r2.message.startswith("Response")

        # History should alternate user/assistant cleanly
        hist = npc.memory.conversation_history
        for i in range(0, len(hist) - 1, 2):
            assert hist[i].role == "user"
            assert hist[i + 1].role == "assistant"

    def test_chat_locks_dict_exists(self):
        """NPCManager has a _chat_locks dict."""
        mock_llm = Mock()
        manager = NPCManager(llm=mock_llm)
        assert hasattr(manager, "_chat_locks")
        assert isinstance(manager._chat_locks, dict)
