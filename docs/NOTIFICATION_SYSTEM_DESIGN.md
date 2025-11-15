# Notification System Design

> **Project**: Recursive://Neon - LLM-Powered RPG
> **Feature**: Desktop Notification System
> **Version**: 1.0
> **Date**: 2025-11-15

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [API Specification](#api-specification)
5. [State Management](#state-management)
6. [UI/UX Design](#uiux-design)
7. [Implementation Plan](#implementation-plan)
8. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Desktop Component                      │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │        NotificationContainer                      │  │ │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │  │ │
│  │  │  │ Toast #1   │ │ Toast #2   │ │ Toast #3   │   │  │ │
│  │  │  └────────────┘ └────────────┘ └────────────┘   │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │               Taskbar                             │  │ │
│  │  │  [...] [NotificationIndicator 🔔 3] [Clock]      │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        Window: Notification Center App                 │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │  Filters: [All] [Info] [Success] [Warning] [Error]│ │ │
│  │  │  Search: [________________]                       │ │ │
│  │  │  ───────────────────────────────────────────────  │ │ │
│  │  │  ● System Ready              12:30 PM             │ │ │
│  │  │  ● New message from Nova     12:25 PM             │ │ │
│  │  │    Task completed            12:20 PM             │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Zustand Notification Store                     │ │
│  │  - activeNotifications: Notification[]                 │ │
│  │  - history: Notification[]                             │ │
│  │  - unreadCount: number                                 │ │
│  │  - config: NotificationConfig                          │ │
│  │  - Actions: create, dismiss, markRead, delete, etc.   │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕ WebSocket / HTTP                 │
└───────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                          Backend                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                FastAPI Application                      │ │
│  │                                                          │ │
│  │  HTTP Endpoints:                                        │ │
│  │  - POST   /api/notifications                           │ │
│  │  - GET    /api/notifications                           │ │
│  │  - GET    /api/notifications/{id}                      │ │
│  │  - PATCH  /api/notifications/{id}                      │ │
│  │  - DELETE /api/notifications/{id}                      │ │
│  │  - DELETE /api/notifications                           │ │
│  │  - GET    /api/notifications/unread-count              │ │
│  │                                                          │ │
│  │  WebSocket:                                             │ │
│  │  - notification_created                                 │ │
│  │  - notification_updated                                 │ │
│  │  - notification_deleted                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          NotificationService (INotificationService)    │ │
│  │  - create_notification(data) -> Notification           │ │
│  │  - get_notification(id) -> Notification                │ │
│  │  - list_notifications(filters) -> List[Notification]   │ │
│  │  - update_notification(id, data) -> Notification       │ │
│  │  - delete_notification(id) -> bool                     │ │
│  │  - clear_all_notifications() -> int                    │ │
│  │  - get_unread_count() -> int                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    GameState                            │ │
│  │  - notifications: List[Notification]                   │ │
│  │  - notification_config: NotificationConfig             │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↕                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Persistent Storage (JSON)                  │ │
│  │  backend/game_data/game_state.json                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Backend manages data/business logic, frontend handles display
2. **Dependency Injection**: Services injected via DI container for testability
3. **Real-Time Updates**: WebSocket for instant notification delivery
4. **Type Safety**: Pydantic (backend) and TypeScript (frontend) for validation
5. **Persistence**: All notifications saved to game state for history
6. **Reactive State**: Zustand for efficient state management and re-renders

---

## Component Design

### Backend Components

#### 1. Notification Model (`models/notification.py`)

```python
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4

class NotificationType(str, Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class Notification(BaseModel):
    """Core notification model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=100)
    message: Optional[str] = Field(None, max_length=500)
    type: NotificationType = NotificationType.INFO
    source: str = Field(..., min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    read: bool = False
    dismissed: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Task Complete",
                "message": "Your file has been saved",
                "type": "success",
                "source": "file-browser",
                "created_at": "2025-11-15T12:30:00Z",
                "read": False,
                "dismissed": False
            }
        }

class NotificationCreate(BaseModel):
    """Request model for creating notifications"""
    title: str = Field(..., min_length=1, max_length=100)
    message: Optional[str] = Field(None, max_length=500)
    type: NotificationType = NotificationType.INFO
    source: str = Field(..., min_length=1, max_length=50)
    duration: Optional[int] = Field(None, ge=0, le=60000)  # Not stored, for client

class NotificationUpdate(BaseModel):
    """Request model for updating notifications"""
    read: Optional[bool] = None
    dismissed: Optional[bool] = None

class NotificationConfig(BaseModel):
    """Configuration for notification display"""
    position: str = "top-right"
    default_duration: int = 5000  # milliseconds
    max_visible: int = 5
    sound_enabled: bool = False

class NotificationFilters(BaseModel):
    """Filters for querying notifications"""
    type: Optional[NotificationType] = None
    source: Optional[str] = None
    read: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
```

#### 2. Notification Service Interface (`services/interfaces.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from recursive_neon.models.notification import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationConfig
)

class INotificationService(ABC):
    """Interface for notification service"""

    @abstractmethod
    def create_notification(self, data: NotificationCreate) -> Notification:
        """Create a new notification"""
        pass

    @abstractmethod
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification by ID"""
        pass

    @abstractmethod
    def list_notifications(
        self,
        filters: NotificationFilters
    ) -> List[Notification]:
        """List notifications with optional filters"""
        pass

    @abstractmethod
    def update_notification(
        self,
        notification_id: str,
        data: NotificationUpdate
    ) -> Optional[Notification]:
        """Update a notification"""
        pass

    @abstractmethod
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification"""
        pass

    @abstractmethod
    def clear_all_notifications(self) -> int:
        """Delete all notifications, returns count deleted"""
        pass

    @abstractmethod
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        pass

    @abstractmethod
    def get_config(self) -> NotificationConfig:
        """Get notification configuration"""
        pass

    @abstractmethod
    def update_config(self, config: NotificationConfig) -> NotificationConfig:
        """Update notification configuration"""
        pass
```

#### 3. Notification Service Implementation (`services/notification_service.py`)

```python
from typing import List, Optional
from datetime import datetime, timedelta
from recursive_neon.models.notification import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationConfig,
    NotificationType
)
from recursive_neon.models.game_state import GameState
from recursive_neon.services.interfaces import INotificationService

class NotificationService(INotificationService):
    """Service for managing notifications"""

    def __init__(self, game_state: GameState):
        """Initialize with game state dependency"""
        self.game_state = game_state

        # Initialize notifications list if not present
        if not hasattr(self.game_state, 'notifications'):
            self.game_state.notifications = []

        # Initialize config if not present
        if not hasattr(self.game_state, 'notification_config'):
            self.game_state.notification_config = NotificationConfig()

    def create_notification(self, data: NotificationCreate) -> Notification:
        """Create a new notification"""
        notification = Notification(
            title=data.title,
            message=data.message,
            type=data.type,
            source=data.source,
        )

        self.game_state.notifications.append(notification)
        return notification

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification by ID"""
        for notification in self.game_state.notifications:
            if notification.id == notification_id:
                return notification
        return None

    def list_notifications(
        self,
        filters: NotificationFilters
    ) -> List[Notification]:
        """List notifications with filters"""
        results = self.game_state.notifications

        # Apply filters
        if filters.type is not None:
            results = [n for n in results if n.type == filters.type]

        if filters.source is not None:
            results = [n for n in results if n.source == filters.source]

        if filters.read is not None:
            results = [n for n in results if n.read == filters.read]

        # Sort by created_at descending (newest first)
        results = sorted(results, key=lambda n: n.created_at, reverse=True)

        # Apply pagination
        start = filters.offset
        end = start + filters.limit
        return results[start:end]

    def update_notification(
        self,
        notification_id: str,
        data: NotificationUpdate
    ) -> Optional[Notification]:
        """Update a notification"""
        notification = self.get_notification(notification_id)
        if not notification:
            return None

        if data.read is not None:
            notification.read = data.read

        if data.dismissed is not None:
            notification.dismissed = data.dismissed

        return notification

    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification"""
        initial_length = len(self.game_state.notifications)
        self.game_state.notifications = [
            n for n in self.game_state.notifications
            if n.id != notification_id
        ]
        return len(self.game_state.notifications) < initial_length

    def clear_all_notifications(self) -> int:
        """Delete all notifications, returns count deleted"""
        count = len(self.game_state.notifications)
        self.game_state.notifications = []
        return count

    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        return sum(1 for n in self.game_state.notifications if not n.read)

    def get_config(self) -> NotificationConfig:
        """Get notification configuration"""
        return self.game_state.notification_config

    def update_config(self, config: NotificationConfig) -> NotificationConfig:
        """Update notification configuration"""
        self.game_state.notification_config = config
        return config
```

#### 4. FastAPI Routes (`main.py` additions)

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from recursive_neon.models.notification import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationConfig
)
from recursive_neon.services.interfaces import INotificationService
from recursive_neon.dependencies import ServiceContainer, get_container

notification_router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@notification_router.post("", response_model=Notification, status_code=201)
async def create_notification(
    data: NotificationCreate,
    container: ServiceContainer = Depends(get_container)
) -> Notification:
    """Create a new notification"""
    notification = container.notification_service.create_notification(data)

    # Broadcast via WebSocket
    await container.message_handler.broadcast({
        "type": "notification_created",
        "data": notification.model_dump(mode='json')
    })

    return notification

@notification_router.get("", response_model=List[Notification])
async def list_notifications(
    type: Optional[str] = None,
    source: Optional[str] = None,
    read: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    container: ServiceContainer = Depends(get_container)
) -> List[Notification]:
    """List notifications with optional filters"""
    filters = NotificationFilters(
        type=type,
        source=source,
        read=read,
        limit=limit,
        offset=offset
    )
    return container.notification_service.list_notifications(filters)

@notification_router.get("/unread-count", response_model=dict)
async def get_unread_count(
    container: ServiceContainer = Depends(get_container)
) -> dict:
    """Get unread notification count"""
    count = container.notification_service.get_unread_count()
    return {"count": count}

@notification_router.get("/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: str,
    container: ServiceContainer = Depends(get_container)
) -> Notification:
    """Get a specific notification"""
    notification = container.notification_service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@notification_router.patch("/{notification_id}", response_model=Notification)
async def update_notification(
    notification_id: str,
    data: NotificationUpdate,
    container: ServiceContainer = Depends(get_container)
) -> Notification:
    """Update a notification"""
    notification = container.notification_service.update_notification(
        notification_id,
        data
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Broadcast update via WebSocket
    await container.message_handler.broadcast({
        "type": "notification_updated",
        "data": notification.model_dump(mode='json')
    })

    return notification

@notification_router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    container: ServiceContainer = Depends(get_container)
) -> None:
    """Delete a notification"""
    success = container.notification_service.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Broadcast deletion via WebSocket
    await container.message_handler.broadcast({
        "type": "notification_deleted",
        "data": {"id": notification_id}
    })

@notification_router.delete("", response_model=dict)
async def clear_all_notifications(
    container: ServiceContainer = Depends(get_container)
) -> dict:
    """Clear all notifications"""
    count = container.notification_service.clear_all_notifications()

    # Broadcast clear via WebSocket
    await container.message_handler.broadcast({
        "type": "notifications_cleared",
        "data": {"count": count}
    })

    return {"deleted_count": count}

@notification_router.get("/config", response_model=NotificationConfig)
async def get_notification_config(
    container: ServiceContainer = Depends(get_container)
) -> NotificationConfig:
    """Get notification configuration"""
    return container.notification_service.get_config()

@notification_router.put("/config", response_model=NotificationConfig)
async def update_notification_config(
    config: NotificationConfig,
    container: ServiceContainer = Depends(get_container)
) -> NotificationConfig:
    """Update notification configuration"""
    updated_config = container.notification_service.update_config(config)

    # Broadcast config update via WebSocket
    await container.message_handler.broadcast({
        "type": "notification_config_updated",
        "data": updated_config.model_dump(mode='json')
    })

    return updated_config
```

### Frontend Components

#### 1. Notification Store (`stores/notificationStore.ts`)

```typescript
import { create } from 'zustand';

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

export interface Notification {
  id: string;
  title: string;
  message?: string;
  type: NotificationType;
  source: string;
  createdAt: string;
  read: boolean;
  dismissed: boolean;
}

export interface NotificationConfig {
  position: 'top-left' | 'top-right' | 'top-center' |
           'bottom-left' | 'bottom-right' | 'bottom-center';
  defaultDuration: number;
  maxVisible: number;
  soundEnabled: boolean;
}

export interface NotificationOptions {
  title: string;
  message?: string;
  type?: NotificationType;
  duration?: number;
  source?: string;
}

interface NotificationState {
  // State
  activeNotifications: Notification[];
  history: Notification[];
  unreadCount: number;
  config: NotificationConfig;

  // Actions
  createNotification: (options: NotificationOptions) => Promise<void>;
  dismissNotification: (id: string) => void;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
  loadHistory: () => Promise<void>;
  loadConfig: () => Promise<void>;
  updateConfig: (config: Partial<NotificationConfig>) => Promise<void>;

  // WebSocket handlers
  handleNotificationCreated: (notification: Notification) => void;
  handleNotificationUpdated: (notification: Notification) => void;
  handleNotificationDeleted: (id: string) => void;
  handleNotificationsCleared: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  // Initial state
  activeNotifications: [],
  history: [],
  unreadCount: 0,
  config: {
    position: 'top-right',
    defaultDuration: 5000,
    maxVisible: 5,
    soundEnabled: false,
  },

  // Create notification
  createNotification: async (options: NotificationOptions) => {
    const response = await fetch('http://localhost:8000/api/notifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: options.title,
        message: options.message,
        type: options.type || NotificationType.INFO,
        source: options.source || 'system',
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to create notification');
    }

    // Notification will be added via WebSocket event
  },

  // Dismiss notification (remove from active display)
  dismissNotification: (id: string) => {
    set(state => ({
      activeNotifications: state.activeNotifications.filter(n => n.id !== id),
    }));
  },

  // Mark notification as read
  markAsRead: async (id: string) => {
    const response = await fetch(
      `http://localhost:8000/api/notifications/${id}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: true }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to mark notification as read');
    }

    // Update will be handled via WebSocket event
  },

  // Mark all as read
  markAllAsRead: async () => {
    const { history } = get();
    const unreadIds = history.filter(n => !n.read).map(n => n.id);

    await Promise.all(
      unreadIds.map(id => get().markAsRead(id))
    );
  },

  // Delete notification
  deleteNotification: async (id: string) => {
    const response = await fetch(
      `http://localhost:8000/api/notifications/${id}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete notification');
    }

    // Deletion will be handled via WebSocket event
  },

  // Clear all notifications
  clearAll: async () => {
    const response = await fetch('http://localhost:8000/api/notifications', {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to clear notifications');
    }

    // Clear will be handled via WebSocket event
  },

  // Load notification history
  loadHistory: async () => {
    const response = await fetch('http://localhost:8000/api/notifications');
    if (!response.ok) {
      throw new Error('Failed to load notifications');
    }

    const notifications = await response.json();
    const unreadCount = notifications.filter((n: Notification) => !n.read).length;

    set({ history: notifications, unreadCount });
  },

  // Load configuration
  loadConfig: async () => {
    const response = await fetch(
      'http://localhost:8000/api/notifications/config'
    );
    if (!response.ok) {
      throw new Error('Failed to load config');
    }

    const config = await response.json();
    set({ config });
  },

  // Update configuration
  updateConfig: async (newConfig: Partial<NotificationConfig>) => {
    const { config } = get();
    const updatedConfig = { ...config, ...newConfig };

    const response = await fetch(
      'http://localhost:8000/api/notifications/config',
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to update config');
    }

    set({ config: updatedConfig });
  },

  // WebSocket event handlers
  handleNotificationCreated: (notification: Notification) => {
    set(state => {
      const newHistory = [notification, ...state.history];
      const newUnreadCount = state.unreadCount + 1;

      // Add to active notifications
      let newActive = [...state.activeNotifications, notification];

      // Respect maxVisible limit
      if (newActive.length > state.config.maxVisible) {
        newActive = newActive.slice(-state.config.maxVisible);
      }

      return {
        activeNotifications: newActive,
        history: newHistory,
        unreadCount: newUnreadCount,
      };
    });
  },

  handleNotificationUpdated: (notification: Notification) => {
    set(state => ({
      history: state.history.map(n =>
        n.id === notification.id ? notification : n
      ),
      unreadCount: state.history.filter(n => !n.read).length,
    }));
  },

  handleNotificationDeleted: (id: string) => {
    set(state => ({
      activeNotifications: state.activeNotifications.filter(n => n.id !== id),
      history: state.history.filter(n => n.id !== id),
      unreadCount: state.history.filter(n => !n.read && n.id !== id).length,
    }));
  },

  handleNotificationsCleared: () => {
    set({
      activeNotifications: [],
      history: [],
      unreadCount: 0,
    });
  },
}));
```

#### 2. NotificationToast Component (`components/NotificationToast.tsx`)

```typescript
import { useEffect, useState } from 'react';
import type { Notification, NotificationType } from '../stores/notificationStore';

interface NotificationToastProps {
  notification: Notification;
  duration?: number;
  onDismiss: (id: string) => void;
  onRead: (id: string) => void;
}

export function NotificationToast({
  notification,
  duration = 5000,
  onDismiss,
  onRead,
}: NotificationToastProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (duration === 0 || isPaused) return;

    const timer = setTimeout(() => {
      handleDismiss();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, isPaused]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss(notification.id);
      if (!notification.read) {
        onRead(notification.id);
      }
    }, 200); // Match exit animation duration
  };

  const getIcon = (type: NotificationType): string => {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    return icons[type];
  };

  return (
    <div
      className={`notification-toast notification-${notification.type} ${
        isExiting ? 'exiting' : ''
      }`}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="notification-icon">{getIcon(notification.type)}</div>
      <div className="notification-content">
        <div className="notification-title">{notification.title}</div>
        {notification.message && (
          <div className="notification-message">{notification.message}</div>
        )}
        <div className="notification-time">
          {new Date(notification.createdAt).toLocaleTimeString()}
        </div>
      </div>
      <button
        className="notification-close"
        onClick={handleDismiss}
        aria-label="Dismiss notification"
      >
        ×
      </button>
    </div>
  );
}
```

#### 3. NotificationContainer Component (`components/NotificationContainer.tsx`)

```typescript
import { useNotificationStore } from '../stores/notificationStore';
import { NotificationToast } from './NotificationToast';

export function NotificationContainer() {
  const { activeNotifications, config, dismissNotification, markAsRead } =
    useNotificationStore();

  const getPositionClass = () => {
    return `notification-container-${config.position}`;
  };

  return (
    <div className={`notification-container ${getPositionClass()}`}>
      {activeNotifications.map(notification => (
        <NotificationToast
          key={notification.id}
          notification={notification}
          duration={config.defaultDuration}
          onDismiss={dismissNotification}
          onRead={markAsRead}
        />
      ))}
    </div>
  );
}
```

#### 4. NotificationCenter App (`components/apps/NotificationCenterApp.tsx`)

```typescript
import { useState, useEffect } from 'react';
import { useNotificationStore, NotificationType } from '../../stores/notificationStore';
import type { Notification } from '../../stores/notificationStore';

export function NotificationCenterApp() {
  const {
    history,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    loadHistory,
  } = useNotificationStore();

  const [filter, setFilter] = useState<'all' | NotificationType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredNotifications = history.filter(notification => {
    // Apply type filter
    if (filter !== 'all' && notification.type !== filter) {
      return false;
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        notification.title.toLowerCase().includes(query) ||
        notification.message?.toLowerCase().includes(query)
      );
    }

    return true;
  });

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  return (
    <div className="notification-center-app">
      <div className="notification-center-header">
        <h2>Notifications ({unreadCount} unread)</h2>
        <div className="notification-center-actions">
          <button onClick={markAllAsRead}>Mark All Read</button>
          <button onClick={clearAll}>Clear All</button>
        </div>
      </div>

      <div className="notification-center-filters">
        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === NotificationType.INFO ? 'active' : ''}
            onClick={() => setFilter(NotificationType.INFO)}
          >
            Info
          </button>
          <button
            className={filter === NotificationType.SUCCESS ? 'active' : ''}
            onClick={() => setFilter(NotificationType.SUCCESS)}
          >
            Success
          </button>
          <button
            className={filter === NotificationType.WARNING ? 'active' : ''}
            onClick={() => setFilter(NotificationType.WARNING)}
          >
            Warning
          </button>
          <button
            className={filter === NotificationType.ERROR ? 'active' : ''}
            onClick={() => setFilter(NotificationType.ERROR)}
          >
            Error
          </button>
        </div>

        <input
          type="text"
          placeholder="Search notifications..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="notification-search"
        />
      </div>

      <div className="notification-center-list">
        {filteredNotifications.length === 0 ? (
          <div className="notification-center-empty">
            No notifications found
          </div>
        ) : (
          filteredNotifications.map(notification => (
            <div
              key={notification.id}
              className={`notification-item notification-item-${notification.type} ${
                !notification.read ? 'unread' : ''
              }`}
              onClick={() => handleNotificationClick(notification)}
            >
              <div className="notification-item-header">
                <span className={`notification-dot ${!notification.read ? 'active' : ''}`}>
                  ●
                </span>
                <span className="notification-item-title">
                  {notification.title}
                </span>
                <span className="notification-item-time">
                  {new Date(notification.createdAt).toLocaleString()}
                </span>
              </div>
              {notification.message && (
                <div className="notification-item-message">
                  {notification.message}
                </div>
              )}
              <div className="notification-item-meta">
                <span className="notification-item-source">
                  {notification.source}
                </span>
                <button
                  className="notification-item-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteNotification(notification.id);
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

#### 5. Notification Indicator (`components/NotificationIndicator.tsx`)

```typescript
import { useNotificationStore } from '../stores/notificationStore';
import { useGameStore } from '../stores/gameStore';
import { NotificationCenterApp } from './apps/NotificationCenterApp';

export function NotificationIndicator() {
  const { unreadCount } = useNotificationStore();
  const { openWindow } = useGameStore();

  const handleClick = () => {
    openWindow({
      title: 'Notifications',
      type: 'notification-center',
      content: <NotificationCenterApp />,
      size: { width: 600, height: 500 },
      position: { x: 100, y: 100 },
    });
  };

  return (
    <button className="notification-indicator" onClick={handleClick}>
      <span className="notification-bell">🔔</span>
      {unreadCount > 0 && (
        <span className="notification-badge">{unreadCount}</span>
      )}
    </button>
  );
}
```

---

## Data Flow

### Creating a Notification

```
App Component
    ↓ (calls)
notificationStore.createNotification({ title: "...", ... })
    ↓ (HTTP POST)
Backend: POST /api/notifications
    ↓
NotificationService.create_notification()
    ↓
GameState.notifications.append(notification)
    ↓ (broadcasts via WebSocket)
All Connected Clients
    ↓
notificationStore.handleNotificationCreated(notification)
    ↓
activeNotifications updated → UI re-renders
    ↓
NotificationToast appears on screen
    ↓ (after duration)
Auto-dismiss → markAsRead() → PATCH /api/notifications/{id}
```

### Viewing Notification History

```
User clicks Notification Center icon
    ↓
NotificationIndicator.handleClick()
    ↓
gameStore.openWindow({ content: <NotificationCenterApp /> })
    ↓
NotificationCenterApp mounts
    ↓
useEffect → loadHistory()
    ↓ (HTTP GET)
Backend: GET /api/notifications
    ↓
NotificationService.list_notifications()
    ↓
Returns notifications from GameState
    ↓
notificationStore.history updated
    ↓
NotificationCenterApp renders list
```

---

## API Specification

See Component Design section for detailed API specifications.

**Key Endpoints**:
- `POST /api/notifications` - Create notification
- `GET /api/notifications` - List with filters
- `GET /api/notifications/{id}` - Get one
- `PATCH /api/notifications/{id}` - Update
- `DELETE /api/notifications/{id}` - Delete one
- `DELETE /api/notifications` - Clear all
- `GET /api/notifications/unread-count` - Unread count
- `GET /api/notifications/config` - Get config
- `PUT /api/notifications/config` - Update config

**WebSocket Events**:
- `notification_created` - New notification
- `notification_updated` - Notification changed
- `notification_deleted` - Notification removed
- `notifications_cleared` - All cleared
- `notification_config_updated` - Config changed

---

## State Management

### Backend State (GameState)

```python
class GameState(BaseModel):
    # ... existing fields
    notifications: List[Notification] = Field(default_factory=list)
    notification_config: NotificationConfig = Field(
        default_factory=NotificationConfig
    )
```

### Frontend State (Zustand)

```typescript
interface NotificationState {
  activeNotifications: Notification[];  // Currently displayed toasts
  history: Notification[];              // All notifications
  unreadCount: number;                  // Badge count
  config: NotificationConfig;           // Display settings
  // ... actions
}
```

---

## UI/UX Design

### Toast Notification Styling

- **Position**: Configurable corner/edge
- **Size**: Min 300px wide, auto height
- **Spacing**: 12px between toasts
- **Animation**: Slide + fade (300ms)
- **Colors**:
  - Info: Blue (#0EA5E9)
  - Success: Green (#22C55E)
  - Warning: Orange (#F59E0B)
  - Error: Red (#EF4444)

### Notification Center Styling

- **Layout**: Header, filters, scrollable list
- **Colors**: Match desktop theme
- **Typography**: Clear hierarchy
- **Interactions**: Hover states, click handlers

---

## Implementation Plan

See main TODO list for implementation steps.

---

## Testing Strategy

### Backend Tests

1. **Unit Tests** (`tests/unit/test_notification_service.py`):
   - Test each service method
   - Test validation
   - Test filters
   - Test edge cases

2. **Integration Tests** (`tests/integration/test_notification_api.py`):
   - Test HTTP endpoints
   - Test WebSocket events
   - Test persistence
   - Test concurrent access

### Frontend Tests

1. **Unit Tests**:
   - `notificationStore.test.ts` - Store logic
   - `NotificationToast.test.tsx` - Component rendering
   - `NotificationCenter.test.tsx` - App functionality

2. **Integration Tests**:
   - WebSocket integration
   - API integration
   - User workflows

---

*This design document provides the technical blueprint for implementing the RecursiveNeon notification system.*
