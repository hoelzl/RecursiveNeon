"""Notification service implementation.

This module provides the NotificationService class, which manages the creation,
retrieval, updating, and deletion of notifications in the game. Notifications
are stored in the GameState and persisted to disk.

The service follows the dependency injection pattern and implements the
INotificationService interface for testability.
"""

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
    """Service for managing notifications.

    This service provides methods for creating, retrieving, updating, and
    deleting notifications. Notifications are stored in the GameState and
    persisted automatically.

    Attributes:
        game_state: Reference to the global game state
    """

    def __init__(self, game_state: GameState):
        """Initialize notification service with game state dependency.

        Args:
            game_state: The game state instance to use for storage
        """
        self.game_state = game_state

        # Initialize notifications list if not present (for backwards compatibility)
        if not hasattr(self.game_state, 'notifications'):
            self.game_state.notifications = []

        # Initialize config if not present (for backwards compatibility)
        if not hasattr(self.game_state, 'notification_config'):
            self.game_state.notification_config = NotificationConfig()

    def create_notification(self, data: NotificationCreate) -> Notification:
        """Create a new notification.

        Creates a notification with the provided data and adds it to the
        game state. The notification ID and timestamp are generated automatically.

        Args:
            data: Notification creation data

        Returns:
            The created Notification instance

        Example:
            >>> service.create_notification(NotificationCreate(
            ...     title="Task Complete",
            ...     message="Your backup has finished",
            ...     type=NotificationType.SUCCESS,
            ...     source="task-list"
            ... ))
        """
        notification = Notification(
            title=data.title,
            message=data.message,
            type=data.type,
            source=data.source,
        )

        self.game_state.notifications.append(notification)
        return notification

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification by ID.

        Args:
            notification_id: The UUID of the notification to retrieve

        Returns:
            The Notification if found, None otherwise

        Example:
            >>> notification = service.get_notification("550e8400-...")
        """
        for notification in self.game_state.notifications:
            if notification.id == notification_id:
                return notification
        return None

    def list_notifications(
        self,
        filters: NotificationFilters
    ) -> List[Notification]:
        """List notifications with optional filters.

        Retrieves notifications from the game state and applies the provided
        filters. Results are sorted by creation time (newest first) and
        paginated according to the filter limits.

        Args:
            filters: Filters to apply (type, source, read status, pagination)

        Returns:
            List of notifications matching the filters

        Example:
            >>> # Get unread info notifications
            >>> filters = NotificationFilters(
            ...     type=NotificationType.INFO,
            ...     read=False,
            ...     limit=50
            ... )
            >>> notifications = service.list_notifications(filters)
        """
        results = self.game_state.notifications

        # Apply type filter
        if filters.type is not None:
            results = [n for n in results if n.type == filters.type]

        # Apply source filter
        if filters.source is not None:
            results = [n for n in results if n.source == filters.source]

        # Apply read status filter
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
        """Update a notification.

        Updates the read and/or dismissed status of a notification.

        Args:
            notification_id: ID of the notification to update
            data: Update data (read and/or dismissed status)

        Returns:
            The updated Notification if found, None otherwise

        Example:
            >>> # Mark notification as read
            >>> service.update_notification(
            ...     "550e8400-...",
            ...     NotificationUpdate(read=True)
            ... )
        """
        notification = self.get_notification(notification_id)
        if not notification:
            return None

        # Update fields if provided
        if data.read is not None:
            notification.read = data.read

        if data.dismissed is not None:
            notification.dismissed = data.dismissed

        return notification

    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification.

        Removes a notification from the game state.

        Args:
            notification_id: ID of the notification to delete

        Returns:
            True if the notification was deleted, False if not found

        Example:
            >>> service.delete_notification("550e8400-...")
            True
        """
        initial_length = len(self.game_state.notifications)
        self.game_state.notifications = [
            n for n in self.game_state.notifications
            if n.id != notification_id
        ]
        return len(self.game_state.notifications) < initial_length

    def clear_all_notifications(self) -> int:
        """Delete all notifications.

        Removes all notifications from the game state.

        Returns:
            Number of notifications that were deleted

        Example:
            >>> count = service.clear_all_notifications()
            >>> print(f"Deleted {count} notifications")
        """
        count = len(self.game_state.notifications)
        self.game_state.notifications = []
        return count

    def get_unread_count(self) -> int:
        """Get count of unread notifications.

        Counts all notifications where read=False.

        Returns:
            Number of unread notifications

        Example:
            >>> unread = service.get_unread_count()
            >>> print(f"You have {unread} unread notifications")
        """
        return sum(1 for n in self.game_state.notifications if not n.read)

    def get_config(self) -> NotificationConfig:
        """Get notification configuration.

        Retrieves the current notification display configuration.

        Returns:
            Current notification configuration

        Example:
            >>> config = service.get_config()
            >>> print(f"Position: {config.position}")
        """
        return self.game_state.notification_config

    def update_config(self, config: NotificationConfig) -> NotificationConfig:
        """Update notification configuration.

        Updates the notification display configuration.

        Args:
            config: New configuration to apply

        Returns:
            The updated configuration

        Example:
            >>> new_config = NotificationConfig(
            ...     position="bottom-right",
            ...     default_duration=3000
            ... )
            >>> service.update_config(new_config)
        """
        self.game_state.notification_config = config
        return config
