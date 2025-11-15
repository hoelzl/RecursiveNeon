"""Calendar service for managing calendar events."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from recursive_neon.models.calendar import CalendarEvent, CreateEventRequest
from recursive_neon.services.interfaces import ICalendarService

logger = logging.getLogger(__name__)


class CalendarService(ICalendarService):
    """Manages calendar events for the game."""

    def __init__(self):
        """Initialize calendar service."""
        self.events: Dict[str, CalendarEvent] = {}
        logger.info("CalendarService initialized")

    def create_event(self, event_data: CreateEventRequest) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            event_data: Event data to create

        Returns:
            The created CalendarEvent
        """
        event = CalendarEvent(**event_data.model_dump())
        self.events[event.id] = event
        logger.info(f"Created calendar event: {event.id} - {event.title}")
        return event

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """
        Get a specific event by ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            The event if found, None otherwise
        """
        return self.events.get(event_id)

    def get_all_events(self) -> List[CalendarEvent]:
        """
        Get all calendar events.

        Returns:
            List of all events
        """
        return list(self.events.values())

    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CalendarEvent]:
        """
        Get events within a date range.

        Events are included if they overlap with the range at all.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of events in range
        """
        return [
            event for event in self.events.values()
            if (event.start_time <= end_date and event.end_time >= start_date)
        ]

    def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> CalendarEvent:
        """
        Update an existing event.

        Args:
            event_id: ID of event to update
            updates: Dictionary of fields to update

        Returns:
            The updated event

        Raises:
            ValueError: If event not found
        """
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Filter out None values
        update_data = {k: v for k, v in updates.items() if v is not None}

        # Convert ISO strings to datetime objects for validation
        start_time = update_data.get('start_time', event.start_time)
        end_time = update_data.get('end_time', event.end_time)

        # Ensure both are datetime objects for comparison
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

        # Validate that end_time is after start_time
        if end_time <= start_time:
            raise ValueError('end_time must be after start_time')

        # Always update the updated_at timestamp
        update_data['updated_at'] = datetime.utcnow()

        # Create updated event
        updated_event = event.model_copy(update=update_data)
        self.events[event_id] = updated_event

        logger.info(f"Updated calendar event: {event_id}")
        return updated_event

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event.

        Args:
            event_id: ID of event to delete

        Returns:
            True if deleted, False if not found
        """
        if event_id in self.events:
            del self.events[event_id]
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        return False

    def save_to_disk(self, file_path: str) -> None:
        """
        Save calendar events to disk.

        Args:
            file_path: Path to save calendar data
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "events": [event.model_dump(mode='json') for event in self.events.values()]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved {len(self.events)} events to {file_path}")

    def load_from_disk(self, file_path: str) -> None:
        """
        Load calendar events from disk.

        Args:
            file_path: Path to load calendar data from
        """
        path = Path(file_path)
        if not path.exists():
            logger.info(f"No calendar data found at {file_path}")
            return

        with open(path, 'r') as f:
            data = json.load(f)

        self.events = {}
        for event_data in data.get('events', []):
            event = CalendarEvent(**event_data)
            self.events[event.id] = event

        logger.info(f"Loaded {len(self.events)} events from {file_path}")
