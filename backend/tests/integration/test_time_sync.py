"""
Integration tests for Time Synchronization

Tests the complete flow of time synchronization between backend and frontend
via WebSocket messages.
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

from recursive_neon.services.time_service import TimeService
from recursive_neon.services.message_handler import MessageHandler
from recursive_neon.services.settings_service import SettingsService
from recursive_neon.dependencies import ServiceContainer


class TestTimeWebSocketIntegration:
    """Test time synchronization via WebSocket messages."""

    @pytest.fixture
    def time_service(self):
        """Create a TimeService for testing."""
        return TimeService(persistence_path=None)

    @pytest.fixture
    def settings_service(self):
        """Create a SettingsService for testing."""
        return SettingsService(persistence_path=None)

    @pytest.fixture
    def message_handler(self, time_service, settings_service):
        """Create a MessageHandler with time and settings services."""
        # Create a minimal container with just the services we need
        container = Mock(spec=ServiceContainer)
        container.time_service = time_service
        container.settings_service = settings_service

        return MessageHandler(container)

    @pytest.mark.asyncio
    async def test_get_time_operation(self, message_handler, time_service):
        """Test getting current time via WebSocket."""
        # Set a known time
        target_time = datetime(2048, 11, 13, 8, 0, 0, tzinfo=timezone.utc)
        time_service.jump_to(target_time)

        # Send get_time message
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "get_time"}
        )

        assert response["status"] == "success"
        assert "data" in response

        # Verify time state
        state = response["data"]
        assert "current_time" in state
        assert "time_dilation" in state
        assert "is_paused" in state

        # Parse and verify time
        returned_time = datetime.fromisoformat(state["current_time"])
        assert returned_time.year == 2048
        assert returned_time.month == 11
        assert returned_time.day == 13

    @pytest.mark.asyncio
    async def test_set_dilation_operation(self, message_handler, time_service):
        """Test setting time dilation via WebSocket."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "set_dilation",
                "dilation": 5.0
            }
        )

        assert response["status"] == "success"
        assert time_service.get_time_dilation() == 5.0

    @pytest.mark.asyncio
    async def test_pause_operation(self, message_handler, time_service):
        """Test pausing time via WebSocket."""
        assert not time_service.is_paused()

        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "pause"}
        )

        assert response["status"] == "success"
        assert time_service.is_paused()

    @pytest.mark.asyncio
    async def test_resume_operation(self, message_handler, time_service):
        """Test resuming time via WebSocket."""
        time_service.pause()
        assert time_service.is_paused()

        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "resume"}
        )

        assert response["status"] == "success"
        assert not time_service.is_paused()

    @pytest.mark.asyncio
    async def test_jump_to_operation(self, message_handler, time_service):
        """Test jumping to specific time via WebSocket."""
        target_time = datetime(2050, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "jump_to",
                "datetime": target_time.isoformat()
            }
        )

        assert response["status"] == "success"

        current = time_service.get_current_time()
        assert current.year == 2050
        assert current.month == 1
        assert current.day == 1

    @pytest.mark.asyncio
    async def test_advance_operation(self, message_handler, time_service):
        """Test advancing time via WebSocket."""
        start = time_service.get_current_time()

        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "advance",
                "seconds": 3600  # 1 hour
            }
        )

        assert response["status"] == "success"

        end = time_service.get_current_time()
        elapsed = (end - start).total_seconds()

        # Should have advanced approximately 1 hour
        assert 3599 < elapsed < 3601

    @pytest.mark.asyncio
    async def test_rewind_operation(self, message_handler, time_service):
        """Test rewinding time via WebSocket."""
        start = time_service.get_current_time()

        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "rewind",
                "seconds": 7200  # 2 hours
            }
        )

        assert response["status"] == "success"

        end = time_service.get_current_time()
        elapsed = (start - end).total_seconds()

        # Should have rewound approximately 2 hours
        assert 7199 < elapsed < 7201

    @pytest.mark.asyncio
    async def test_invalid_operation(self, message_handler):
        """Test invalid operation returns error."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "invalid_op"}
        )

        assert response["status"] == "error"
        assert "error" in response

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, message_handler):
        """Test missing required parameter returns error."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "set_dilation"
                # Missing "dilation" parameter
            }
        )

        assert response["status"] == "error"
        assert "error" in response

    @pytest.mark.asyncio
    async def test_sequential_operations(self, message_handler, time_service):
        """Test multiple sequential time operations."""
        # Set dilation
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "set_dilation", "dilation": 2.0}
        )
        assert time_service.get_time_dilation() == 2.0

        # Pause
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "pause"}
        )
        assert time_service.is_paused()

        # Resume
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "resume"}
        )
        assert not time_service.is_paused()
        assert time_service.get_time_dilation() == 2.0

        # Jump to future
        target = datetime(2049, 6, 15, tzinfo=timezone.utc)
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "jump_to", "datetime": target.isoformat()}
        )

        current = time_service.get_current_time()
        assert current.year == 2049


class TestSettingsWebSocketIntegration:
    """Test settings synchronization via WebSocket messages."""

    @pytest.fixture
    def settings_service(self):
        """Create a SettingsService for testing."""
        return SettingsService(persistence_path=None)

    @pytest.fixture
    def message_handler(self, settings_service):
        """Create a MessageHandler with settings service."""
        container = Mock(spec=ServiceContainer)
        container.settings_service = settings_service

        return MessageHandler(container)

    @pytest.mark.asyncio
    async def test_get_all_settings(self, message_handler):
        """Test getting all settings via WebSocket."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={"operation": "get_all"}
        )

        assert response["status"] == "success"
        assert "data" in response

        settings = response["data"]
        assert "clock.mode" in settings
        assert "theme.current" in settings

    @pytest.mark.asyncio
    async def test_get_single_setting(self, message_handler):
        """Test getting a single setting via WebSocket."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "get",
                "key": "clock.mode"
            }
        )

        assert response["status"] == "success"
        assert response["data"]["value"] == "digital"

    @pytest.mark.asyncio
    async def test_set_setting(self, message_handler, settings_service):
        """Test setting a value via WebSocket."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "clock.mode",
                "value": "analog"
            }
        )

        assert response["status"] == "success"
        assert settings_service.get("clock.mode") == "analog"

    @pytest.mark.asyncio
    async def test_set_many_settings(self, message_handler, settings_service):
        """Test setting multiple values via WebSocket."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set_many",
                "settings": {
                    "clock.mode": "analog",
                    "clock.showSeconds": False,
                    "theme.current": "dark"
                }
            }
        )

        assert response["status"] == "success"
        assert settings_service.get("clock.mode") == "analog"
        assert settings_service.get("clock.showSeconds") is False
        assert settings_service.get("theme.current") == "dark"

    @pytest.mark.asyncio
    async def test_reset_setting(self, message_handler, settings_service):
        """Test resetting a setting to default via WebSocket."""
        # Change from default
        settings_service.set("clock.mode", "analog")
        assert settings_service.get("clock.mode") == "analog"

        # Reset
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "reset",
                "key": "clock.mode"
            }
        )

        assert response["status"] == "success"
        assert settings_service.get("clock.mode") == "digital"

    @pytest.mark.asyncio
    async def test_reset_all_settings(self, message_handler, settings_service):
        """Test resetting all settings to defaults via WebSocket."""
        # Change multiple settings
        settings_service.set("clock.mode", "analog")
        settings_service.set("theme.current", "dark")

        # Reset all
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={"operation": "reset_all"}
        )

        assert response["status"] == "success"
        assert settings_service.get("clock.mode") == "digital"
        assert settings_service.get("theme.current") == "classic"

    @pytest.mark.asyncio
    async def test_validation_error(self, message_handler):
        """Test setting invalid value returns error."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "clock.mode",
                "value": "invalid_mode"
            }
        )

        assert response["status"] == "error"
        assert "error" in response


class TestTimeSettingsIntegration:
    """Test integration between time and settings systems."""

    @pytest.fixture
    def time_service(self):
        """Create a TimeService for testing."""
        return TimeService(persistence_path=None)

    @pytest.fixture
    def settings_service(self):
        """Create a SettingsService for testing."""
        return SettingsService(persistence_path=None)

    @pytest.fixture
    def message_handler(self, time_service, settings_service):
        """Create a MessageHandler with both services."""
        container = Mock(spec=ServiceContainer)
        container.time_service = time_service
        container.settings_service = settings_service

        return MessageHandler(container)

    @pytest.mark.asyncio
    async def test_clock_settings_affect_display(
        self,
        message_handler,
        settings_service
    ):
        """Test that clock settings changes work correctly."""
        # Change clock mode
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "clock.mode",
                "value": "analog"
            }
        )
        assert response["status"] == "success"
        assert settings_service.get("clock.mode") == "analog"

        # Change position
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "clock.position",
                "value": "bottom-left"
            }
        )
        assert response["status"] == "success"
        assert settings_service.get("clock.position") == "bottom-left"

        # Verify time service still works independently
        time_state_response = await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "get_time"}
        )
        assert time_state_response["status"] == "success"

    @pytest.mark.asyncio
    async def test_theme_change_and_time_query(
        self,
        message_handler,
        time_service,
        settings_service
    ):
        """Test that theme changes don't affect time operations."""
        # Change theme
        await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "theme.current",
                "value": "neon"
            }
        )
        assert settings_service.get("theme.current") == "neon"

        # Jump to a specific time
        target_time = datetime(2049, 12, 25, 12, 0, 0, tzinfo=timezone.utc)
        await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "jump_to",
                "datetime": target_time.isoformat()
            }
        )

        # Verify time was set correctly
        current = time_service.get_current_time()
        assert current.year == 2049
        assert current.month == 12
        assert current.day == 25

        # Verify theme is still set
        assert settings_service.get("theme.current") == "neon"

    @pytest.mark.asyncio
    async def test_concurrent_time_and_settings_operations(
        self,
        message_handler,
        time_service,
        settings_service
    ):
        """Test multiple interleaved time and settings operations."""
        # Set time dilation
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "set_dilation", "dilation": 3.0}
        )

        # Change theme
        await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "theme.current",
                "value": "cyberpunk"
            }
        )

        # Jump time
        target = datetime(2050, 1, 1, tzinfo=timezone.utc)
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "jump_to", "datetime": target.isoformat()}
        )

        # Change clock mode
        await message_handler.handle_message(
            msg_type="settings",
            msg_data={
                "operation": "set",
                "key": "clock.mode",
                "value": "off"
            }
        )

        # Pause time
        await message_handler.handle_message(
            msg_type="time",
            msg_data={"operation": "pause"}
        )

        # Verify all states are correct
        assert time_service.is_paused()
        assert time_service.get_time_dilation() == 0.0  # Paused
        assert time_service.get_current_time().year == 2050
        assert settings_service.get("theme.current") == "cyberpunk"
        assert settings_service.get("clock.mode") == "off"


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @pytest.fixture
    def message_handler(self):
        """Create a MessageHandler with mock services."""
        container = Mock(spec=ServiceContainer)
        container.time_service = TimeService(persistence_path=None)
        container.settings_service = SettingsService(persistence_path=None)

        return MessageHandler(container)

    @pytest.mark.asyncio
    async def test_malformed_time_message(self, message_handler):
        """Test handling of malformed time message."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={}  # Missing operation
        )

        assert response["status"] == "error"

    @pytest.mark.asyncio
    async def test_malformed_settings_message(self, message_handler):
        """Test handling of malformed settings message."""
        response = await message_handler.handle_message(
            msg_type="settings",
            msg_data={"operation": "set"}  # Missing key and value
        )

        assert response["status"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_datetime_format(self, message_handler):
        """Test handling of invalid datetime format."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "jump_to",
                "datetime": "not-a-valid-datetime"
            }
        )

        assert response["status"] == "error"
        assert "error" in response

    @pytest.mark.asyncio
    async def test_negative_time_dilation(self, message_handler):
        """Test handling of negative time dilation."""
        response = await message_handler.handle_message(
            msg_type="time",
            msg_data={
                "operation": "set_dilation",
                "dilation": -1.0
            }
        )

        assert response["status"] == "error"
        assert "error" in response
