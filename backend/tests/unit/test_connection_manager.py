"""Tests for the WebSocket connection manager."""

from unittest.mock import AsyncMock

from recursive_neon.connection_manager import ConnectionManager
from recursive_neon.services.interfaces import IConnectionManager


class TestConnectionManager:
    async def test_broadcast_removes_dead_connection(self):
        """A socket that fails during broadcast is removed."""
        mgr = ConnectionManager()
        assert isinstance(mgr, IConnectionManager)

        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = Exception("disconnected")

        await mgr.connect(good_ws)
        await mgr.connect(bad_ws)
        assert mgr.active_count == 2

        await mgr.broadcast({"type": "test"})

        good_ws.send_json.assert_called_once_with({"type": "test"})
        assert mgr.active_count == 1
        assert bad_ws not in mgr.active_connections
