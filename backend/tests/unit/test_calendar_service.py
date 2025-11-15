"""Unit tests for CalendarService."""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from recursive_neon.services.calendar_service import CalendarService
from recursive_neon.models.calendar import CalendarEvent, CreateEventRequest


class TestCalendarService:
    """Tests for CalendarService."""

    @pytest.fixture
    def calendar_service(self):
        """Create a CalendarService instance for testing."""
        return CalendarService()

    @pytest.fixture
    def sample_event_request(self):
        """Create a sample event request."""
        now = datetime.utcnow()
        return CreateEventRequest(
            title="Test Event",
            description="Test Description",
            start_time=now,
            end_time=now + timedelta(hours=1),
            location="Test Location",
            color="#FF5733",
            notes="Test Notes",
            all_day=False
        )

    def test_initialization(self, calendar_service):
        """Test service initialization."""
        assert calendar_service is not None
        assert calendar_service.events == {}

    def test_create_event(self, calendar_service, sample_event_request):
        """Test creating a calendar event."""
        event = calendar_service.create_event(sample_event_request)

        assert event is not None
        assert event.id is not None
        assert event.title == "Test Event"
        assert event.description == "Test Description"
        assert event.location == "Test Location"
        assert event.color == "#FF5733"
        assert event.notes == "Test Notes"
        assert event.all_day is False
        assert event.id in calendar_service.events

    def test_create_event_with_invalid_time_range(self, calendar_service):
        """Test creating event with end_time before start_time."""
        now = datetime.utcnow()

        with pytest.raises(ValueError, match="end_time must be after start_time"):
            CreateEventRequest(
                title="Bad Event",
                start_time=now,
                end_time=now - timedelta(hours=1)  # End before start
            )

    def test_create_all_day_event(self, calendar_service):
        """Test creating an all-day event."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        request = CreateEventRequest(
            title="All Day Event",
            start_time=today,
            end_time=tomorrow,
            all_day=True
        )

        event = calendar_service.create_event(request)
        assert event.all_day is True

    def test_get_event(self, calendar_service, sample_event_request):
        """Test getting a specific event by ID."""
        created = calendar_service.create_event(sample_event_request)
        retrieved = calendar_service.get_event(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_nonexistent_event(self, calendar_service):
        """Test getting an event that doesn't exist."""
        result = calendar_service.get_event("nonexistent-id")
        assert result is None

    def test_get_all_events(self, calendar_service):
        """Test getting all events."""
        # Initially empty
        assert calendar_service.get_all_events() == []

        # Create some events
        now = datetime.utcnow()
        for i in range(3):
            request = CreateEventRequest(
                title=f"Event {i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1)
            )
            calendar_service.create_event(request)

        # Get all events
        events = calendar_service.get_all_events()
        assert len(events) == 3

    def test_get_events_in_range(self, calendar_service):
        """Test getting events within a date range."""
        now = datetime.utcnow()

        # Create events at different times
        event1_req = CreateEventRequest(
            title="Event 1",
            start_time=now,
            end_time=now + timedelta(hours=1)
        )
        event2_req = CreateEventRequest(
            title="Event 2",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1)
        )
        event3_req = CreateEventRequest(
            title="Event 3",
            start_time=now + timedelta(days=7),
            end_time=now + timedelta(days=7, hours=1)
        )

        calendar_service.create_event(event1_req)
        calendar_service.create_event(event2_req)
        calendar_service.create_event(event3_req)

        # Query for events in the first 3 days
        range_start = now - timedelta(hours=1)
        range_end = now + timedelta(days=3)

        events = calendar_service.get_events_in_range(range_start, range_end)
        assert len(events) == 2  # Should get event 1 and 2, not 3

    def test_get_events_in_range_overlapping(self, calendar_service):
        """Test that overlapping events are included."""
        now = datetime.utcnow()

        # Create a long event
        request = CreateEventRequest(
            title="Long Event",
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=1)
        )
        calendar_service.create_event(request)

        # Query for a small window within the event
        range_start = now
        range_end = now + timedelta(hours=1)

        events = calendar_service.get_events_in_range(range_start, range_end)
        assert len(events) == 1

    def test_update_event(self, calendar_service, sample_event_request):
        """Test updating an existing event."""
        event = calendar_service.create_event(sample_event_request)

        updates = {
            "title": "Updated Title",
            "description": "Updated Description",
            "location": "Updated Location"
        }

        updated = calendar_service.update_event(event.id, updates)

        assert updated.title == "Updated Title"
        assert updated.description == "Updated Description"
        assert updated.location == "Updated Location"
        assert updated.updated_at > event.created_at

    def test_update_event_times(self, calendar_service, sample_event_request):
        """Test updating event times."""
        event = calendar_service.create_event(sample_event_request)

        new_start = datetime.utcnow() + timedelta(days=1)
        new_end = new_start + timedelta(hours=2)

        updates = {
            "start_time": new_start,
            "end_time": new_end
        }

        updated = calendar_service.update_event(event.id, updates)

        assert updated.start_time == new_start
        assert updated.end_time == new_end

    def test_update_event_with_invalid_times(self, calendar_service, sample_event_request):
        """Test updating with invalid time range."""
        event = calendar_service.create_event(sample_event_request)

        now = datetime.utcnow()
        updates = {
            "start_time": now,
            "end_time": now - timedelta(hours=1)  # End before start
        }

        with pytest.raises(ValueError, match="end_time must be after start_time"):
            calendar_service.update_event(event.id, updates)

    def test_update_nonexistent_event(self, calendar_service):
        """Test updating an event that doesn't exist."""
        with pytest.raises(ValueError, match="Event .* not found"):
            calendar_service.update_event("nonexistent-id", {"title": "New Title"})

    def test_delete_event(self, calendar_service, sample_event_request):
        """Test deleting an event."""
        event = calendar_service.create_event(sample_event_request)

        assert event.id in calendar_service.events

        success = calendar_service.delete_event(event.id)

        assert success is True
        assert event.id not in calendar_service.events

    def test_delete_nonexistent_event(self, calendar_service):
        """Test deleting an event that doesn't exist."""
        success = calendar_service.delete_event("nonexistent-id")
        assert success is False

    def test_save_to_disk(self, calendar_service, sample_event_request):
        """Test saving calendar data to disk."""
        # Create some events
        calendar_service.create_event(sample_event_request)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            calendar_service.save_to_disk(temp_path)

            # Verify file exists and has content
            assert Path(temp_path).exists()

            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert 'events' in data
            assert len(data['events']) == 1
            assert data['events'][0]['title'] == "Test Event"

        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_disk(self, calendar_service, sample_event_request):
        """Test loading calendar data from disk."""
        # Create and save some events
        event = calendar_service.create_event(sample_event_request)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            calendar_service.save_to_disk(temp_path)

            # Create new service and load from disk
            new_service = CalendarService()
            assert len(new_service.get_all_events()) == 0

            new_service.load_from_disk(temp_path)

            # Verify events were loaded
            events = new_service.get_all_events()
            assert len(events) == 1
            assert events[0].id == event.id
            assert events[0].title == event.title

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_nonexistent_file(self, calendar_service):
        """Test loading from a file that doesn't exist."""
        # Should not raise an exception
        calendar_service.load_from_disk("/path/that/does/not/exist.json")

        # Should still have no events
        assert len(calendar_service.get_all_events()) == 0

    def test_save_creates_directory(self, calendar_service, sample_event_request):
        """Test that save creates parent directories if they don't exist."""
        calendar_service.create_event(sample_event_request)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a nested path that doesn't exist
            temp_path = Path(temp_dir) / "nested" / "dir" / "calendar.json"

            calendar_service.save_to_disk(str(temp_path))

            assert temp_path.exists()
            assert temp_path.parent.exists()

    def test_event_color_validation(self, calendar_service):
        """Test that color field is validated."""
        now = datetime.utcnow()

        # Valid color
        valid_request = CreateEventRequest(
            title="Valid Color",
            start_time=now,
            end_time=now + timedelta(hours=1),
            color="#AABBCC"
        )
        event = calendar_service.create_event(valid_request)
        assert event.color == "#AABBCC"

        # Invalid color format
        with pytest.raises(ValueError):
            CreateEventRequest(
                title="Invalid Color",
                start_time=now,
                end_time=now + timedelta(hours=1),
                color="not-a-color"
            )

    def test_event_field_length_validation(self, calendar_service):
        """Test that field lengths are validated."""
        now = datetime.utcnow()

        # Title too long
        with pytest.raises(ValueError):
            CreateEventRequest(
                title="x" * 201,  # Max is 200
                start_time=now,
                end_time=now + timedelta(hours=1)
            )

        # Description too long
        with pytest.raises(ValueError):
            CreateEventRequest(
                title="Valid Title",
                description="x" * 2001,  # Max is 2000
                start_time=now,
                end_time=now + timedelta(hours=1)
            )

        # Notes too long
        with pytest.raises(ValueError):
            CreateEventRequest(
                title="Valid Title",
                notes="x" * 5001,  # Max is 5000
                start_time=now,
                end_time=now + timedelta(hours=1)
            )

    def test_concurrent_operations(self, calendar_service):
        """Test multiple operations in sequence."""
        now = datetime.utcnow()

        # Create multiple events
        events = []
        for i in range(5):
            request = CreateEventRequest(
                title=f"Event {i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1)
            )
            event = calendar_service.create_event(request)
            events.append(event)

        # Update some
        calendar_service.update_event(events[0].id, {"title": "Updated Event 0"})
        calendar_service.update_event(events[2].id, {"title": "Updated Event 2"})

        # Delete one
        calendar_service.delete_event(events[1].id)

        # Verify state
        all_events = calendar_service.get_all_events()
        assert len(all_events) == 4  # 5 created, 1 deleted

        # Verify updates
        event0 = calendar_service.get_event(events[0].id)
        assert event0.title == "Updated Event 0"

        event2 = calendar_service.get_event(events[2].id)
        assert event2.title == "Updated Event 2"

        # Verify deletion
        assert calendar_service.get_event(events[1].id) is None
