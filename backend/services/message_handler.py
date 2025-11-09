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
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from .interfaces import INPCManager, IOllamaClient
from ..models.game_state import SystemState

if TYPE_CHECKING:
    from .app_service import AppService

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
        start_time: Optional[datetime] = None,
        app_service: Optional["AppService"] = None
    ):
        """
        Initialize the message handler.

        Args:
            npc_manager: NPC manager service
            ollama_client: Ollama client service (optional)
            system_state: System state instance (optional)
            start_time: Application start time for uptime calculation (optional)
            app_service: Desktop app service (optional)
        """
        self.npc_manager = npc_manager
        self.ollama_client = ollama_client
        self.system_state = system_state or SystemState()
        self.start_time = start_time or datetime.now()
        self.app_service = app_service

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
            # Desktop app handlers
            "app": self._handle_app_operation,
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

    async def _handle_app_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle desktop app operations.

        Message format:
        {
            "type": "app",
            "data": {
                "operation": "notes.list" | "notes.create" | "notes.update" | ...,
                "payload": { ... }
            }
        }
        """
        if not self.app_service:
            return self._create_error_response("App service not available")

        operation = data.get("operation")
        payload = data.get("payload", {})

        try:
            # Notes operations
            if operation == "notes.list":
                notes = self.app_service.get_notes()
                return {"type": "app_response", "data": {"notes": [n.model_dump() for n in notes]}}
            elif operation == "notes.get":
                note = self.app_service.get_note(payload["id"])
                return {"type": "app_response", "data": {"note": note.model_dump()}}
            elif operation == "notes.create":
                note = self.app_service.create_note(payload)
                return {"type": "app_response", "data": {"note": note.model_dump()}}
            elif operation == "notes.update":
                note = self.app_service.update_note(payload["id"], payload)
                return {"type": "app_response", "data": {"note": note.model_dump()}}
            elif operation == "notes.delete":
                self.app_service.delete_note(payload["id"])
                return {"type": "app_response", "data": {"success": True}}

            # Task list operations
            elif operation == "tasks.lists":
                lists = self.app_service.get_task_lists()
                return {"type": "app_response", "data": {"lists": [l.model_dump() for l in lists]}}
            elif operation == "tasks.list.create":
                task_list = self.app_service.create_task_list(payload)
                return {"type": "app_response", "data": {"list": task_list.model_dump()}}
            elif operation == "tasks.list.update":
                task_list = self.app_service.update_task_list(payload["id"], payload)
                return {"type": "app_response", "data": {"list": task_list.model_dump()}}
            elif operation == "tasks.list.delete":
                self.app_service.delete_task_list(payload["id"])
                return {"type": "app_response", "data": {"success": True}}
            elif operation == "tasks.create":
                task = self.app_service.create_task(payload["list_id"], payload)
                return {"type": "app_response", "data": {"task": task.model_dump()}}
            elif operation == "tasks.update":
                task = self.app_service.update_task(payload["list_id"], payload["id"], payload)
                return {"type": "app_response", "data": {"task": task.model_dump()}}
            elif operation == "tasks.delete":
                self.app_service.delete_task(payload["list_id"], payload["id"])
                return {"type": "app_response", "data": {"success": True}}

            # Filesystem operations
            elif operation == "fs.init":
                root = self.app_service.init_filesystem()
                return {"type": "app_response", "data": {"root": root.model_dump()}}
            elif operation == "fs.list":
                nodes = self.app_service.list_directory(payload["dir_id"])
                return {"type": "app_response", "data": {"nodes": [n.model_dump() for n in nodes]}}
            elif operation == "fs.get":
                node = self.app_service.get_file(payload["id"])
                return {"type": "app_response", "data": {"node": node.model_dump()}}
            elif operation == "fs.create.dir":
                directory = self.app_service.create_directory(payload)
                return {"type": "app_response", "data": {"node": directory.model_dump()}}
            elif operation == "fs.create.file":
                file = self.app_service.create_file(payload)
                return {"type": "app_response", "data": {"node": file.model_dump()}}
            elif operation == "fs.update":
                node = self.app_service.update_file(payload["id"], payload)
                return {"type": "app_response", "data": {"node": node.model_dump()}}
            elif operation == "fs.delete":
                self.app_service.delete_file(payload["id"])
                return {"type": "app_response", "data": {"success": True}}
            elif operation == "fs.copy":
                copy = self.app_service.copy_file(
                    payload["id"],
                    payload["target_parent_id"],
                    payload.get("new_name")
                )
                return {"type": "app_response", "data": {"node": copy.model_dump()}}
            elif operation == "fs.move":
                node = self.app_service.move_file(payload["id"], payload["target_parent_id"])
                return {"type": "app_response", "data": {"node": node.model_dump()}}

            # Browser operations
            elif operation == "browser.pages":
                pages = self.app_service.get_browser_pages()
                return {"type": "app_response", "data": {"pages": [p.model_dump() for p in pages]}}
            elif operation == "browser.page.get":
                page = self.app_service.get_browser_page_by_url(payload["url"])
                if page:
                    return {"type": "app_response", "data": {"page": page.model_dump()}}
                return self._create_error_response(f"Page not found: {payload['url']}")
            elif operation == "browser.page.create":
                page = self.app_service.create_browser_page(payload)
                return {"type": "app_response", "data": {"page": page.model_dump()}}
            elif operation == "browser.bookmarks":
                bookmarks = self.app_service.get_bookmarks()
                return {"type": "app_response", "data": {"bookmarks": bookmarks}}
            elif operation == "browser.bookmark.add":
                self.app_service.add_bookmark(payload["url"])
                return {"type": "app_response", "data": {"success": True}}
            elif operation == "browser.bookmark.remove":
                self.app_service.remove_bookmark(payload["url"])
                return {"type": "app_response", "data": {"success": True}}

            else:
                return self._create_error_response(f"Unknown app operation: {operation}")

        except Exception as e:
            logger.error(f"Error in app operation {operation}: {e}", exc_info=True)
            return self._create_error_response(str(e))

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
