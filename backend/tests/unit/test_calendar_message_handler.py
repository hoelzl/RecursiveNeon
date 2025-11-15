"""Unit tests for calendar message handling."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from recursive_neon.services.message_handler import MessageHandler
from recursive_neon.services.calendar_service import CalendarService
from recursive_neon.models.calendar import CalendarEvent, CreateEventRequest


class TestCalendarMessageHandler:
    """Tests for calendar message handling in MessageHandler."""

    @pytest.fixture
    def mock_npc_manager(self):
        """Create a mock NPC manager."""
        return Mock()

    @pytest.fixture
    def calendar_service(self):
        """Create a real calendar service for testing."""
        return CalendarService()

    @pytest.fixture
    def message_handler(self, mock_npc_manager, calendar_service):
        """Create a message handler with calendar service."""
        return MessageHandler(
            npc_manager=mock_npc_manager,
            calendar_service=calendar_service
        )

    @pytest.fixture
    def sample_event_data(self):
        """Create sample event data for testing."""
        now = datetime.utcnow()
        return {
            "title": "Test Event",
            "description": "Test Description",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "location": "Test Location",
            "color": "#FF5733",
            "notes": "Test Notes",
            "all_day": False
        }

    @pytest.mark.asyncio
    async def test_get_events_empty(self, message_handler):
        """Test getting events when calendar is empty."""
        response = await message_handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )

        assert response["type"] == "calendar_events_list"
        assert response["data"]["events"] == []

    @pytest.mark.asyncio
    async def test_create_event(self, message_handler, sample_event_data):
        """Test creating an event via message handler."""
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )

        assert response["type"] == "calendar_event_created"
        assert "event" in response["data"]

        event = response["data"]["event"]
        assert event["title"] == "Test Event"
        assert event["description"] == "Test Description"
        assert event["location"] == "Test Location"
        assert event["id"] is not None

    @pytest.mark.asyncio
    async def test_get_events_after_create(self, message_handler, sample_event_data):
        """Test getting events after creating some."""
        # Create an event
        create_response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )
        event_id = create_response["data"]["event"]["id"]

        # Get all events
        get_response = await message_handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )

        assert get_response["type"] == "calendar_events_list"
        assert len(get_response["data"]["events"]) == 1
        assert get_response["data"]["events"][0]["id"] == event_id

    @pytest.mark.asyncio
    async def test_get_events_in_range(self, message_handler, sample_event_data):
        """Test getting events in a specific date range."""
        # Create event
        await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )

        # Query for events in range
        now = datetime.utcnow()
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "get_events_range",
                "start_date": (now - timedelta(hours=1)).isoformat(),
                "end_date": (now + timedelta(hours=2)).isoformat()
            }
        )

        assert response["type"] == "calendar_events_list"
        assert len(response["data"]["events"]) == 1

    @pytest.mark.asyncio
    async def test_get_events_out_of_range(self, message_handler, sample_event_data):
        """Test getting events outside the date range."""
        # Create event
        await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )

        # Query for events in a different range
        future = datetime.utcnow() + timedelta(days=30)
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "get_events_range",
                "start_date": future.isoformat(),
                "end_date": (future + timedelta(hours=1)).isoformat()
            }
        )

        assert response["type"] == "calendar_events_list"
        assert len(response["data"]["events"]) == 0

    @pytest.mark.asyncio
    async def test_update_event(self, message_handler, sample_event_data):
        """Test updating an event."""
        # Create event
        create_response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )
        event_id = create_response["data"]["event"]["id"]

        # Update event
        update_response = await message_handler.handle_message(
            "calendar",
            {
                "action": "update_event",
                "event_id": event_id,
                "updates": {
                    "title": "Updated Title",
                    "description": "Updated Description"
                }
            }
        )

        assert update_response["type"] == "calendar_event_updated"
        updated_event = update_response["data"]["event"]
        assert updated_event["id"] == event_id
        assert updated_event["title"] == "Updated Title"
        assert updated_event["description"] == "Updated Description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_event(self, message_handler):
        """Test updating an event that doesn't exist."""
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "update_event",
                "event_id": "nonexistent-id",
                "updates": {"title": "New Title"}
            }
        )

        assert response["type"] == "error"
        assert "not found" in response["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_event(self, message_handler, sample_event_data):
        """Test deleting an event."""
        # Create event
        create_response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )
        event_id = create_response["data"]["event"]["id"]

        # Delete event
        delete_response = await message_handler.handle_message(
            "calendar",
            {
                "action": "delete_event",
                "event_id": event_id
            }
        )

        assert delete_response["type"] == "calendar_event_deleted"
        assert delete_response["data"]["event_id"] == event_id
        assert delete_response["data"]["success"] is True

        # Verify deletion
        get_response = await message_handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )
        assert len(get_response["data"]["events"]) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_event(self, message_handler):
        """Test deleting an event that doesn't exist."""
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "delete_event",
                "event_id": "nonexistent-id"
            }
        )

        assert response["type"] == "calendar_event_deleted"
        assert response["data"]["success"] is False

    @pytest.mark.asyncio
    async def test_unknown_calendar_action(self, message_handler):
        """Test handling unknown calendar action."""
        response = await message_handler.handle_message(
            "calendar",
            {"action": "unknown_action"}
        )

        assert response["type"] == "error"
        assert "Unknown calendar action" in response["data"]["message"]

    @pytest.mark.asyncio
    async def test_calendar_service_not_available(self, mock_npc_manager):
        """Test calendar operations when service is not available."""
        # Create handler without calendar service
        handler = MessageHandler(npc_manager=mock_npc_manager)

        response = await handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )

        assert response["type"] == "error"
        assert "Calendar service not available" in response["data"]["message"]

    @pytest.mark.asyncio
    async def test_create_event_with_invalid_data(self, message_handler):
        """Test creating event with invalid data."""
        now = datetime.utcnow()

        # Missing required field (title)
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": {
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=1)).isoformat()
                }
            }
        )

        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_create_event_with_invalid_time_range(self, message_handler):
        """Test creating event with end_time before start_time."""
        now = datetime.utcnow()

        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": {
                    "title": "Invalid Event",
                    "start_time": now.isoformat(),
                    "end_time": (now - timedelta(hours=1)).isoformat()
                }
            }
        )

        assert response["type"] == "error"
        assert "end_time must be after start_time" in response["data"]["message"]

    @pytest.mark.asyncio
    async def test_multiple_events_workflow(self, message_handler, sample_event_data):
        """Test a complete workflow with multiple events."""
        # Create three events
        event_ids = []
        for i in range(3):
            event_data = sample_event_data.copy()
            event_data["title"] = f"Event {i}"
            response = await message_handler.handle_message(
                "calendar",
                {
                    "action": "create_event",
                    "event": event_data
                }
            )
            event_ids.append(response["data"]["event"]["id"])

        # Verify all created
        get_response = await message_handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )
        assert len(get_response["data"]["events"]) == 3

        # Update one
        await message_handler.handle_message(
            "calendar",
            {
                "action": "update_event",
                "event_id": event_ids[1],
                "updates": {"title": "Updated Event 1"}
            }
        )

        # Delete one
        await message_handler.handle_message(
            "calendar",
            {
                "action": "delete_event",
                "event_id": event_ids[0]
            }
        )

        # Verify final state
        final_response = await message_handler.handle_message(
            "calendar",
            {"action": "get_events"}
        )
        events = final_response["data"]["events"]
        assert len(events) == 2

        # Find updated event
        updated_event = next(e for e in events if e["id"] == event_ids[1])
        assert updated_event["title"] == "Updated Event 1"

    @pytest.mark.asyncio
    async def test_event_persistence_format(self, message_handler, sample_event_data):
        """Test that events are properly formatted in responses."""
        response = await message_handler.handle_message(
            "calendar",
            {
                "action": "create_event",
                "event": sample_event_data
            }
        )

        event = response["data"]["event"]

        # Verify all expected fields are present
        assert "id" in event
        assert "title" in event
        assert "description" in event
        assert "start_time" in event
        assert "end_time" in event
        assert "location" in event
        assert "color" in event
        assert "notes" in event
        assert "all_day" in event
        assert "created_at" in event
        assert "updated_at" in event

        # Verify datetime fields are strings (ISO format)
        assert isinstance(event["start_time"], str)
        assert isinstance(event["end_time"], str)
        assert isinstance(event["created_at"], str)
        assert isinstance(event["updated_at"], str)
