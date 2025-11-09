"""
WebSocket Message Handler Service

This service extracts business logic from WebSocket handlers to improve testability.
It processes different message types and returns responses without knowing about
the WebSocket protocol details.

Benefits:
- Testable without WebSocket connections
- Clear separation of concerns
- Reusable business logic
- Protocol-agnostic message processing
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .interfaces import INPCManager, IOllamaClient
from ..models.game_state import SystemState

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles processing of different message types.

    This class contains the business logic for handling various client requests,
    separated from the WebSocket protocol layer for better testability.
    """

    def __init__(
        self,
        npc_manager: INPCManager,
        ollama_client: Optional[IOllamaClient] = None,
        system_state: Optional[SystemState] = None,
        start_time: Optional[datetime] = None
    ):
        """
        Initialize the message handler.

        Args:
            npc_manager: NPC manager service
            ollama_client: Ollama client service (optional)
            system_state: System state instance (optional)
            start_time: Application start time for uptime calculation (optional)
        """
        self.npc_manager = npc_manager
        self.ollama_client = ollama_client
        self.system_state = system_state or SystemState()
        self.start_time = start_time or datetime.now()

    async def handle_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route and handle a message based on its type.

        Args:
            message_type: The type of message to handle
            data: Message payload data

        Returns:
            Response dictionary with 'type' and 'data' keys

        Raises:
            ValueError: If message type is unknown
        """
        logger.debug(f"Handling message type: {message_type}")

        handler_map = {
            "ping": self._handle_ping,
            "get_npcs": self._handle_get_npcs,
            "chat": self._handle_chat,
            "get_status": self._handle_get_status,
        }

        handler = handler_map.get(message_type)
        if handler is None:
            return self._create_error_response(f"Unknown message type: {message_type}")

        try:
            return await handler(data)
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}", exc_info=True)
            return self._create_error_response(str(e))

    async def _handle_ping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ping message.

        Args:
            data: Message data (unused for ping)

        Returns:
            Pong response
        """
        return {
            "type": "pong",
            "data": {}
        }

    async def _handle_get_npcs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle request to get all NPCs.

        Args:
            data: Message data (unused)

        Returns:
            List of all NPCs
        """
        npcs = self.npc_manager.list_npcs()
        return {
            "type": "npcs_list",
            "data": {
                "npcs": [npc.model_dump(mode='json') for npc in npcs]
            }
        }

    async def _handle_chat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle chat message to an NPC.

        This is the core business logic for NPC chat, extracted from the
        WebSocket handler for testability.

        Args:
            data: Chat data containing npc_id, message, and optionally player_id

        Returns:
            Chat response or error

        Raises:
            ValueError: If required fields are missing
        """
        npc_id = data.get("npc_id")
        message = data.get("message")
        player_id = data.get("player_id", "player_1")

        # Validate required fields
        if not npc_id:
            raise ValueError("Missing required field: npc_id")
        if not message:
            raise ValueError("Missing required field: message")

        # Get response from NPC manager
        response = await self.npc_manager.chat(npc_id, message, player_id)

        return {
            "type": "chat_response",
            "data": response.model_dump(mode='json')
        }

    async def _handle_get_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle request for system status.

        Args:
            data: Message data (unused)

        Returns:
            System status including uptime
        """
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "type": "status",
            "data": {
                "system": self.system_state.model_dump(mode='json'),
                "uptime_seconds": uptime
            }
        }

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            message: Error message

        Returns:
            Error response dictionary
        """
        return {
            "type": "error",
            "data": {"message": message}
        }

    async def create_thinking_indicator(self, npc_id: str) -> Dict[str, Any]:
        """
        Create a thinking indicator message.

        This is called before processing a chat message to indicate
        that the NPC is "thinking".

        Args:
            npc_id: ID of the NPC that is thinking

        Returns:
            Thinking indicator message
        """
        return {
            "type": "chat_thinking",
            "data": {"npc_id": npc_id}
        }
