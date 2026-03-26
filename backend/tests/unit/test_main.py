"""
Tests for the FastAPI application — HTTP endpoints and WebSocket handling.

Covers the biggest coverage gap identified in the code review (main.py was at 0%).
"""

import pytest
from fastapi.testclient import TestClient

from recursive_neon.dependencies import (
    ServiceFactory,
    initialize_container,
    reset_container,
)
from recursive_neon.main import app, handle_ws_message
from recursive_neon.models.game_state import SystemStatus


@pytest.fixture(autouse=True)
def _reset_global_container():
    """Ensure the global container is clean for each test."""
    yield
    reset_container()


@pytest.fixture
def container(mock_llm):
    """A test ServiceContainer with NPCs and filesystem."""
    npc_manager = ServiceFactory.create_npc_manager(llm=mock_llm)
    c = ServiceFactory.create_test_container(mock_npc_manager=npc_manager)
    c.app_service.init_filesystem()
    npc_manager.create_default_npcs()
    c.system_state.status = SystemStatus.READY
    # Configure mock return values for endpoints that call these
    c.process_manager.get_status.return_value = {
        "running": False,
        "pid": None,
        "memory_mb": 0,
        "cpu_percent": 0,
    }
    return c


@pytest.fixture
def client(container):
    """A FastAPI TestClient with initialized container."""
    initialize_container(container)
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# HTTP endpoint tests
# ============================================================================


class TestRootEndpoint:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Recursive://Neon"
        assert data["version"] == "0.2.0"
        assert data["status"] == "ready"


class TestHealthEndpoint:
    def test_health_ready(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["system"]["status"] == "ready"

    def test_health_unhealthy(self, client, container):
        container.system_state.status = SystemStatus.ERROR
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "unhealthy"


class TestNPCEndpoints:
    def test_list_npcs(self, client):
        resp = client.get("/npcs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["npcs"]) == 5

    def test_get_npc_exists(self, client):
        resp = client.get("/npcs/receptionist_aria")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Aria"

    def test_get_npc_not_found(self, client):
        resp = client.get("/npcs/nonexistent")
        assert resp.status_code == 404

    def test_chat_success(self, client, mock_llm):
        from langchain_core.messages import AIMessage

        response_text = "Hello there!"
        mock_llm.invoke.return_value = AIMessage(content=response_text)

        resp = client.post(
            "/chat",
            json={
                "npc_id": "receptionist_aria",
                "message": "Hi",
                "player_id": "player_1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["npc_id"] == "receptionist_aria"
        assert data["npc_name"] == "Aria"

    def test_chat_npc_not_found(self, client):
        resp = client.post(
            "/chat",
            json={
                "npc_id": "nonexistent",
                "message": "Hi",
                "player_id": "player_1",
            },
        )
        assert resp.status_code == 404


class TestStatsEndpoint:
    def test_stats(self, client):
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "system" in data
        assert "npc_manager" in data
        assert data["npc_manager"]["total_npcs"] == 5


# ============================================================================
# WebSocket message handler tests
# ============================================================================


class TestHandleWsMessage:
    """Test the handle_ws_message function directly (no real WebSocket needed)."""

    @pytest.fixture
    def ws_container(self, container):
        return container

    async def test_ping(self, ws_container):
        resp = await handle_ws_message(ws_container, "ping", {})
        assert resp["type"] == "pong"

    async def test_get_npcs(self, ws_container):
        resp = await handle_ws_message(ws_container, "get_npcs", {})
        assert resp["type"] == "npcs_list"
        assert len(resp["data"]["npcs"]) == 5

    async def test_chat_message(self, ws_container, mock_llm):
        from langchain_core.messages import AIMessage

        response_text = "I can help!"
        mock_llm.invoke.return_value = AIMessage(content=response_text)

        resp = await handle_ws_message(
            ws_container,
            "chat",
            {"npc_id": "receptionist_aria", "message": "Hello"},
        )
        assert resp["type"] == "chat_response"
        assert resp["data"]["npc_name"] == "Aria"

    async def test_unknown_type(self, ws_container):
        resp = await handle_ws_message(ws_container, "bogus", {})
        assert resp["type"] == "error"
        assert "Unknown message type" in resp["data"]["message"]

    async def test_app_filesystem_init(self, ws_container):
        resp = await handle_ws_message(
            ws_container,
            "app",
            {"app_type": "filesystem", "action": "init"},
        )
        assert resp["type"] == "app_response"
        assert "root" in resp["data"]

    async def test_app_notes_get_all(self, ws_container):
        resp = await handle_ws_message(
            ws_container,
            "app",
            {"app_type": "notes", "action": "get_all"},
        )
        assert resp["type"] == "app_response"
        assert "notes" in resp["data"]

    async def test_app_unknown_type(self, ws_container):
        resp = await handle_ws_message(
            ws_container,
            "app",
            {"app_type": "unknown", "action": "foo"},
        )
        assert resp["type"] == "error"


# ============================================================================
# WebSocket integration test
# ============================================================================


class TestWebSocket:
    def test_websocket_ping_pong(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping", "data": {}})
            resp = ws.receive_json()
            assert resp["type"] == "pong"

    def test_websocket_get_npcs(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "get_npcs", "data": {}})
            resp = ws.receive_json()
            assert resp["type"] == "npcs_list"
            assert len(resp["data"]["npcs"]) == 5


# ============================================================================
# Lifespan / NPC persistence regression test
# ============================================================================


class TestLifespanNPCPersistence:
    """Regression test for Critical Issue #1: lifespan must not overwrite
    NPC state that was already loaded by create_production_container()."""

    def test_lifespan_does_not_call_create_default_npcs(self):
        """Verify main.py lifespan doesn't re-create default NPCs."""
        import ast
        from pathlib import Path

        # Parse main.py and check that create_default_npcs is not called in lifespan
        main_path = (
            Path(__file__).parent.parent.parent / "src" / "recursive_neon" / "main.py"
        )
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find the lifespan function
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
                # Check that no call to create_default_npcs exists
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Attribute)
                        and child.attr == "create_default_npcs"
                    ):
                        pytest.fail(
                            "lifespan() calls create_default_npcs() — "
                            "this overwrites NPCs loaded from disk"
                        )
                break

    def test_lifespan_saves_all_state_not_just_filesystem(self):
        """Verify main.py lifespan calls save_all_to_disk and save_npcs_to_disk."""
        import ast
        from pathlib import Path

        main_path = (
            Path(__file__).parent.parent.parent / "src" / "recursive_neon" / "main.py"
        )
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
                attrs = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        attrs.add(child.attr)
                assert "save_all_to_disk" in attrs, (
                    "lifespan should call save_all_to_disk, not just save_filesystem_to_disk"
                )
                assert "save_npcs_to_disk" in attrs, (
                    "lifespan should call save_npcs_to_disk to persist NPC state"
                )
                break
