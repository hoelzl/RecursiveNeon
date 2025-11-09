"""
Unit tests for MessageHandler

These tests demonstrate how extracting business logic from WebSocket handlers
into a service layer makes it testable without WebSocket connections.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from backend.services.message_handler import MessageHandler
from backend.models.npc import NPC, ChatResponse, NPCPersonality, NPCRole
from backend.models.game_state import SystemState, SystemStatus


class TestMessageHandler:
    """Test suite for MessageHandler service."""

    @pytest.fixture
    def mock_npc_manager(self):
        """Create a mock NPC manager."""
        mock = AsyncMock()
        mock.list_npcs = Mock(return_value=[])
        mock.chat = AsyncMock()
        return mock

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def system_state(self):
        """Create a system state for testing."""
        state = SystemState()
        state.status = SystemStatus.READY
        state.ollama_running = True
        return state

    @pytest.fixture
    def message_handler(self, mock_npc_manager, mock_ollama_client, system_state):
        """Create a MessageHandler with mocked dependencies."""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        return MessageHandler(
            npc_manager=mock_npc_manager,
            ollama_client=mock_ollama_client,
            system_state=system_state,
            start_time=start_time
        )

    @pytest.mark.asyncio
    async def test_handle_ping(self, message_handler):
        """Test ping message handling."""
        response = await message_handler.handle_message("ping", {})

        assert response["type"] == "pong"
        assert response["data"] == {}

    @pytest.mark.asyncio
    async def test_handle_get_npcs(self, message_handler, mock_npc_manager):
        """Test getting NPC list."""
        # Setup mock NPCs
        npc1 = NPC(
            id="npc1",
            name="Test NPC 1",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.INFORMANT,
            background="Test background",
            occupation="Test occupation",
            location="Test location",
            greeting="Hello!",
            conversation_style="friendly"
        )
        npc2 = NPC(
            id="npc2",
            name="Test NPC 2",
            personality=NPCPersonality.PROFESSIONAL,
            role=NPCRole.MERCHANT,
            background="Professional background",
            occupation="Merchant",
            location="Market",
            greeting="Welcome!",
            conversation_style="professional"
        )
        mock_npc_manager.list_npcs.return_value = [npc1, npc2]

        response = await message_handler.handle_message("get_npcs", {})

        assert response["type"] == "npcs_list"
        assert "npcs" in response["data"]
        assert len(response["data"]["npcs"]) == 2
        mock_npc_manager.list_npcs.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_chat_success(self, message_handler, mock_npc_manager):
        """Test successful chat message handling."""
        # Setup mock response
        mock_response = ChatResponse(
            npc_id="npc1",
            npc_name="Test NPC",
            message="Hello, how can I help you?"
        )
        mock_npc_manager.chat.return_value = mock_response

        data = {
            "npc_id": "npc1",
            "message": "Hi there!",
            "player_id": "player1"
        }

        response = await message_handler.handle_message("chat", data)

        assert response["type"] == "chat_response"
        assert response["data"]["npc_id"] == "npc1"
        assert response["data"]["message"] == "Hello, how can I help you?"

        # Verify chat was called with correct parameters
        mock_npc_manager.chat.assert_called_once_with("npc1", "Hi there!", "player1")

    @pytest.mark.asyncio
    async def test_handle_chat_missing_npc_id(self, message_handler):
        """Test chat with missing npc_id returns error."""
        data = {
            "message": "Hi there!"
        }

        response = await message_handler.handle_message("chat", data)

        assert response["type"] == "error"
        assert "npc_id" in response["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_chat_missing_message(self, message_handler):
        """Test chat with missing message returns error."""
        data = {
            "npc_id": "npc1"
        }

        response = await message_handler.handle_message("chat", data)

        assert response["type"] == "error"
        assert "message" in response["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_chat_default_player_id(self, message_handler, mock_npc_manager):
        """Test chat uses default player_id when not provided."""
        mock_response = ChatResponse(
            npc_id="npc1",
            npc_name="Test NPC",
            message="Hello!"
        )
        mock_npc_manager.chat.return_value = mock_response

        data = {
            "npc_id": "npc1",
            "message": "Hi!"
        }

        await message_handler.handle_message("chat", data)

        # Verify default player_id was used
        mock_npc_manager.chat.assert_called_once_with("npc1", "Hi!", "player_1")

    @pytest.mark.asyncio
    async def test_handle_get_status(self, message_handler, system_state):
        """Test status request handling."""
        # Set a known start time
        message_handler.start_time = datetime(2024, 1, 1, 12, 0, 0)

        # Mock current time to calculate uptime
        with patch('backend.services.message_handler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 5, 30)

            response = await message_handler.handle_message("get_status", {})

        assert response["type"] == "status"
        assert "system" in response["data"]
        assert "uptime_seconds" in response["data"]
        assert response["data"]["uptime_seconds"] == 330  # 5 minutes 30 seconds

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, message_handler):
        """Test unknown message type returns error."""
        response = await message_handler.handle_message("unknown_type", {})

        assert response["type"] == "error"
        assert "unknown message type" in response["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_message_exception(self, message_handler, mock_npc_manager):
        """Test that exceptions in handlers are caught and return errors."""
        # Make the mock raise an exception
        mock_npc_manager.list_npcs.side_effect = Exception("Database error")

        response = await message_handler.handle_message("get_npcs", {})

        assert response["type"] == "error"
        assert "database error" in response["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_create_thinking_indicator(self, message_handler):
        """Test creating thinking indicator message."""
        indicator = await message_handler.create_thinking_indicator("npc1")

        assert indicator["type"] == "chat_thinking"
        assert indicator["data"]["npc_id"] == "npc1"

    @pytest.mark.asyncio
    async def test_chat_with_npc_manager_error(self, message_handler, mock_npc_manager):
        """Test chat when NPC manager raises ValueError."""
        mock_npc_manager.chat.side_effect = ValueError("NPC not found")

        data = {
            "npc_id": "nonexistent",
            "message": "Hi!"
        }

        response = await message_handler.handle_message("chat", data)

        assert response["type"] == "error"
        assert "not found" in response["data"]["message"].lower()

    def test_create_error_response(self, message_handler):
        """Test error response creation."""
        error = message_handler._create_error_response("Test error")

        assert error["type"] == "error"
        assert error["data"]["message"] == "Test error"


class TestMessageHandlerIntegration:
    """Integration tests with real (non-mocked) dependencies."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """
        Test a complete message flow with minimal mocking.

        This demonstrates how the refactored code enables integration testing
        of business logic without requiring WebSocket infrastructure.
        """
        # Create real system state
        system_state = SystemState()
        system_state.status = SystemStatus.READY

        # Create mock NPC manager with realistic behavior
        mock_npc_manager = Mock()
        test_npc = NPC(
            id="guide",
            name="Luna",
            personality=NPCPersonality.FRIENDLY,
            role=NPCRole.COMPANION,
            background="A helpful AI guide",
            occupation="Digital Guide",
            location="Tutorial Zone",
            greeting="Hi! I'm Luna, your guide.",
            conversation_style="friendly and patient"
        )
        # list_npcs is synchronous, not async
        mock_npc_manager.list_npcs = Mock(return_value=[test_npc])
        # chat is async
        mock_npc_manager.chat = AsyncMock(return_value=ChatResponse(
            npc_id="guide",
            npc_name="Luna",
            message="Welcome! How can I help you today?"
        ))

        # Create message handler
        handler = MessageHandler(
            npc_manager=mock_npc_manager,
            system_state=system_state,
            start_time=datetime.now()
        )

        # Test sequence of messages
        # 1. Get NPCs
        response1 = await handler.handle_message("get_npcs", {})
        assert response1["type"] == "npcs_list"
        assert len(response1["data"]["npcs"]) == 1

        # 2. Chat with NPC
        response2 = await handler.handle_message("chat", {
            "npc_id": "guide",
            "message": "Hello!",
            "player_id": "test_player"
        })
        assert response2["type"] == "chat_response"
        assert response2["data"]["npc_name"] == "Luna"

        # 3. Ping
        response3 = await handler.handle_message("ping", {})
        assert response3["type"] == "pong"
