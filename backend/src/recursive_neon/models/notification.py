"""Notification models for the notification system.

This module defines the data models for notifications, including:
- Notification types (info, success, warning, error)
- Core notification model with validation
- Request/response models for API
- Configuration model for notification display settings
- Filter model for querying notifications
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class NotificationType(str, Enum):
    """Types of notifications with different visual styles and semantics."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(BaseModel):
    """Core notification model.

    Represents a single notification in the system. Notifications are created
    by applications to inform users of events, status changes, or errors.

    Attributes:
        id: Unique identifier (UUID)
        title: Notification title (max 100 characters)
        message: Optional longer message (max 500 characters)
        type: Notification type (info, success, warning, error)
        source: Identifier of the application that created the notification
        created_at: Timestamp when notification was created
        read: Whether the user has read/acknowledged the notification
        dismissed: Whether the notification has been dismissed from display
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=100)
    message: Optional[str] = Field(None, max_length=500)
    type: NotificationType = NotificationType.INFO
    source: str = Field(..., min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    read: bool = False
    dismissed: bool = False

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Task Complete",
                "message": "Your file has been saved successfully",
                "type": "success",
                "source": "file-browser",
                "created_at": "2025-11-15T12:30:00Z",
                "read": False,
                "dismissed": False,
            }
        }


class NotificationCreate(BaseModel):
    """Request model for creating notifications.

    This is the data structure apps use to create new notifications.
    The ID and created_at fields are auto-generated.

    Attributes:
        title: Notification title (required, max 100 characters)
        message: Optional longer message (max 500 characters)
        type: Notification type (default: INFO)
        source: Identifier of the creating application (required)
        duration: Optional display duration in milliseconds (not persisted)
    """

    title: str = Field(..., min_length=1, max_length=100)
    message: Optional[str] = Field(None, max_length=500)
    type: NotificationType = NotificationType.INFO
    source: str = Field(..., min_length=1, max_length=50)
    duration: Optional[int] = Field(None, ge=0, le=60000)  # Not stored, for client

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "title": "Task Complete",
                "message": "Your backup has finished",
                "type": "success",
                "source": "task-list",
                "duration": 5000,
            }
        }


class NotificationUpdate(BaseModel):
    """Request model for updating notifications.

    Used to update notification state (read/dismissed status).

    Attributes:
        read: Mark notification as read/unread
        dismissed: Mark notification as dismissed
    """

    read: Optional[bool] = None
    dismissed: Optional[bool] = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "read": True,
                "dismissed": False,
            }
        }


class NotificationConfig(BaseModel):
    """Configuration for notification display behavior.

    Controls how notifications are displayed to the user.

    Attributes:
        position: Where notifications appear on screen
        default_duration: Default auto-dismiss time in milliseconds
        max_visible: Maximum number of simultaneously visible notifications
        sound_enabled: Whether to play sounds for notifications
    """

    position: str = "top-right"
    default_duration: int = 5000  # milliseconds
    max_visible: int = 5
    sound_enabled: bool = False

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "position": "top-right",
                "default_duration": 5000,
                "max_visible": 5,
                "sound_enabled": False,
            }
        }


class NotificationFilters(BaseModel):
    """Filters for querying notifications.

    Used to filter and paginate notification queries.

    Attributes:
        type: Filter by notification type
        source: Filter by source application
        read: Filter by read status
        limit: Maximum number of results (default 100, max 1000)
        offset: Number of results to skip for pagination
    """

    type: Optional[NotificationType] = None
    source: Optional[str] = None
    read: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "type": "info",
                "source": "chat",
                "read": False,
                "limit": 50,
                "offset": 0,
            }
        }
