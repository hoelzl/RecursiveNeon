"""
Unit tests for NPCManager

These tests demonstrate the improved testability after refactoring for
dependency injection. The NPCManager can now be tested in complete isolation
without requiring a running Ollama server.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.services.npc_manager import NPCManager
from backend.models.npc import NPC, NPCPersonality, NPCRole


class TestNPCManagerWithDependencyInjection:
    """Test suite for NPCManager with mocked LLM dependency."""

    @pytest.fixture
    def mock_llm(self):
        """
        Create a mock LLM that implements the LangChain interface.

        This mock replaces the real ChatOllama instance, allowing us to test
        NPCManager without requiring a running Ollama server.
        """
        mock = Mock()
        # Mock the synchronous predict method (used by ConversationChain)
        mock.predict = Mock(return_value="Hello! I'm happy to help you.")
        # Mock async methods if needed in the future
        mock.ainvoke = AsyncMock(return_value="Async response")
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
            topics_of_interest=["testing", "quality assurance"]
        )

    def test_initialization_with_injected_llm(self, npc_manager, mock_llm):
        """Test that NPCManager correctly uses injected LLM."""
        assert npc_manager.llm is mock_llm
        assert len(npc_manager.npcs) == 0
        assert len(npc_manager.chains) == 0

    def test_initialization_with_default_llm(self):
        """Test that NPCManager can still create default LLM for backward compatibility."""
        # This will create a real ChatOllama instance (may fail without Ollama running)
        # In a real test environment, you might skip this or mock ChatOllama
        manager = NPCManager()
        assert manager.llm is not None

    def test_register_npc(self, npc_manager, sample_npc):
        """Test registering an NPC creates both storage and conversation chain."""
        npc_manager.register_npc(sample_npc)

        # Verify NPC was stored
        assert sample_npc.id in npc_manager.npcs
        assert npc_manager.npcs[sample_npc.id] == sample_npc

        # Verify conversation chain was created
        assert sample_npc.id in npc_manager.chains
        assert npc_manager.chains[sample_npc.id] is not None

    def test_unregister_npc(self, npc_manager, sample_npc):
        """Test unregistering an NPC removes it from storage and chains."""
        npc_manager.register_npc(sample_npc)
        npc_manager.unregister_npc(sample_npc.id)

        assert sample_npc.id not in npc_manager.npcs
        assert sample_npc.id not in npc_manager.chains

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
            location="Test Market"
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
        npc_manager.register_npc(sample_npc)

        # Mock the chain's predict method to return a specific response
        expected_response = "I can help you with that!"
        with patch.object(
            npc_manager.chains[sample_npc.id],
            'predict',
            return_value=expected_response
        ):
            response = await npc_manager.chat(
                npc_id=sample_npc.id,
                message="Hello, can you help me?",
                player_id="test_player"
            )

        # Verify response structure
        assert response.npc_id == sample_npc.id
        assert response.npc_name == sample_npc.name
        assert response.message == expected_response

        # Verify memory was updated
        assert len(sample_npc.memory.conversation_history) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_chat_npc_not_found(self, npc_manager):
        """Test chat with non-existent NPC raises ValueError."""
        with pytest.raises(ValueError, match="NPC not found"):
            await npc_manager.chat(
                npc_id="nonexistent_npc",
                message="Hello",
                player_id="test_player"
            )

    @pytest.mark.asyncio
    async def test_chat_updates_relationship(self, npc_manager, sample_npc):
        """Test that chat updates relationship level based on sentiment."""
        npc_manager.register_npc(sample_npc)
        initial_relationship = sample_npc.memory.relationship_level

        with patch.object(
            npc_manager.chains[sample_npc.id],
            'predict',
            return_value="You're welcome!"
        ):
            # Send a polite message
            await npc_manager.chat(
                npc_id=sample_npc.id,
                message="Thank you so much for your help!",
                player_id="test_player"
            )

        # Relationship should have increased
        assert sample_npc.memory.relationship_level > initial_relationship

    @pytest.mark.asyncio
    async def test_chat_error_handling(self, npc_manager, sample_npc):
        """Test that chat errors are handled gracefully with fallback response."""
        npc_manager.register_npc(sample_npc)

        # Make the chain raise an exception
        with patch.object(
            npc_manager.chains[sample_npc.id],
            'predict',
            side_effect=Exception("LLM error")
        ):
            response = await npc_manager.chat(
                npc_id=sample_npc.id,
                message="Hello",
                player_id="test_player"
            )

        # Should return fallback response instead of crashing
        assert response.npc_id == sample_npc.id
        assert "not sure what to say" in response.message.lower()

    def test_create_default_npcs(self, npc_manager):
        """Test creating default NPCs."""
        npcs = npc_manager.create_default_npcs()

        # Verify correct number of NPCs created
        assert len(npcs) == 5

        # Verify they were registered
        assert len(npc_manager.npcs) == 5
        assert len(npc_manager.chains) == 5

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
        with patch('backend.services.npc_manager.ChatOllama') as mock_ollama_class:
            mock_llm_instance = Mock()
            mock_ollama_class.return_value = mock_llm_instance

            manager = NPCManager.create_with_ollama(
                ollama_host="localhost",
                ollama_port=11434
            )

            # Verify ChatOllama was created with correct parameters
            mock_ollama_class.assert_called_once()
            call_kwargs = mock_ollama_class.call_args[1]
            assert "localhost:11434" in call_kwargs['base_url']
            assert manager.llm is mock_llm_instance


class TestNPCManagerBackwardCompatibility:
    """Test that NPCManager maintains backward compatibility."""

    def test_legacy_initialization(self):
        """Test legacy initialization pattern still works."""
        with patch('backend.services.npc_manager.ChatOllama') as mock_ollama:
            mock_llm = Mock()
            mock_ollama.return_value = mock_llm

            # Old-style initialization
            manager = NPCManager(
                ollama_host="localhost",
                ollama_port=11434
            )

            # Should have created LLM internally
            assert manager.llm is mock_llm
            mock_ollama.assert_called_once()
