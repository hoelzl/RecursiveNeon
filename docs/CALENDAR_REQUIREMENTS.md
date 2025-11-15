# Calendar App Requirements

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon Calendar App

---

## Overview

The Calendar App is an in-game desktop application that allows players to manage events, appointments, and schedules within the game world. The backend serves as the source of truth for all calendar data, with the frontend providing multiple view modes and editing capabilities.

---

## Functional Requirements

### FR1: Event Management

#### FR1.1: Create Event
- **Description**: Players can create new calendar events
- **Fields**:
  - `title` (required): Event name/summary (max 200 characters)
  - `description` (optional): Detailed event description (max 2000 characters)
  - `start_time` (required): Event start date and time (ISO 8601 format)
  - `end_time` (required): Event end date and time (ISO 8601 format)
  - `location` (optional): Event location (max 200 characters)
  - `color` (optional): Event color tag for visual organization (hex color)
  - `notes` (optional): Additional notes (max 5000 characters)
  - `all_day` (optional): Boolean flag for all-day events
- **Validation**:
  - end_time must be after start_time
  - title cannot be empty
  - times must be valid ISO 8601 format

#### FR1.2: Edit Event
- **Description**: Players can edit existing events
- **Capabilities**:
  - Modify all event fields
  - Same validation rules as creation
  - Preserve event ID and creation timestamp

#### FR1.3: Delete Event
- **Description**: Players can delete events
- **Behavior**:
  - Soft delete (mark as deleted) or hard delete
  - Confirmation dialog before deletion

#### FR1.4: View Event Details
- **Description**: Players can view full event details
- **Display**:
  - All event fields
  - Creation timestamp
  - Last modified timestamp

### FR2: Calendar Views

#### FR2.1: Month View
- **Description**: Display calendar in monthly grid format
- **Features**:
  - Show current month with all days
  - Display events on their respective dates
  - Multiple events per day shown as stacked items
  - Navigate to previous/next month
  - Jump to specific month/year
  - Highlight current day
  - Show event indicators (dots/bars) on days with events

#### FR2.2: Week View
- **Description**: Display calendar in weekly format
- **Features**:
  - Show 7 days with hourly time slots
  - Events positioned by time with duration
  - Navigate to previous/next week
  - Current time indicator
  - All-day events shown in dedicated section

#### FR2.3: Day View
- **Description**: Display single day with detailed timeline
- **Features**:
  - Hourly time slots (00:00 - 23:59)
  - Events positioned precisely by time
  - Navigate to previous/next day
  - Jump to specific date
  - Current time indicator

#### FR2.4: List View
- **Description**: Display events as a chronological list
- **Features**:
  - Show upcoming events in order
  - Group by date
  - Filter options (date range, search)
  - Sort options (date, title, location)
  - Pagination for large event lists

### FR3: Backend Integration

#### FR3.1: Backend as Source of Truth
- **Description**: All calendar data stored and managed by backend
- **Capabilities**:
  - RESTful API endpoints for CRUD operations
  - Persistence to disk (game_data/calendar.json)
  - Load calendar data on startup
  - Save calendar data on shutdown and after modifications

#### FR3.2: Backend Event Push
- **Description**: Backend can create events without player action
- **Use Cases**:
  - NPCs can schedule meetings
  - Game events can add reminders
  - System can create notifications
- **Implementation**:
  - WebSocket message: `calendar_event_created`
  - Frontend updates view automatically

#### FR3.3: WebSocket Integration
- **Description**: Real-time synchronization via WebSocket
- **Messages**:
  - `get_events`: Retrieve all events or filtered events
  - `create_event`: Create new event
  - `update_event`: Update existing event
  - `delete_event`: Delete event
  - `calendar_event_created` (push): Backend notifies of new event
  - `calendar_event_updated` (push): Backend notifies of event change
  - `calendar_event_deleted` (push): Backend notifies of event deletion

### FR4: User Interface

#### FR4.1: View Switcher
- **Description**: Easy switching between calendar views
- **Implementation**: Tab bar or dropdown selector
- **Options**: Month, Week, Day, List

#### FR4.2: Navigation Controls
- **Description**: Navigate through time in each view
- **Controls**:
  - Previous/Next buttons
  - "Today" button to jump to current date
  - Date picker for jumping to specific date

#### FR4.3: Event Creation UI
- **Description**: Modal dialog or side panel for creating events
- **Interaction**:
  - Click on date/time slot to create event
  - Pre-fill start/end times based on clicked slot
  - Form validation with error messages
  - "Save" and "Cancel" buttons

#### FR4.4: Event Editing UI
- **Description**: Modal dialog for editing existing events
- **Interaction**:
  - Click on event to view/edit
  - Same form as creation with populated fields
  - "Save", "Delete", and "Cancel" buttons

#### FR4.5: Visual Design
- **Description**: Consistent with RecursiveNeon desktop aesthetic
- **Style**:
  - Futuristic/nostalgic theme
  - Color-coded events
  - Clear typography
  - Responsive layout

### FR5: Data Persistence

#### FR5.1: Save Calendar Data
- **Location**: `backend/game_data/calendar.json`
- **Trigger**:
  - On application shutdown
  - After each event modification
  - Periodic auto-save (every 30 seconds if dirty)

#### FR5.2: Load Calendar Data
- **Trigger**: On application startup
- **Behavior**:
  - Load from `calendar.json` if exists
  - Initialize empty calendar if not exists

---

## Non-Functional Requirements

### NFR1: Performance
- Calendar views should render in < 100ms for up to 1000 events
- Event creation/editing should respond in < 50ms
- WebSocket messages should be processed in < 10ms

### NFR2: Usability
- Intuitive UI requiring no tutorial
- Clear visual feedback for all actions
- Keyboard shortcuts for common actions (optional)

### NFR3: Reliability
- Data should never be lost (proper persistence)
- Graceful error handling for all operations
- Recovery from invalid data states

### NFR4: Maintainability
- Follow RecursiveNeon code conventions
- Comprehensive test coverage (>80%)
- Clear separation of concerns (MVC pattern)

### NFR5: Security
- Input validation on all fields
- Sanitize user input to prevent XSS
- No arbitrary code execution

---

## Data Model

### Event Object

```typescript
interface CalendarEvent {
  id: string;              // UUID
  title: string;           // Max 200 chars
  description?: string;    // Max 2000 chars
  start_time: string;      // ISO 8601 datetime
  end_time: string;        // ISO 8601 datetime
  location?: string;       // Max 200 chars
  color?: string;          // Hex color (e.g., "#FF5733")
  notes?: string;          // Max 5000 chars
  all_day: boolean;        // Default: false
  created_at: string;      // ISO 8601 timestamp
  updated_at: string;      // ISO 8601 timestamp
}
```

### Backend Model (Pydantic)

```python
class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
```

---

## API Endpoints

### REST API

```
GET    /api/calendar/events              - List all events
GET    /api/calendar/events/{id}         - Get specific event
POST   /api/calendar/events              - Create event
PUT    /api/calendar/events/{id}         - Update event
DELETE /api/calendar/events/{id}         - Delete event
GET    /api/calendar/events/range        - Get events in date range
```

### WebSocket Messages

#### Client → Server

```json
{
  "type": "get_calendar_events",
  "data": {
    "start_date": "2025-11-01T00:00:00Z",  // Optional
    "end_date": "2025-11-30T23:59:59Z"     // Optional
  }
}
```

```json
{
  "type": "create_calendar_event",
  "data": {
    "title": "Meeting with Nova",
    "start_time": "2025-11-15T14:00:00Z",
    "end_time": "2025-11-15T15:00:00Z",
    "location": "Engineering Bay",
    "color": "#4A90E2",
    "notes": "Discuss infrastructure upgrades"
  }
}
```

#### Server → Client

```json
{
  "type": "calendar_events_list",
  "data": {
    "events": [...]
  }
}
```

```json
{
  "type": "calendar_event_created",
  "data": {
    "event": {...}
  }
}
```

---

## Testing Requirements

### Backend Tests

1. **Unit Tests**:
   - CalendarEvent model validation
   - CalendarService CRUD operations
   - Event persistence (save/load)
   - Date range filtering

2. **Integration Tests**:
   - WebSocket message handling
   - REST API endpoints
   - Concurrent event modifications

### Frontend Tests

1. **Component Tests**:
   - CalendarApp renders all views
   - Month view displays events correctly
   - Week view time slots
   - Day view navigation
   - Event creation modal
   - Event editing modal

2. **Integration Tests**:
   - Create/edit/delete event workflows
   - View switching
   - WebSocket event updates
   - Date navigation

### Coverage Target

- Backend: >85% code coverage
- Frontend: >80% code coverage

---

## Future Enhancements (Out of Scope for v1)

- Recurring events (daily, weekly, monthly patterns)
- Event categories/tags
- Event reminders/notifications
- Calendar sharing between NPCs
- Event conflicts detection
- Drag-and-drop event rescheduling
- Calendar import/export (iCal format)
- Multi-calendar support
- Event attachments

---

## Success Criteria

1. ✅ All FR requirements implemented
2. ✅ All NFR requirements met
3. ✅ Backend tests pass with >85% coverage
4. ✅ Frontend tests pass with >80% coverage
5. ✅ Calendar integrates seamlessly with Desktop UI
6. ✅ Events persist across app restarts
7. ✅ Backend can push events to frontend
8. ✅ All four view modes functional

---

## Implementation Priority

### Phase 1: Core Backend (Must Have)
- Data models
- Calendar service with DI
- Persistence
- WebSocket integration

### Phase 2: Core Frontend (Must Have)
- Month view
- Event creation/editing
- Basic styling

### Phase 3: Enhanced Views (Must Have)
- Week view
- Day view
- List view

### Phase 4: Polish (Should Have)
- Comprehensive tests
- Error handling
- Performance optimization
- Visual polish

---

**Document Status**: Approved for Implementation
**Last Updated**: 2025-11-15
