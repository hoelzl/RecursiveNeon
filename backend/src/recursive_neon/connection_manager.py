"""Generic WebSocket connection manager."""

from __future__ import annotations

import logging
from typing import Any

from recursive_neon.services.interfaces import IConnectionManager

logger = logging.getLogger(__name__)


class ConnectionManager(IConnectionManager):
    """Manages WebSocket connections."""

    MAX_CONNECTIONS = 50

    def __init__(self) -> None:
        self.active_connections: set[Any] = set()

    @property
    def active_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: Any) -> bool:
        """Accept a WebSocket connection. Returns False if limit reached."""
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Server overloaded")
            logger.warning(
                "Connection rejected: limit reached (%d)", self.MAX_CONNECTIONS
            )
            return False
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("Client connected. Total: %d", len(self.active_connections))
        return True

    def disconnect(self, websocket: Any) -> None:
        self.active_connections.discard(websocket)
        logger.info("Client disconnected. Total: %d", len(self.active_connections))

    async def send_personal(self, message: dict[str, Any], websocket: Any) -> None:
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Stub: does not remove dead connections yet."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to send message to a connection")
