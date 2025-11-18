"""
Integration tests for FastAPI Lifespan Hooks

Tests the application startup and shutdown sequences defined in main.py.
Uses FastAPI's TestClient to trigger lifespan events.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager

from recursive_neon.main import app, lifespan
from recursive_neon.dependencies import ServiceContainer, ServiceFactory
from recursive_neon.models.game_state import SystemStatus


@pytest.mark.integration
class TestLifespanStartup:
    """Test application startup sequence."""

    @pytest.mark.asyncio
    async def test_startup_sequence_success(self):
        """Test successful startup sequence."""
        # Create a mock container
        mock_container = Mock(spec=ServiceContainer)

        # Mock services
        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = [
            "qwen3:4b",
            "llama3.2:3b"
        ]
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = [
            Mock(id="npc1"),
            Mock(id="npc2")
        ]

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        # Patch ServiceFactory to return our mock container
        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                # Create a test FastAPI app with our lifespan
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                # Use TestClient to trigger lifespan
                with TestClient(test_app) as client:
                    # Startup should have completed
                    pass

                # Verify startup sequence
                mock_container.process_manager.start.assert_called_once()
                mock_container.ollama_client.wait_for_ready.assert_called_once()
                mock_container.ollama_client.list_models.assert_called_once()
                mock_container.npc_manager.create_default_npcs.assert_called_once()

                # Verify shutdown sequence
                mock_container.app_service.save_filesystem_to_disk.assert_called_once()
                mock_container.ollama_client.close.assert_called_once()
                mock_container.process_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_process_manager_failure(self):
        """Test startup failure when process manager fails to start."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = False  # Failure
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.close = AsyncMock()

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                # Should raise exception during startup
                with pytest.raises(Exception, match="Failed to start ollama server"):
                    with TestClient(test_app):
                        pass

    @pytest.mark.asyncio
    async def test_startup_ollama_not_ready(self):
        """Test startup failure when ollama doesn't become ready."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = False  # Not ready

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with pytest.raises(Exception, match="Ollama server did not become ready"):
                    with TestClient(test_app):
                        pass

    @pytest.mark.asyncio
    async def test_startup_sets_system_state(self):
        """Test that startup sets system state correctly."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = ["model1", "model2"]
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = [
            Mock(), Mock(), Mock()
        ]

        # Track status changes
        status_values = []

        def track_status(value):
            status_values.append(value)

        mock_container.system_state = Mock()
        type(mock_container.system_state).status = property(
            lambda self: status_values[-1] if status_values else SystemStatus.INITIALIZING,
            lambda self, value: track_status(value)
        )
        mock_container.system_state.ollama_running = None
        mock_container.system_state.ollama_models_loaded = None
        mock_container.system_state.npcs_loaded = None

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app):
                    pass

                # Verify system state was updated during startup
                assert mock_container.system_state.ollama_running is True
                assert mock_container.system_state.ollama_models_loaded == ["model1", "model2"]
                assert mock_container.system_state.npcs_loaded == 3
                # Status should have been READY at some point, then SHUTTING_DOWN
                assert SystemStatus.READY in status_values
                assert SystemStatus.SHUTTING_DOWN in status_values


@pytest.mark.integration
class TestLifespanShutdown:
    """Test application shutdown sequence."""

    @pytest.mark.asyncio
    async def test_shutdown_saves_filesystem(self):
        """Test that shutdown saves filesystem state."""
        mock_container = Mock(spec=ServiceContainer)

        # Setup for successful startup
        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        # Shutdown services
        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app):
                    pass

                # Verify filesystem was saved
                mock_container.app_service.save_filesystem_to_disk.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_saves_calendar(self):
        """Test that shutdown saves calendar data."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                with patch('recursive_neon.config.settings') as mock_settings:
                    mock_settings.game_data_path = Mock()

                    from fastapi import FastAPI

                    test_app = FastAPI(lifespan=lifespan)

                    with TestClient(test_app):
                        pass

                    # Verify calendar was saved
                    mock_container.calendar_service.save_to_disk.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_filesystem_save_error(self):
        """Test that shutdown continues even if filesystem save fails."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        # Make filesystem save fail
        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk.side_effect = Exception("Save failed")

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                # Should not raise exception during shutdown
                with TestClient(test_app):
                    pass

                # Other cleanup should still happen
                mock_container.ollama_client.close.assert_called_once()
                mock_container.process_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_ollama_client(self):
        """Test that shutdown closes ollama client."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app):
                    pass

                # Verify ollama client was closed
                mock_container.ollama_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_stops_process_manager(self):
        """Test that shutdown stops process manager."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app):
                    pass

                # Verify process manager was stopped
                mock_container.process_manager.stop.assert_called_once()


@pytest.mark.integration
class TestLifespanErrorHandling:
    """Test error handling during lifespan events."""

    @pytest.mark.asyncio
    async def test_startup_error_sets_error_state(self):
        """Test that startup errors set system state to ERROR."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.side_effect = Exception("Startup failed")
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.close = AsyncMock()

        # Track status changes
        status_values = []
        last_error_value = [None]

        def track_status(value):
            status_values.append(value)

        def track_last_error(value):
            last_error_value[0] = value

        mock_container.system_state = Mock()
        type(mock_container.system_state).status = property(
            lambda self: status_values[-1] if status_values else SystemStatus.INITIALIZING,
            lambda self, value: track_status(value)
        )
        type(mock_container.system_state).last_error = property(
            lambda self: last_error_value[0],
            lambda self, value: track_last_error(value)
        )

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with pytest.raises(Exception):
                    with TestClient(test_app):
                        pass

                # Verify error state was set during startup (before shutdown)
                assert SystemStatus.ERROR in status_values
                assert SystemStatus.SHUTTING_DOWN in status_values
                assert last_error_value[0] is not None

    @pytest.mark.asyncio
    async def test_shutdown_runs_even_on_startup_failure(self):
        """Test that shutdown cleanup runs even if startup failed."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = False  # Startup fails
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.close = AsyncMock()

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with pytest.raises(Exception):
                    with TestClient(test_app):
                        pass

                # Shutdown should still run
                mock_container.app_service.save_filesystem_to_disk.assert_called_once()
                mock_container.ollama_client.close.assert_called_once()
                mock_container.process_manager.stop.assert_called_once()


@pytest.mark.integration
class TestLifespanAppState:
    """Test that app.state is populated correctly."""

    @pytest.mark.asyncio
    async def test_app_state_services_populated(self):
        """Test that app.state.services is populated during startup."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        mock_container.system_state = Mock()
        mock_container.system_state.status = SystemStatus.INITIALIZING

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app) as client:
                    # App state should be populated
                    assert hasattr(test_app.state, 'services')
                    assert test_app.state.services == mock_container


@pytest.mark.integration
class TestLifespanIntegrationWithEndpoints:
    """Test that lifespan works correctly with actual endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_after_startup(self):
        """Test that health endpoint works after successful startup."""
        from datetime import datetime
        from recursive_neon.models.game_state import SystemState

        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        # Create a real SystemState instance for Pydantic validation
        mock_container.system_state = SystemState()
        mock_container.system_state.status = SystemStatus.READY
        mock_container.system_state.uptime_seconds = 0

        mock_container.start_time = datetime.now()

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        # Mock the global initialize_container to actually set the container
        def mock_initialize(container):
            import recursive_neon.dependencies as deps
            deps._container = container

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container', side_effect=mock_initialize):
                from fastapi import FastAPI
                from recursive_neon.main import health_check

                test_app = FastAPI(lifespan=lifespan)
                test_app.get("/health")(health_check)

                with TestClient(test_app) as client:
                    # Call health endpoint
                    response = client.get("/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"


@pytest.mark.integration
class TestLifespanSystemStatusTransitions:
    """Test system status transitions during lifespan."""

    @pytest.mark.asyncio
    async def test_status_transitions_on_success(self):
        """Test system status transitions through lifecycle on success."""
        mock_container = Mock(spec=ServiceContainer)

        mock_container.process_manager = AsyncMock()
        mock_container.process_manager.start.return_value = True
        mock_container.process_manager.stop = AsyncMock()

        mock_container.ollama_client = AsyncMock()
        mock_container.ollama_client.wait_for_ready.return_value = True
        mock_container.ollama_client.list_models.return_value = []
        mock_container.ollama_client.close = AsyncMock()

        mock_container.npc_manager = Mock()
        mock_container.npc_manager.create_default_npcs.return_value = []

        # Track status transitions
        status_history = []

        def track_status(value):
            status_history.append(value)

        mock_container.system_state = Mock()
        type(mock_container.system_state).status = property(
            lambda self: status_history[-1] if status_history else SystemStatus.INITIALIZING,
            lambda self, value: track_status(value)
        )

        mock_container.app_service = Mock()
        mock_container.app_service.save_filesystem_to_disk = Mock()

        mock_container.calendar_service = Mock()
        mock_container.calendar_service.save_to_disk = Mock()

        with patch.object(ServiceFactory, 'create_production_container', return_value=mock_container):
            with patch('recursive_neon.main.initialize_container'):
                from fastapi import FastAPI

                test_app = FastAPI(lifespan=lifespan)

                with TestClient(test_app):
                    pass

                # Should transition: READY -> SHUTTING_DOWN
                assert SystemStatus.READY in status_history
                assert SystemStatus.SHUTTING_DOWN in status_history
