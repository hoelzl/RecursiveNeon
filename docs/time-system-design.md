# Time/Date System Design

> **Version**: 1.0
> **Date**: 2025-11-15
> **Project**: Recursive://Neon
> **Status**: Draft

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Design](#backend-design)
3. [Frontend Design](#frontend-design)
4. [Synchronization Design](#synchronization-design)
5. [Data Flow](#data-flow)
6. [Implementation Details](#implementation-details)
7. [Testing Strategy](#testing-strategy)
8. [Performance Considerations](#performance-considerations)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│                                                         │
│  ┌──────────────┐      ┌─────────────────────┐        │
│  │ Clock Widget │◄─────┤ TimeService (Client)│        │
│  └──────────────┘      │                     │        │
│                        │ - Interpolation     │        │
│  ┌──────────────┐      │ - Synchronization   │        │
│  │ Other UI     │◄─────┤ - Event Handling    │        │
│  │ Components   │      └─────────┬───────────┘        │
│  └──────────────┘                │                     │
│                                   │ WebSocket          │
└───────────────────────────────────┼─────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────┐
│                      Backend      │                     │
│                                   ▼                     │
│  ┌──────────────────────────────────────────┐          │
│  │      MessageHandler                      │          │
│  │      (routes time messages)              │          │
│  └──────────────┬───────────────────────────┘          │
│                 │                                       │
│                 ▼                                       │
│  ┌──────────────────────────────────────────┐          │
│  │      TimeService (Backend)               │          │
│  │                                           │          │
│  │  - Authoritative time source             │          │
│  │  - Time dilation control                 │          │
│  │  - Manual time manipulation              │          │
│  │  - Persistence                            │          │
│  │                                           │          │
│  │  ┌────────────┐    ┌──────────────┐     │          │
│  │  │ TimeState  │    │ TimePersist  │     │          │
│  │  │ (in-memory)│◄───┤ (JSON file)  │     │          │
│  │  └────────────┘    └──────────────┘     │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Backend Authority**: Backend is the single source of truth for time
2. **Client Interpolation**: Frontend interpolates between sync points for smooth display
3. **Event-Driven Sync**: Backend pushes updates on state changes
4. **Periodic Sync**: Frontend periodically resyncs to prevent drift
5. **Graceful Degradation**: System continues functioning if sync temporarily fails
6. **Testability**: All components easily mockable and testable

---

## Backend Design

### TimeService Interface

```python
# backend/src/recursive_neon/services/interfaces.py

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any

class ITimeService(ABC):
    """Interface for game time management."""

    @abstractmethod
    def get_current_time(self) -> datetime:
        """Get the current game time."""
        pass

    @abstractmethod
    def get_time_state(self) -> Dict[str, Any]:
        """Get complete time state including dilation and pause status."""
        pass

    @abstractmethod
    def set_time_dilation(self, dilation: float) -> None:
        """Set time dilation factor (0.0 = paused, 1.0 = real-time, etc.)."""
        pass

    @abstractmethod
    def get_time_dilation(self) -> float:
        """Get current time dilation factor."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause time (equivalent to set_time_dilation(0.0))."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume time at previous dilation rate."""
        pass

    @abstractmethod
    def is_paused(self) -> bool:
        """Check if time is currently paused."""
        pass

    @abstractmethod
    def jump_to(self, target_time: datetime) -> None:
        """Jump to a specific time."""
        pass

    @abstractmethod
    def advance(self, duration: timedelta) -> None:
        """Advance time by a specific duration."""
        pass

    @abstractmethod
    def rewind(self, duration: timedelta) -> None:
        """Rewind time by a specific duration."""
        pass

    @abstractmethod
    def reset_to_default(self) -> None:
        """Reset to default time and dilation."""
        pass

    @abstractmethod
    def save_state(self) -> None:
        """Save current time state to disk."""
        pass

    @abstractmethod
    def load_state(self) -> None:
        """Load time state from disk."""
        pass
```

### TimeService Implementation

```python
# backend/src/recursive_neon/services/time_service.py

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging
from pydantic import BaseModel

from recursive_neon.services.interfaces import ITimeService

logger = logging.getLogger(__name__)

class TimeState(BaseModel):
    """State of the game time system."""
    game_time: datetime              # Current game time (UTC)
    time_dilation: float             # Time dilation factor
    is_paused: bool                  # Pause state
    last_real_time: float           # Last real time update (monotonic)
    previous_dilation: float        # Dilation before pause (for resume)

class TimeService(ITimeService):
    """Game time management service."""

    DEFAULT_GAME_TIME = datetime(2048, 11, 13, 8, 0, 0, tzinfo=timezone.utc)
    DEFAULT_DILATION = 1.0

    def __init__(self, persistence_path: Optional[Path] = None):
        """Initialize time service.

        Args:
            persistence_path: Path to save/load time state
        """
        self.persistence_path = persistence_path
        self._state = TimeState(
            game_time=self.DEFAULT_GAME_TIME,
            time_dilation=self.DEFAULT_DILATION,
            is_paused=False,
            last_real_time=time.monotonic(),
            previous_dilation=self.DEFAULT_DILATION,
        )
        self._update_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Try to load saved state
        if persistence_path and persistence_path.exists():
            try:
                self.load_state()
            except Exception as e:
                logger.warning(f"Failed to load time state: {e}, using defaults")

    def _update_time(self) -> None:
        """Update game time based on elapsed real time."""
        current_real_time = time.monotonic()
        real_elapsed = current_real_time - self._state.last_real_time

        if not self._state.is_paused:
            game_elapsed = timedelta(seconds=real_elapsed * self._state.time_dilation)
            self._state.game_time += game_elapsed

        self._state.last_real_time = current_real_time

    def get_current_time(self) -> datetime:
        """Get current game time."""
        self._update_time()
        return self._state.game_time

    def get_time_state(self) -> Dict[str, Any]:
        """Get complete time state."""
        self._update_time()
        return {
            "current_time": self._state.game_time.isoformat(),
            "time_dilation": self._state.time_dilation,
            "is_paused": self._state.is_paused,
            "real_time": self._state.last_real_time,
        }

    def set_time_dilation(self, dilation: float) -> None:
        """Set time dilation factor."""
        if dilation < 0:
            raise ValueError("Time dilation must be non-negative")

        self._update_time()
        old_dilation = self._state.time_dilation
        self._state.time_dilation = dilation
        self._state.is_paused = (dilation == 0.0)

        if not self._state.is_paused:
            self._state.previous_dilation = dilation

        self._notify_change("dilation_change", {
            "old_dilation": old_dilation,
            "new_dilation": dilation,
        })
        self.save_state()

    def get_time_dilation(self) -> float:
        """Get current time dilation."""
        return self._state.time_dilation

    def pause(self) -> None:
        """Pause time."""
        if not self._state.is_paused:
            self._update_time()
            self._state.previous_dilation = self._state.time_dilation
            self._state.time_dilation = 0.0
            self._state.is_paused = True
            self._notify_change("pause", {})
            self.save_state()

    def resume(self) -> None:
        """Resume time."""
        if self._state.is_paused:
            self._update_time()
            self._state.time_dilation = self._state.previous_dilation
            self._state.is_paused = False
            self._notify_change("resume", {})
            self.save_state()

    def is_paused(self) -> bool:
        """Check if paused."""
        return self._state.is_paused

    def jump_to(self, target_time: datetime) -> None:
        """Jump to specific time."""
        self._update_time()
        old_time = self._state.game_time
        self._state.game_time = target_time.replace(tzinfo=timezone.utc)
        self._notify_change("manual_jump", {
            "old_time": old_time.isoformat(),
            "new_time": self._state.game_time.isoformat(),
        })
        self.save_state()

    def advance(self, duration: timedelta) -> None:
        """Advance time by duration."""
        self._update_time()
        self._state.game_time += duration
        self._notify_change("manual_advance", {
            "duration": duration.total_seconds(),
        })
        self.save_state()

    def rewind(self, duration: timedelta) -> None:
        """Rewind time by duration."""
        self._update_time()
        self._state.game_time -= duration
        self._notify_change("manual_rewind", {
            "duration": duration.total_seconds(),
        })
        self.save_state()

    def reset_to_default(self) -> None:
        """Reset to defaults."""
        self._state.game_time = self.DEFAULT_GAME_TIME
        self._state.time_dilation = self.DEFAULT_DILATION
        self._state.is_paused = False
        self._state.last_real_time = time.monotonic()
        self._state.previous_dilation = self.DEFAULT_DILATION
        self._notify_change("reset", {})
        self.save_state()

    def save_state(self) -> None:
        """Save state to disk."""
        if not self.persistence_path:
            return

        try:
            self._update_time()
            data = {
                "game_time": self._state.game_time.isoformat(),
                "time_dilation": self._state.time_dilation,
                "is_paused": self._state.is_paused,
                "previous_dilation": self._state.previous_dilation,
            }

            # Atomic write
            temp_path = self.persistence_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.persistence_path)

            logger.debug(f"Saved time state to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save time state: {e}")

    def load_state(self) -> None:
        """Load state from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            self._state.game_time = datetime.fromisoformat(data["game_time"])
            self._state.time_dilation = data["time_dilation"]
            self._state.is_paused = data["is_paused"]
            self._state.previous_dilation = data.get("previous_dilation", self.DEFAULT_DILATION)
            self._state.last_real_time = time.monotonic()

            logger.info(f"Loaded time state from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load time state: {e}")
            raise

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to time change events."""
        self._update_callbacks.append(callback)

    def _notify_change(self, change_type: str, details: Dict[str, Any]) -> None:
        """Notify subscribers of time change."""
        event = {
            "type": change_type,
            "state": self.get_time_state(),
            "details": details,
        }
        for callback in self._update_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in time change callback: {e}")
```

### Integration with MessageHandler

```python
# backend/src/recursive_neon/services/message_handler.py

# Add time handling methods

async def _handle_time_message(self, data: dict) -> Dict[str, Any]:
    """Handle time-related messages."""
    action = data.get("action")

    if action == "get_time":
        return {
            "type": "time_response",
            "data": self.time_service.get_time_state()
        }

    elif action == "set_dilation":
        value = data.get("value")
        if value is None or value < 0:
            return {"type": "error", "message": "Invalid dilation value"}

        self.time_service.set_time_dilation(value)
        return {
            "type": "time_update",
            "data": self.time_service.get_time_state(),
            "update_type": "dilation_change"
        }

    elif action == "pause":
        self.time_service.pause()
        return {
            "type": "time_update",
            "data": self.time_service.get_time_state(),
            "update_type": "pause"
        }

    elif action == "resume":
        self.time_service.resume()
        return {
            "type": "time_update",
            "data": self.time_service.get_time_state(),
            "update_type": "resume"
        }

    elif action == "jump_to":
        target_time_str = data.get("target_time")
        if not target_time_str:
            return {"type": "error", "message": "Missing target_time"}

        target_time = datetime.fromisoformat(target_time_str)
        self.time_service.jump_to(target_time)
        return {
            "type": "time_update",
            "data": self.time_service.get_time_state(),
            "update_type": "manual_jump"
        }

    elif action == "advance":
        seconds = data.get("value")
        if seconds is None:
            return {"type": "error", "message": "Missing duration"}

        self.time_service.advance(timedelta(seconds=seconds))
        return {
            "type": "time_update",
            "data": self.time_service.get_time_state(),
            "update_type": "manual_advance"
        }

    else:
        return {"type": "error", "message": f"Unknown time action: {action}"}
```

---

## Frontend Design

### TimeService (Frontend)

```typescript
// frontend/src/services/timeService.ts

export interface TimeState {
  currentTime: Date;
  timeDilation: number;
  isPaused: boolean;
}

export interface TimeUpdate {
  current_time: string;      // ISO 8601
  time_dilation: number;
  is_paused: boolean;
  real_time: number;
  update_type?: string;
}

type TimeUpdateCallback = (state: TimeState) => void;

export class TimeService {
  private anchorGameTime: Date;
  private anchorRealTime: number;
  private timeDilation: number;
  private isPaused: boolean;
  private subscribers: TimeUpdateCallback[];
  private syncInterval: number | null;
  private wsClient: WebSocketClient | null;

  constructor() {
    this.anchorGameTime = new Date();
    this.anchorRealTime = performance.now();
    this.timeDilation = 1.0;
    this.isPaused = false;
    this.subscribers = [];
    this.syncInterval = null;
    this.wsClient = null;
  }

  /**
   * Initialize with WebSocket client and start syncing.
   */
  initialize(wsClient: WebSocketClient): void {
    this.wsClient = wsClient;

    // Subscribe to time updates from backend
    wsClient.addMessageHandler('time_response', this.handleTimeUpdate.bind(this));
    wsClient.addMessageHandler('time_update', this.handleTimeUpdate.bind(this));

    // Request initial sync
    this.sync();

    // Start periodic sync (every 5 seconds)
    this.syncInterval = window.setInterval(() => {
      this.sync();
    }, 5000);
  }

  /**
   * Clean up resources.
   */
  destroy(): void {
    if (this.syncInterval !== null) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Get current game time (interpolated).
   */
  getCurrentTime(): Date {
    if (this.isPaused) {
      return new Date(this.anchorGameTime);
    }

    const realElapsed = (performance.now() - this.anchorRealTime) / 1000; // seconds
    const gameElapsed = realElapsed * this.timeDilation;
    const currentTime = new Date(this.anchorGameTime.getTime() + gameElapsed * 1000);

    return currentTime;
  }

  /**
   * Get current time dilation.
   */
  getTimeDilation(): number {
    return this.timeDilation;
  }

  /**
   * Check if time is paused.
   */
  isTimePaused(): boolean {
    return this.isPaused;
  }

  /**
   * Get complete time state.
   */
  getState(): TimeState {
    return {
      currentTime: this.getCurrentTime(),
      timeDilation: this.timeDilation,
      isPaused: this.isPaused,
    };
  }

  /**
   * Subscribe to time updates.
   */
  subscribe(callback: TimeUpdateCallback): () => void {
    this.subscribers.push(callback);
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index > -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  /**
   * Request sync from backend.
   */
  async sync(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'get_time',
      },
    });
  }

  /**
   * Handle time update from backend.
   */
  private handleTimeUpdate(message: any): void {
    const data: TimeUpdate = message.data;

    // Update anchor point
    this.anchorGameTime = new Date(data.current_time);
    this.anchorRealTime = performance.now();
    this.timeDilation = data.time_dilation;
    this.isPaused = data.is_paused;

    // Notify subscribers
    this.notifySubscribers();
  }

  /**
   * Notify all subscribers of state change.
   */
  private notifySubscribers(): void {
    const state = this.getState();
    this.subscribers.forEach(callback => {
      try {
        callback(state);
      } catch (error) {
        console.error('Error in time update callback:', error);
      }
    });
  }

  // Control methods (send commands to backend)

  async setTimeDilation(dilation: number): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'set_dilation',
        value: dilation,
      },
    });
  }

  async pause(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'pause',
      },
    });
  }

  async resume(): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'resume',
      },
    });
  }

  async jumpTo(targetTime: Date): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'jump_to',
        target_time: targetTime.toISOString(),
      },
    });
  }

  async advance(seconds: number): Promise<void> {
    if (!this.wsClient) return;

    this.wsClient.sendMessage({
      type: 'time',
      data: {
        action: 'advance',
        value: seconds,
      },
    });
  }
}
```

### TimeService Context

```typescript
// frontend/src/contexts/TimeServiceContext.tsx

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { TimeService, TimeState } from '../services/timeService';
import { useWebSocket } from './WebSocketContext';

interface TimeServiceContextType {
  timeService: TimeService;
  timeState: TimeState;
}

const TimeServiceContext = createContext<TimeServiceContextType | null>(null);

export function TimeServiceProvider({ children }: { children: ReactNode }) {
  const wsClient = useWebSocket();
  const [timeService] = useState(() => new TimeService());
  const [timeState, setTimeState] = useState<TimeState>(timeService.getState());

  useEffect(() => {
    if (wsClient) {
      timeService.initialize(wsClient);
    }

    return () => {
      timeService.destroy();
    };
  }, [wsClient, timeService]);

  useEffect(() => {
    const unsubscribe = timeService.subscribe(setTimeState);
    return unsubscribe;
  }, [timeService]);

  return (
    <TimeServiceContext.Provider value={{ timeService, timeState }}>
      {children}
    </TimeServiceContext.Provider>
  );
}

export function useTimeService(): TimeServiceContextType {
  const context = useContext(TimeServiceContext);
  if (!context) {
    throw new Error('useTimeService must be used within TimeServiceProvider');
  }
  return context;
}
```

---

## Synchronization Design

### Synchronization Flow

```
Time T0: Backend = 2048-11-13 08:00:00, Dilation = 1.0
         ↓
Frontend requests sync
         ↓
Backend responds: {
  game_time: "2048-11-13T08:00:00Z",
  real_time: 1000.5,
  dilation: 1.0
}
         ↓
Frontend stores anchor:
  anchorGameTime = 2048-11-13 08:00:00
  anchorRealTime = 1000.5
         ↓
Time T0 + 2.5s: Frontend calculates current time:
  realElapsed = 2.5s
  gameElapsed = 2.5s * 1.0 = 2.5s
  currentTime = 2048-11-13 08:00:02.5
         ↓
Time T0 + 5s: Frontend syncs again
         ↓
Backend responds: {
  game_time: "2048-11-13T08:00:05Z",
  real_time: 1005.5,
  dilation: 1.0
}
         ↓
Frontend updates anchor (smooth correction if drift exists)
```

### Drift Detection and Correction

```typescript
// In handleTimeUpdate method

private handleTimeUpdate(message: any): void {
  const data: TimeUpdate = message.data;
  const backendTime = new Date(data.current_time);

  // Calculate expected time based on current anchor
  const expectedTime = this.getCurrentTime();

  // Calculate drift
  const drift = Math.abs(backendTime.getTime() - expectedTime.getTime());

  if (drift > 2000) { // > 2 seconds
    console.warn(`Time drift detected: ${drift}ms, resyncing`);
  }

  // Update anchor (this corrects any drift)
  this.anchorGameTime = backendTime;
  this.anchorRealTime = performance.now();
  this.timeDilation = data.time_dilation;
  this.isPaused = data.is_paused;

  this.notifySubscribers();
}
```

---

## Data Flow

### Time Query Flow

```
1. Frontend component calls timeService.getCurrentTime()
2. TimeService interpolates from anchor point
3. Return interpolated time
```

### Time Control Flow

```
1. User action (e.g., pause button)
2. Frontend calls timeService.pause()
3. TimeService sends WebSocket message to backend
4. Backend TimeService pauses time
5. Backend broadcasts update to all clients
6. Frontend receives update
7. Frontend updates anchor and notifies subscribers
8. UI updates (clock stops, etc.)
```

### Periodic Sync Flow

```
Every 5 seconds:
1. Timer fires in frontend TimeService
2. Frontend sends "get_time" message
3. Backend responds with current state
4. Frontend updates anchor
5. Any accumulated drift is corrected
```

---

## Implementation Details

### File Structure

**Backend**:
- `backend/src/recursive_neon/services/interfaces.py` - Add ITimeService
- `backend/src/recursive_neon/services/time_service.py` - TimeService implementation
- `backend/src/recursive_neon/models/time_models.py` - Time-related Pydantic models
- `backend/src/recursive_neon/dependencies.py` - Add TimeService to container
- `backend/src/recursive_neon/services/message_handler.py` - Add time message handling
- `backend/tests/unit/test_time_service.py` - Unit tests
- `backend/tests/integration/test_time_sync.py` - Integration tests

**Frontend**:
- `frontend/src/services/timeService.ts` - TimeService class
- `frontend/src/contexts/TimeServiceContext.tsx` - Context provider
- `frontend/src/components/ClockWidget.tsx` - Clock widget component
- `frontend/src/components/ClockAnalog.tsx` - Analog clock face
- `frontend/src/components/ClockDigital.tsx` - Digital clock display
- `frontend/src/test/timeService.test.ts` - Unit tests

### Dependency Injection Updates

```python
# backend/src/recursive_neon/dependencies.py

from pathlib import Path
from recursive_neon.services.time_service import TimeService

@dataclass
class ServiceContainer:
    # ... existing services
    time_service: ITimeService

class ServiceFactory:
    @staticmethod
    def create_production_container() -> ServiceContainer:
        # ... create other services

        # Create time service
        game_data_path = Path("game_data")
        game_data_path.mkdir(exist_ok=True)
        time_persistence_path = game_data_path / "time_state.json"

        time_service = TimeService(persistence_path=time_persistence_path)

        return ServiceContainer(
            # ... existing services
            time_service=time_service,
        )
```

### Lifespan Management

```python
# backend/src/recursive_neon/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _container

    # Startup
    _container = ServiceFactory.create_production_container()

    # Load time state
    _container.time_service.load_state()

    # Start other services...
    await _container.process_manager.start()
    # ...

    yield

    # Shutdown
    # Save time state
    _container.time_service.save_state()

    # Shutdown other services...
```

---

## Testing Strategy

### Backend Unit Tests

```python
# backend/tests/unit/test_time_service.py

class TestTimeService:
    def test_initialization_with_defaults(self):
        """Test service initializes with default values."""
        service = TimeService()
        assert service.get_time_dilation() == 1.0
        assert not service.is_paused()
        # Time should be close to default
        assert service.get_current_time().year == 2048

    def test_set_time_dilation(self):
        """Test setting time dilation."""
        service = TimeService()
        service.set_time_dilation(2.0)
        assert service.get_time_dilation() == 2.0

    def test_time_advances_with_dilation(self):
        """Test time advances at correct rate."""
        service = TimeService()
        start_time = service.get_current_time()

        time.sleep(1.0)  # Sleep 1 real second
        service.set_time_dilation(2.0)

        time.sleep(1.0)  # Sleep 1 more real second
        end_time = service.get_current_time()

        # First second at 1.0x, second second at 2.0x = 3 seconds total
        elapsed = (end_time - start_time).total_seconds()
        assert 2.8 < elapsed < 3.2  # Allow some tolerance

    def test_pause_and_resume(self):
        """Test pausing and resuming time."""
        service = TimeService()
        service.pause()
        assert service.is_paused()

        time_before = service.get_current_time()
        time.sleep(0.5)
        time_after = service.get_current_time()

        assert time_before == time_after  # Time should not advance

        service.resume()
        assert not service.is_paused()

    def test_manual_jump(self):
        """Test jumping to specific time."""
        service = TimeService()
        target = datetime(2049, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        service.jump_to(target)

        current = service.get_current_time()
        assert current.year == 2049
        assert current.month == 1
        assert current.day == 1

    def test_advance_and_rewind(self):
        """Test advancing and rewinding time."""
        service = TimeService()
        start = service.get_current_time()

        service.advance(timedelta(days=5))
        after_advance = service.get_current_time()
        assert (after_advance - start).days == 5

        service.rewind(timedelta(days=2))
        after_rewind = service.get_current_time()
        assert (after_rewind - start).days == 3

    def test_persistence(self, tmp_path):
        """Test saving and loading state."""
        save_path = tmp_path / "time_state.json"

        # Create service and modify state
        service1 = TimeService(persistence_path=save_path)
        service1.set_time_dilation(5.0)
        target_time = datetime(2050, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        service1.jump_to(target_time)
        service1.save_state()

        # Create new service and load
        service2 = TimeService(persistence_path=save_path)
        service2.load_state()

        assert service2.get_time_dilation() == 5.0
        loaded_time = service2.get_current_time()
        assert loaded_time.year == 2050
        assert loaded_time.month == 6

    def test_notifications(self):
        """Test change notifications."""
        service = TimeService()
        notifications = []

        def callback(event):
            notifications.append(event)

        service.subscribe(callback)

        service.set_time_dilation(3.0)
        assert len(notifications) == 1
        assert notifications[0]["type"] == "dilation_change"

        service.pause()
        assert len(notifications) == 2
        assert notifications[1]["type"] == "pause"
```

### Frontend Unit Tests

```typescript
// frontend/src/test/timeService.test.ts

describe('TimeService', () => {
  let timeService: TimeService;
  let mockWsClient: jest.Mocked<WebSocketClient>;

  beforeEach(() => {
    timeService = new TimeService();
    mockWsClient = createMockWebSocketClient();
  });

  afterEach(() => {
    timeService.destroy();
  });

  test('initializes with default values', () => {
    const state = timeService.getState();
    expect(state.timeDilation).toBe(1.0);
    expect(state.isPaused).toBe(false);
  });

  test('interpolates time correctly', () => {
    const anchorTime = new Date('2048-11-13T08:00:00Z');

    // Simulate backend update
    timeService['handleTimeUpdate']({
      data: {
        current_time: anchorTime.toISOString(),
        time_dilation: 1.0,
        is_paused: false,
        real_time: performance.now(),
      },
    });

    // Wait 1 second
    jest.advanceTimersByTime(1000);

    const currentTime = timeService.getCurrentTime();
    const expected = new Date(anchorTime.getTime() + 1000);

    expect(Math.abs(currentTime.getTime() - expected.getTime())).toBeLessThan(100);
  });

  test('handles time dilation', () => {
    const anchorTime = new Date('2048-11-13T08:00:00Z');

    timeService['handleTimeUpdate']({
      data: {
        current_time: anchorTime.toISOString(),
        time_dilation: 2.0,
        is_paused: false,
        real_time: performance.now(),
      },
    });

    jest.advanceTimersByTime(1000); // 1 real second

    const currentTime = timeService.getCurrentTime();
    const expected = new Date(anchorTime.getTime() + 2000); // 2 game seconds

    expect(Math.abs(currentTime.getTime() - expected.getTime())).toBeLessThan(100);
  });

  test('handles pause', () => {
    const anchorTime = new Date('2048-11-13T08:00:00Z');

    timeService['handleTimeUpdate']({
      data: {
        current_time: anchorTime.toISOString(),
        time_dilation: 0.0,
        is_paused: true,
        real_time: performance.now(),
      },
    });

    const timeBefore = timeService.getCurrentTime();
    jest.advanceTimersByTime(5000);
    const timeAfter = timeService.getCurrentTime();

    expect(timeBefore.getTime()).toBe(timeAfter.getTime());
  });

  test('notifies subscribers on update', () => {
    const callback = jest.fn();
    timeService.subscribe(callback);

    timeService['handleTimeUpdate']({
      data: {
        current_time: new Date().toISOString(),
        time_dilation: 1.0,
        is_paused: false,
        real_time: performance.now(),
      },
    });

    expect(callback).toHaveBeenCalled();
  });

  test('syncs periodically', () => {
    timeService.initialize(mockWsClient);

    jest.advanceTimersByTime(5000);

    expect(mockWsClient.sendMessage).toHaveBeenCalledWith({
      type: 'time',
      data: { action: 'get_time' },
    });
  });
});
```

### Integration Tests

Test full sync cycle with real WebSocket connection (mocked backend responses).

---

## Performance Considerations

### Backend Performance

1. **Time Calculation**: O(1) operation, no loops
2. **State Updates**: In-memory updates, minimal overhead
3. **Persistence**: Atomic file write, ~1-5ms
4. **Notifications**: Fan-out to N clients, O(N) but async

### Frontend Performance

1. **Time Interpolation**: Pure calculation, <0.1ms
2. **Sync Frequency**: 5 seconds is acceptable
3. **UI Updates**: Only when state changes or on render
4. **Memory**: Minimal (single anchor point + state)

### Optimizations

1. **Debounce UI Updates**: Clock widget updates at most 60fps
2. **Lazy Formatting**: Only format time when rendering
3. **Batch Notifications**: Group rapid changes
4. **Connection Resilience**: Exponential backoff on sync failures

---

**Document Status**: Ready for implementation
**Next Steps**: Begin backend implementation with TimeService
