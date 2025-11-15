# Time/Date System Requirements

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon
> **Status**: Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Goals and Objectives](#goals-and-objectives)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Data Models](#data-models)
6. [API Requirements](#api-requirements)
7. [Synchronization Requirements](#synchronization-requirements)
8. [Use Cases](#use-cases)
9. [Out of Scope](#out-of-scope)

---

## Overview

The Time/Date System provides game-controlled time that is independent of the operating system's real-time clock. This allows the game to:
- Set arbitrary starting times (e.g., November 13, 2048)
- Jump forward or backward in time for narrative purposes
- Control the rate of time passage (time dilation)
- Pause time completely
- Provide consistent time across all game systems

---

## Goals and Objectives

### Primary Goals

1. **Independence from OS Time**: Game time must be completely decoupled from system time
2. **Controllable Time Flow**: Support pausing, time dilation, and manual time jumps
3. **Backend Authority**: Backend maintains authoritative game time
4. **Frontend Synchronization**: Frontend displays synchronized time with acceptable drift
5. **Persistence**: Game time state persists across sessions
6. **Testability**: All time operations must be easily testable

### Secondary Goals

1. **Performance**: Minimal overhead for time queries
2. **Flexibility**: Easy to extend with additional time-related features
3. **Developer-Friendly**: Simple API for both reading and controlling time

---

## Functional Requirements

### FR-1: Game Time Management

**FR-1.1**: The system SHALL maintain an independent game time that advances separately from OS time.

**FR-1.2**: The system SHALL support setting an arbitrary starting date and time (year, month, day, hour, minute, second).

**FR-1.3**: The system SHALL use standard date/time representations (ISO 8601 format for serialization).

**FR-1.4**: The system SHALL support dates from year 1 to year 9999.

### FR-2: Time Dilation

**FR-2.1**: The system SHALL support a time dilation factor that controls how fast game time progresses relative to real time.

**FR-2.2**: Time dilation factor SHALL be a positive floating-point number where:
- `1.0` = real-time (1 second of real time = 1 second of game time)
- `0.0` = paused (time stopped)
- `2.0` = double speed
- `0.5` = half speed
- `60.0` = 1 minute per real second
- Any positive value SHALL be supported

**FR-2.3**: The system SHALL allow changing the time dilation factor at runtime.

**FR-2.4**: The system SHALL smoothly transition to the new time dilation without time jumps.

### FR-3: Manual Time Control

**FR-3.1**: The system SHALL support manually advancing time by a specified duration.

**FR-3.2**: The system SHALL support manually rewinding time by a specified duration.

**FR-3.3**: The system SHALL support jumping to an absolute date/time.

**FR-3.4**: Manual time changes SHALL take effect immediately.

**FR-3.5**: Manual time changes SHALL persist the new time state.

### FR-4: Time Queries

**FR-4.1**: The system SHALL provide the current game date and time.

**FR-4.2**: The system SHALL provide the current time dilation factor.

**FR-4.3**: The system SHALL provide time in multiple formats:
- Full timestamp (date + time)
- Date only
- Time only
- Unix timestamp (seconds since epoch)
- Formatted strings (customizable)

**FR-4.4**: Time queries SHALL be fast (<1ms for standard queries).

### FR-5: Persistence

**FR-5.1**: The system SHALL save time state when the game shuts down.

**FR-5.2**: The system SHALL restore time state when the game starts up.

**FR-5.3**: Persisted state SHALL include:
- Current game time
- Time dilation factor
- Whether time is paused

**FR-5.4**: If no saved state exists, the system SHALL use default initial values.

### FR-6: Frontend Synchronization

**FR-6.1**: The frontend SHALL periodically synchronize with backend time.

**FR-6.2**: Synchronization SHALL occur:
- On initial connection
- Every N seconds (configurable, default: 5 seconds)
- When time dilation changes
- When manual time changes occur

**FR-6.3**: Frontend SHALL interpolate time between synchronization points using local clock.

**FR-6.4**: Acceptable time drift between frontend and backend: ±2 seconds.

**FR-6.5**: If drift exceeds acceptable threshold, frontend SHALL resynchronize.

### FR-7: Events and Notifications

**FR-7.1**: The system SHALL notify connected clients when:
- Time dilation changes
- Manual time jump occurs
- Time is paused or resumed

**FR-7.2**: Notifications SHALL include:
- Event type
- New time state
- Timestamp of change

### FR-8: Default Configuration

**FR-8.1**: Default starting time: `2048-11-13 08:00:00` (November 13, 2048, 8:00 AM)

**FR-8.2**: Default time dilation: `1.0` (real-time)

**FR-8.3**: Default time zone: UTC (game time is always in UTC)

---

## Non-Functional Requirements

### NFR-1: Performance

**NFR-1.1**: Time queries SHALL complete in <1ms for 99% of requests.

**NFR-1.2**: Time updates SHALL complete in <10ms for 99% of requests.

**NFR-1.3**: The system SHALL support at least 1000 time queries per second.

### NFR-2: Reliability

**NFR-2.1**: Time SHALL never go backward unintentionally (except for manual rewind).

**NFR-2.2**: Time SHALL continue to advance accurately even after long periods of inactivity.

**NFR-2.3**: System SHALL recover gracefully from time synchronization failures.

### NFR-3: Maintainability

**NFR-3.1**: Time service SHALL follow dependency injection patterns.

**NFR-3.2**: Time service SHALL have >90% test coverage.

**NFR-3.3**: Time service SHALL use type hints throughout.

**NFR-3.4**: Time service SHALL be documented with docstrings.

### NFR-4: Testability

**NFR-4.1**: Time service SHALL be easily mockable for testing.

**NFR-4.2**: Time service SHALL not depend on system clock for tests.

**NFR-4.3**: Time service SHALL provide test utilities for simulating time passage.

---

## Data Models

### TimeState

Represents the complete state of the game time system.

```python
class TimeState(BaseModel):
    current_time: datetime          # Current game time (UTC)
    time_dilation: float            # Time dilation factor (>= 0)
    is_paused: bool                 # Whether time is paused
    last_update_real_time: float    # Real time of last update (for interpolation)
```

### TimeUpdate

Message sent to clients when time state changes.

```python
class TimeUpdate(BaseModel):
    current_time: datetime          # Current game time
    time_dilation: float            # Current time dilation
    is_paused: bool                 # Pause state
    update_type: str                # "sync" | "dilation_change" | "manual_jump" | "pause_change"
```

### TimeQuery

Request for current time information.

```python
class TimeQuery(BaseModel):
    format: Optional[str]           # Requested format ("iso" | "timestamp" | "formatted")
    format_string: Optional[str]    # Custom format string if format="formatted"
```

### TimeResponse

Response with current time information.

```python
class TimeResponse(BaseModel):
    current_time: datetime          # Current game time
    time_dilation: float            # Current dilation
    is_paused: bool                 # Pause state
    formatted: Optional[str]        # Formatted time if requested
```

### TimeControlCommand

Command to control time system.

```python
class TimeControlCommand(BaseModel):
    action: str                     # "set_dilation" | "jump_to" | "advance" | "rewind" | "pause" | "resume"
    value: Optional[float]          # Value for the action (dilation, duration, or timestamp)
    target_time: Optional[datetime] # Target time for "jump_to"
```

---

## API Requirements

### Backend API (WebSocket)

#### Get Current Time

```json
// Request
{
  "type": "time",
  "data": {
    "action": "get_time"
  }
}

// Response
{
  "type": "time_response",
  "data": {
    "current_time": "2048-11-13T08:30:45.123Z",
    "time_dilation": 1.0,
    "is_paused": false
  }
}
```

#### Set Time Dilation

```json
// Request
{
  "type": "time",
  "data": {
    "action": "set_dilation",
    "value": 2.0
  }
}

// Response
{
  "type": "time_update",
  "data": {
    "current_time": "2048-11-13T08:30:45.123Z",
    "time_dilation": 2.0,
    "is_paused": false,
    "update_type": "dilation_change"
  }
}
```

#### Jump to Time

```json
// Request
{
  "type": "time",
  "data": {
    "action": "jump_to",
    "target_time": "2048-11-18T12:00:00.000Z"
  }
}

// Response
{
  "type": "time_update",
  "data": {
    "current_time": "2048-11-18T12:00:00.000Z",
    "time_dilation": 1.0,
    "is_paused": false,
    "update_type": "manual_jump"
  }
}
```

#### Advance Time

```json
// Request
{
  "type": "time",
  "data": {
    "action": "advance",
    "value": 3600  // seconds
  }
}
```

#### Pause/Resume

```json
// Request
{
  "type": "time",
  "data": {
    "action": "pause"
  }
}

// Request
{
  "type": "time",
  "data": {
    "action": "resume"
  }
}
```

### Frontend API

```typescript
// Time Service Interface
interface ITimeService {
  // Get current game time (interpolated)
  getCurrentTime(): Date;

  // Get time dilation factor
  getTimeDilation(): number;

  // Check if time is paused
  isPaused(): boolean;

  // Subscribe to time updates
  subscribe(callback: (update: TimeUpdate) => void): () => void;

  // Request immediate synchronization
  sync(): Promise<void>;
}
```

---

## Synchronization Requirements

### Synchronization Strategy

1. **Initial Sync**: On WebSocket connection, frontend requests current time
2. **Periodic Sync**: Frontend requests update every 5 seconds
3. **Event-Driven Sync**: Backend pushes updates on state changes
4. **Local Interpolation**: Frontend calculates current time between syncs

### Synchronization Algorithm

```
Frontend Time Calculation:
  1. Receive sync from backend: {game_time, time_dilation, real_time}
  2. Store as anchor point
  3. To get current time:
     - Calculate real_time_elapsed = current_real_time - anchor_real_time
     - Calculate game_time_elapsed = real_time_elapsed * time_dilation
     - current_game_time = anchor_game_time + game_time_elapsed
```

### Drift Handling

- If calculated drift > 2 seconds: immediate resync
- If sync fails: retry with exponential backoff (1s, 2s, 4s, 8s)
- If multiple sync failures: show warning to user

---

## Use Cases

### UC-1: Game Startup

1. Backend loads saved time state (or uses defaults)
2. Backend starts time service
3. Frontend connects via WebSocket
4. Frontend requests initial time sync
5. Backend sends current time state
6. Frontend starts local time interpolation

### UC-2: Player Pauses Game

1. Game triggers pause command
2. Backend sets time_dilation to 0
3. Backend broadcasts pause event
4. Frontend receives update and stops time interpolation
5. UI shows time is paused

### UC-3: Story Event Advances Time

1. Story script calls time service to advance 5 days
2. Backend adds 5 days to current time
3. Backend broadcasts manual jump event
4. Frontend receives update and resyncs
5. Clock widget shows new date

### UC-4: Puzzle Mode - Accelerated Time

1. Puzzle starts
2. Game sets time_dilation to 60.0 (1 minute per second)
3. Backend broadcasts dilation change
4. Frontend adjusts interpolation calculation
5. Clock visibly advances faster

### UC-5: Time Synchronization Drift Detected

1. Frontend calculates expected time
2. Frontend requests sync from backend
3. Backend responds with authoritative time
4. Frontend detects 3-second drift
5. Frontend smoothly adjusts to backend time
6. Frontend logs drift for debugging

### UC-6: Network Disconnection and Reconnection

1. WebSocket disconnects
2. Frontend continues interpolation (may drift)
3. WebSocket reconnects
4. Frontend immediately requests sync
5. Backend sends current time
6. Frontend corrects any accumulated drift

---

## Out of Scope

The following features are explicitly out of scope for version 1.0:

1. **Multiple Time Zones**: All times in UTC
2. **Calendars**: No calendar view or date picker
3. **Time-Based Events**: No built-in event scheduling (other systems can use time service)
4. **Historical Time Tracking**: No recording of time state changes
5. **Network Time Protocol (NTP)**: No synchronization with real-world time servers
6. **Daylight Saving Time**: Not applicable (UTC only)
7. **Leap Seconds**: Standard datetime handling
8. **Astronomical Calculations**: No sunrise/sunset, moon phases, etc.
9. **Multiple Simultaneous Timelines**: Single timeline only

---

## Acceptance Criteria

The time system shall be considered complete when:

1. ✅ Backend time service is implemented with all FR requirements
2. ✅ Frontend time service is implemented with synchronization
3. ✅ All API endpoints are functional and tested
4. ✅ Time persists across backend restarts
5. ✅ Frontend stays synchronized within ±2 seconds
6. ✅ Time dilation works correctly for values 0.0 to 100.0
7. ✅ Manual time jumps work correctly
8. ✅ Unit tests achieve >90% coverage
9. ✅ Integration tests verify synchronization
10. ✅ Documentation is complete and accurate

---

## Future Enhancements

Potential future additions (not in v1.0):

1. **Time Events**: Trigger callbacks at specific game times
2. **Time Zones**: Support for multiple time zones in UI
3. **Calendar System**: Visual calendar with game events
4. **Time Compression Profiles**: Predefined time dilation presets
5. **Time Debugging Tools**: UI for developers to manipulate time
6. **Time Analytics**: Track time dilation usage and time jumps
7. **Synchronized Audio**: Music tempo adjusts with time dilation
8. **Time-Aware Animations**: Animations respect time dilation

---

**Document Status**: Ready for review
**Next Steps**: Create design document and begin implementation
