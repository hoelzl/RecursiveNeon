"""
Service Interfaces for Dependency Injection

This module defines abstract interfaces (protocols) for all backend services.
These interfaces enable:
- Dependency injection
- Mocking in tests
- Loose coupling between components
- Clear service contracts
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator, Protocol, Callable
from dataclasses import dataclass

from recursive_neon.models.npc import NPC, ChatResponse
from recursive_neon.models.calendar import CalendarEvent, CreateEventRequest
from recursive_neon.models.notification import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters,
    NotificationConfig
)


# ============================================================================
# LLM Interface (for LangChain compatibility)
# ============================================================================

class LLMInterface(Protocol):
    """
    Protocol for Language Model providers.

    This interface matches the LangChain LLM interface, allowing us to
    inject different LLM implementations (real or mock) into NPCManager.
    """

    def invoke(self, messages: Any) -> Any:
        """Synchronously invoke the LLM"""
        ...

    async def ainvoke(self, messages: Any) -> Any:
        """Asynchronously invoke the LLM"""
        ...


# ============================================================================
# NPC Manager Interface
# ============================================================================

class INPCManager(ABC):
    """
    Abstract interface for NPC management.

    Defines the contract for managing NPCs and their conversations.
    """

    @abstractmethod
    def register_npc(self, npc: NPC) -> None:
        """
        Register a new NPC.

        Args:
            npc: The NPC instance to register
        """
        pass

    @abstractmethod
    def unregister_npc(self, npc_id: str) -> None:
        """
        Unregister an NPC.

        Args:
            npc_id: ID of the NPC to unregister
        """
        pass

    @abstractmethod
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """
        Get an NPC by ID.

        Args:
            npc_id: ID of the NPC to retrieve

        Returns:
            The NPC instance if found, None otherwise
        """
        pass

    @abstractmethod
    def list_npcs(self) -> List[NPC]:
        """
        List all registered NPCs.

        Returns:
            List of all NPC instances
        """
        pass

    @abstractmethod
    async def chat(
        self,
        npc_id: str,
        message: str,
        player_id: str = "player_1"
    ) -> ChatResponse:
        """
        Send a chat message to an NPC and get a response.

        Args:
            npc_id: ID of the NPC to chat with
            message: The message to send
            player_id: ID of the player sending the message

        Returns:
            The NPC's response
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about NPC interactions.

        Returns:
            Dictionary containing stats
        """
        pass


# ============================================================================
# Ollama Client Interface
# ============================================================================

class IOllamaClient(ABC):
    """
    Abstract interface for Ollama HTTP client.

    Defines the contract for communicating with the Ollama server.
    """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if Ollama server is healthy.

        Returns:
            True if server is responding, False otherwise
        """
        pass

    @abstractmethod
    async def wait_for_ready(
        self,
        max_wait: int = 30,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for Ollama server to become ready.

        Args:
            max_wait: Maximum seconds to wait
            check_interval: Seconds between health checks

        Returns:
            True if server became ready, False if timeout
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models on the Ollama server.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any
    ) -> Any:
        """
        Generate text using a model.

        Args:
            model: Name of the model to use
            prompt: The prompt text
            **kwargs: Additional generation parameters

        Returns:
            Generation response
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        pass


# ============================================================================
# Process Manager Interface
# ============================================================================

class IProcessManager(ABC):
    """
    Abstract interface for Ollama process management.

    Defines the contract for managing the Ollama server process lifecycle.
    """

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the Ollama server process.

        Returns:
            True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop(self, timeout: int = 10) -> bool:
        """
        Stop the Ollama server process.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the Ollama server process is running.

        Returns:
            True if process is running, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information about the process.

        Returns:
            Dictionary containing process status
        """
        pass


# ============================================================================
# Calendar Service Interface
# ============================================================================

class ICalendarService(ABC):
    """
    Abstract interface for calendar event management.

    Defines the contract for managing calendar events in the game.
    """

    @abstractmethod
    def create_event(self, event_data: CreateEventRequest) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            event_data: Event data to create

        Returns:
            The created CalendarEvent
        """
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """
        Get a specific event by ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            The event if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all_events(self) -> List[CalendarEvent]:
        """
        Get all calendar events.

        Returns:
            List of all events
        """
        pass

    @abstractmethod
    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CalendarEvent]:
        """
        Get events within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of events in range
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event.

        Args:
            event_id: ID of event to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def save_to_disk(self, file_path: str) -> None:
        """
        Save calendar events to disk.

        Args:
            file_path: Path to save calendar data
        """
        pass

    @abstractmethod
    def load_from_disk(self, file_path: str) -> None:
        """
        Load calendar events from disk.

        Args:
            file_path: Path to load calendar data from
        """
        pass


# ============================================================================
# Notification Service Interface
# ============================================================================

class INotificationService(ABC):
    """
    Abstract interface for notification management.

    Defines the contract for creating, retrieving, updating, and managing
    notifications in the game.
    """

    @abstractmethod
    def create_notification(self, data: NotificationCreate) -> Notification:
        """
        Create a new notification.

        Args:
            data: Notification creation data

        Returns:
            The created Notification
        """
        pass

    @abstractmethod
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a specific notification by ID.

        Args:
            notification_id: ID of the notification to retrieve

        Returns:
            The notification if found, None otherwise
        """
        pass

    @abstractmethod
    def list_notifications(
        self,
        filters: NotificationFilters
    ) -> List[Notification]:
        """
        List notifications with optional filters.

        Args:
            filters: Filters to apply to the query

        Returns:
            List of notifications matching filters
        """
        pass

    @abstractmethod
    def update_notification(
        self,
        notification_id: str,
        data: NotificationUpdate
    ) -> Optional[Notification]:
        """
        Update a notification.

        Args:
            notification_id: ID of notification to update
            data: Update data

        Returns:
            The updated notification if found, None otherwise
        """
        pass

    @abstractmethod
    def delete_notification(self, notification_id: str) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: ID of notification to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def clear_all_notifications(self) -> int:
        """
        Delete all notifications.

        Returns:
            Number of notifications deleted
        """
        pass

    @abstractmethod
    def get_unread_count(self) -> int:
        """
        Get count of unread notifications.

        Returns:
            Number of unread notifications
        """
        pass

    @abstractmethod
    def get_config(self) -> NotificationConfig:
        """
        Get notification configuration.

        Returns:
            Current notification configuration
        """
        pass

    @abstractmethod
    def update_config(self, config: NotificationConfig) -> NotificationConfig:
        """
        Update notification configuration.

        Args:
            config: New configuration

        Returns:
            Updated configuration
        """
        pass


# ============================================================================
# Time Service Interface
# ============================================================================

class ITimeService(ABC):
    """
    Abstract interface for game time management.

    Defines the contract for managing game time independently from OS time,
    including time dilation and manual time manipulation.
    """

    @abstractmethod
    def get_current_time(self) -> datetime:
        """
        Get the current game time.

        Returns:
            Current game time as datetime
        """
        pass

    @abstractmethod
    def get_time_state(self) -> Dict[str, Any]:
        """
        Get complete time state including dilation and pause status.

        Returns:
            Dictionary containing time state information
        """
        pass

    @abstractmethod
    def set_time_dilation(self, dilation: float) -> None:
        """
        Set time dilation factor.

        Args:
            dilation: Time dilation factor (0.0 = paused, 1.0 = real-time, etc.)

        Raises:
            ValueError: If dilation is negative
        """
        pass

    @abstractmethod
    def get_time_dilation(self) -> float:
        """
        Get current time dilation factor.

        Returns:
            Current time dilation factor
        """
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
        """
        Check if time is currently paused.

        Returns:
            True if paused, False otherwise
        """
        pass

    @abstractmethod
    def jump_to(self, target_time: datetime) -> None:
        """
        Jump to a specific time.

        Args:
            target_time: Target datetime to jump to
        """
        pass

    @abstractmethod
    def advance(self, duration: timedelta) -> None:
        """
        Advance time by a specific duration.

        Args:
            duration: Duration to advance time by
        """
        pass

    @abstractmethod
    def rewind(self, duration: timedelta) -> None:
        """
        Rewind time by a specific duration.

        Args:
            duration: Duration to rewind time by
        """
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

    @abstractmethod
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to time change events.

        Args:
            callback: Function to call when time state changes
        """
        pass


# ============================================================================
# Settings Service Interface
# ============================================================================

class ISettingsService(ABC):
    """
    Abstract interface for settings management.

    Defines the contract for managing application settings with persistence.
    """

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key

        Returns:
            Setting value

        Raises:
            KeyError: If setting not found
        """
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.

        Returns:
            Dictionary of all settings
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: New value

        Raises:
            ValueError: If value is invalid
        """
        pass

    @abstractmethod
    def set_many(self, settings: Dict[str, Any]) -> None:
        """
        Set multiple settings at once.

        Args:
            settings: Dictionary of settings to update

        Raises:
            ValueError: If any value is invalid
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """
        Reset a setting to its default value.

        Args:
            key: Setting key to reset

        Raises:
            KeyError: If setting has no default
        """
        pass

    @abstractmethod
    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        pass

    @abstractmethod
    def get_default(self, key: str) -> Any:
        """
        Get the default value for a setting.

        Args:
            key: Setting key

        Returns:
            Default value

        Raises:
            KeyError: If setting has no default
        """
        pass

    @abstractmethod
    def register_default(
        self,
        key: str,
        default_value: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: Optional[str] = None
    ) -> None:
        """
        Register a default value and optional validator.

        Args:
            key: Setting key
            default_value: Default value
            validator: Optional validation function
            description: Optional description
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """Save settings to disk."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load settings from disk."""
        pass

    @abstractmethod
    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to setting changes.

        Args:
            callback: Function to call when settings change (receives key, value)
        """
        pass
