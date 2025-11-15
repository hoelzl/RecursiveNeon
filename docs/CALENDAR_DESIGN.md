# Calendar App Design Document

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon Calendar App

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Design](#backend-design)
3. [Frontend Design](#frontend-design)
4. [Data Flow](#data-flow)
5. [Component Specifications](#component-specifications)
6. [State Management](#state-management)
7. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

The Calendar App follows the RecursiveNeon architectural patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CalendarApp  │  │  EventModal  │  │  ViewModes   │      │
│  │  Component   │  │   Component  │  │  Components  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┼──────────────────┘               │
│                           │                                  │
│                    ┌──────▼───────┐                          │
│                    │  Game Store  │                          │
│                    │  (Zustand)   │                          │
│                    └──────┬───────┘                          │
│                           │                                  │
│                    ┌──────▼───────┐                          │
│                    │  WebSocket   │                          │
│                    │    Client    │                          │
└────────────────────┴──────┬───────┴──────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │   WebSocket    │
                    │   Connection   │
                    └───────┬────────┘
┌────────────────────────────▼──────────────────────────────────┐
│                     Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Message    │  │   Calendar   │  │    REST      │        │
│  │   Handler    │  │   Service    │  │    Routes    │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                  │                 │
│         └─────────────────┼──────────────────┘                 │
│                           │                                    │
│                    ┌──────▼───────┐                            │
│                    │  Calendar    │                            │
│                    │   Events     │                            │
│                    │  (In-Memory) │                            │
│                    └──────┬───────┘                            │
│                           │                                    │
│                    ┌──────▼───────┐                            │
│                    │ Persistence  │                            │
│                    │ (JSON File)  │                            │
│                    └──────────────┘                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Backend Design

### Models

#### CalendarEvent (Pydantic)

```python
# backend/src/recursive_neon/models/calendar.py

from datetime import datetime
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, validator

class CalendarEvent(BaseModel):
    """Represents a calendar event in the game."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateEventRequest(BaseModel):
    """Request model for creating a calendar event."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: bool = False


class UpdateEventRequest(BaseModel):
    """Request model for updating a calendar event."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: Optional[bool] = None
```

### Service Interface

```python
# backend/src/recursive_neon/services/interfaces.py

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from recursive_neon.models.calendar import CalendarEvent, CreateEventRequest

class ICalendarService(ABC):
    """Interface for calendar event management."""

    @abstractmethod
    def create_event(self, event_data: CreateEventRequest) -> CalendarEvent:
        """Create a new calendar event."""
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get a specific event by ID."""
        pass

    @abstractmethod
    def get_all_events(self) -> List[CalendarEvent]:
        """Get all calendar events."""
        pass

    @abstractmethod
    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events within a date range."""
        pass

    @abstractmethod
    def update_event(
        self,
        event_id: str,
        updates: dict
    ) -> CalendarEvent:
        """Update an existing event."""
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        pass

    @abstractmethod
    def save_to_disk(self, file_path: str) -> None:
        """Save calendar events to disk."""
        pass

    @abstractmethod
    def load_from_disk(self, file_path: str) -> None:
        """Load calendar events from disk."""
        pass
```

### Service Implementation

```python
# backend/src/recursive_neon/services/calendar_service.py

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from recursive_neon.models.calendar import (
    CalendarEvent,
    CreateEventRequest,
)
from recursive_neon.services.interfaces import ICalendarService

logger = logging.getLogger(__name__)


class CalendarService(ICalendarService):
    """Manages calendar events for the game."""

    def __init__(self):
        """Initialize calendar service."""
        self.events: Dict[str, CalendarEvent] = {}

    def create_event(self, event_data: CreateEventRequest) -> CalendarEvent:
        """Create a new calendar event."""
        event = CalendarEvent(**event_data.dict())
        self.events[event.id] = event
        logger.info(f"Created calendar event: {event.id} - {event.title}")
        return event

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get a specific event by ID."""
        return self.events.get(event_id)

    def get_all_events(self) -> List[CalendarEvent]:
        """Get all calendar events."""
        return list(self.events.values())

    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events within a date range."""
        return [
            event for event in self.events.values()
            if (event.start_time <= end_date and event.end_time >= start_date)
        ]

    def update_event(self, event_id: str, updates: dict) -> CalendarEvent:
        """Update an existing event."""
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Update fields
        update_data = {k: v for k, v in updates.items() if v is not None}
        update_data['updated_at'] = datetime.utcnow()

        updated_event = event.copy(update=update_data)
        self.events[event_id] = updated_event

        logger.info(f"Updated calendar event: {event_id}")
        return updated_event

    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        if event_id in self.events:
            del self.events[event_id]
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        return False

    def save_to_disk(self, file_path: str) -> None:
        """Save calendar events to disk."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "events": [event.dict() for event in self.events.values()]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved {len(self.events)} events to {file_path}")

    def load_from_disk(self, file_path: str) -> None:
        """Load calendar events from disk."""
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
```

### Message Handler Updates

Add calendar message handling to `MessageHandler`:

```python
# In services/message_handler.py

async def _handle_calendar_message(self, data: dict) -> Dict[str, Any]:
    """Handle calendar-related messages."""
    action = data.get('action')

    if action == 'get_events':
        events = self.calendar_service.get_all_events()
        return {
            'type': 'calendar_events_list',
            'data': {'events': [e.dict() for e in events]}
        }

    elif action == 'get_events_range':
        start = datetime.fromisoformat(data['start_date'])
        end = datetime.fromisoformat(data['end_date'])
        events = self.calendar_service.get_events_in_range(start, end)
        return {
            'type': 'calendar_events_list',
            'data': {'events': [e.dict() for e in events]}
        }

    elif action == 'create_event':
        request = CreateEventRequest(**data['event'])
        event = self.calendar_service.create_event(request)
        return {
            'type': 'calendar_event_created',
            'data': {'event': event.dict()}
        }

    elif action == 'update_event':
        event = self.calendar_service.update_event(
            data['event_id'],
            data['updates']
        )
        return {
            'type': 'calendar_event_updated',
            'data': {'event': event.dict()}
        }

    elif action == 'delete_event':
        success = self.calendar_service.delete_event(data['event_id'])
        return {
            'type': 'calendar_event_deleted',
            'data': {'event_id': data['event_id'], 'success': success}
        }
```

---

## Frontend Design

### TypeScript Types

```typescript
// frontend/src/types/calendar.ts

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;  // ISO 8601
  end_time: string;    // ISO 8601
  location?: string;
  color?: string;      // Hex color
  notes?: string;
  all_day: boolean;
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
}

export interface CreateEventData {
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  location?: string;
  color?: string;
  notes?: string;
  all_day?: boolean;
}

export type CalendarView = 'month' | 'week' | 'day' | 'list';

export interface CalendarState {
  events: CalendarEvent[];
  selectedDate: Date;
  currentView: CalendarView;
  selectedEvent: CalendarEvent | null;
}
```

### Component Structure

```
CalendarApp/
├── CalendarApp.tsx              # Main component
├── components/
│   ├── CalendarHeader.tsx       # Navigation and view switcher
│   ├── MonthView.tsx            # Month grid view
│   ├── WeekView.tsx             # Week timeline view
│   ├── DayView.tsx              # Day timeline view
│   ├── ListView.tsx             # List of events
│   ├── EventModal.tsx           # Create/edit event dialog
│   ├── EventCard.tsx            # Event display component
│   └── TimeGrid.tsx             # Reusable time grid component
└── utils/
    ├── dateUtils.ts             # Date manipulation utilities
    └── calendarApi.ts           # Backend API client
```

### Main Component Design

```typescript
// frontend/src/components/apps/CalendarApp.tsx

import { useState, useEffect, useCallback } from 'react';
import { CalendarEvent, CalendarView } from '../../types/calendar';
import { useGameStore } from '../../stores/gameStore';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { CalendarHeader } from './calendar/CalendarHeader';
import { MonthView } from './calendar/MonthView';
import { WeekView } from './calendar/WeekView';
import { DayView } from './calendar/DayView';
import { ListView } from './calendar/ListView';
import { EventModal } from './calendar/EventModal';

export function CalendarApp() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [currentView, setCurrentView] = useState<CalendarView>('month');
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);

  const wsClient = useWebSocket();

  // Load events on mount
  useEffect(() => {
    wsClient.sendMessage({
      type: 'calendar',
      data: { action: 'get_events' }
    });
  }, [wsClient]);

  // Listen for calendar updates
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'calendar_events_list':
          setEvents(message.data.events);
          break;

        case 'calendar_event_created':
          setEvents(prev => [...prev, message.data.event]);
          break;

        case 'calendar_event_updated':
          setEvents(prev => prev.map(e =>
            e.id === message.data.event.id ? message.data.event : e
          ));
          break;

        case 'calendar_event_deleted':
          setEvents(prev => prev.filter(e => e.id !== message.data.event_id));
          break;
      }
    };

    wsClient.addEventListener('message', handleMessage);
    return () => wsClient.removeEventListener('message', handleMessage);
  }, [wsClient]);

  const handleCreateEvent = useCallback((eventData: CreateEventData) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'create_event',
        event: eventData
      }
    });
    setIsModalOpen(false);
  }, [wsClient]);

  const handleUpdateEvent = useCallback((eventId: string, updates: Partial<CalendarEvent>) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'update_event',
        event_id: eventId,
        updates
      }
    });
    setIsModalOpen(false);
    setEditingEvent(null);
  }, [wsClient]);

  const handleDeleteEvent = useCallback((eventId: string) => {
    wsClient.sendMessage({
      type: 'calendar',
      data: {
        action: 'delete_event',
        event_id: eventId
      }
    });
    setIsModalOpen(false);
    setEditingEvent(null);
  }, [wsClient]);

  const renderView = () => {
    switch (currentView) {
      case 'month':
        return (
          <MonthView
            events={events}
            selectedDate={selectedDate}
            onDateClick={setSelectedDate}
            onEventClick={setSelectedEvent}
            onCreateEvent={(date) => {
              setEditingEvent(null);
              setIsModalOpen(true);
            }}
          />
        );

      case 'week':
        return (
          <WeekView
            events={events}
            selectedDate={selectedDate}
            onEventClick={setSelectedEvent}
            onTimeSlotClick={(date) => {
              setEditingEvent(null);
              setIsModalOpen(true);
            }}
          />
        );

      case 'day':
        return (
          <DayView
            events={events}
            selectedDate={selectedDate}
            onEventClick={setSelectedEvent}
            onTimeSlotClick={(time) => {
              setEditingEvent(null);
              setIsModalOpen(true);
            }}
          />
        );

      case 'list':
        return (
          <ListView
            events={events}
            onEventClick={setSelectedEvent}
          />
        );
    }
  };

  return (
    <div className="calendar-app">
      <CalendarHeader
        currentView={currentView}
        selectedDate={selectedDate}
        onViewChange={setCurrentView}
        onDateChange={setSelectedDate}
        onCreateEvent={() => setIsModalOpen(true)}
      />

      <div className="calendar-view">
        {renderView()}
      </div>

      {isModalOpen && (
        <EventModal
          event={editingEvent}
          onSave={editingEvent ? handleUpdateEvent : handleCreateEvent}
          onDelete={editingEvent ? handleDeleteEvent : undefined}
          onClose={() => {
            setIsModalOpen(false);
            setEditingEvent(null);
          }}
        />
      )}
    </div>
  );
}
```

---

## Data Flow

### Event Creation Flow

```
User clicks "+" button
  ↓
EventModal opens with empty form
  ↓
User fills in event details
  ↓
User clicks "Save"
  ↓
Frontend validates input
  ↓
WebSocket sends create_event message
  ↓
Backend validates and creates CalendarEvent
  ↓
Backend saves to disk
  ↓
Backend sends calendar_event_created message
  ↓
Frontend updates events state
  ↓
Calendar view re-renders with new event
```

### Backend Push Flow

```
NPC or system creates event
  ↓
Calls calendar_service.create_event()
  ↓
Event stored in memory
  ↓
Saved to disk
  ↓
WebSocket broadcasts calendar_event_created
  ↓
All connected clients receive update
  ↓
Frontends update their event lists
```

---

## State Management

### Game Store Extensions

```typescript
// In frontend/src/stores/gameStore.ts

interface IGameStore {
  // Existing state...

  // Calendar state
  calendarEvents: CalendarEvent[];
  setCalendarEvents: (events: CalendarEvent[]) => void;
  addCalendarEvent: (event: CalendarEvent) => void;
  updateCalendarEvent: (eventId: string, updates: Partial<CalendarEvent>) => void;
  removeCalendarEvent: (eventId: string) => void;
}

// Implementation
setCalendarEvents: (events) => set({ calendarEvents: events }),

addCalendarEvent: (event) => set((state) => ({
  calendarEvents: [...state.calendarEvents, event]
})),

updateCalendarEvent: (eventId, updates) => set((state) => ({
  calendarEvents: state.calendarEvents.map(e =>
    e.id === eventId ? { ...e, ...updates } : e
  )
})),

removeCalendarEvent: (eventId) => set((state) => ({
  calendarEvents: state.calendarEvents.filter(e => e.id !== eventId)
})),
```

---

## Testing Strategy

### Backend Tests

**Unit Tests** (`backend/tests/unit/test_calendar_service.py`):
- Event creation with valid/invalid data
- Event updates
- Event deletion
- Date range filtering
- Persistence (save/load)

**Integration Tests** (`backend/tests/integration/test_calendar_websocket.py`):
- WebSocket message handling
- Concurrent event modifications
- Error handling

### Frontend Tests

**Component Tests**:
- CalendarApp renders correctly
- MonthView displays events
- WeekView time slots
- EventModal form validation
- Event CRUD operations

**Integration Tests**:
- WebSocket communication
- State updates on event changes
- View switching

---

## Implementation Notes

1. **Date Handling**:
   - Use ISO 8601 format for all date/time strings
   - Use JavaScript `Date` objects in frontend, convert to ISO strings for API
   - Backend uses Python `datetime`, serializes to ISO strings

2. **Color Handling**:
   - Validate hex colors on backend
   - Provide color picker in frontend
   - Default colors for events without explicit color

3. **Performance**:
   - Filter events by date range before rendering
   - Use React.memo for event cards
   - Debounce date navigation

4. **Error Handling**:
   - Validate all inputs
   - Show user-friendly error messages
   - Log errors for debugging

5. **Accessibility**:
   - Keyboard navigation in calendar grids
   - ARIA labels for screen readers
   - Focus management in modals

---

**Document Status**: Approved for Implementation
**Last Updated**: 2025-11-15
