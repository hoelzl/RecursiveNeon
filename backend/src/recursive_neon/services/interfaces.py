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
from recursive_neon.models.app_models import (
    Note,
    Task,
    TaskList,
    FileNode,
    BrowserPage,
    MediaViewerConfig,
    TextMessage,
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


# ============================================================================
# App Service Interface
# ============================================================================

class IAppService(ABC):
    """
    Abstract interface for desktop application services.

    This interface defines the contract for managing in-game desktop app data:
    - Notes (note-taking application)
    - Tasks and TaskLists (task management)
    - FileSystem (virtual file browser)
    - Browser pages and bookmarks
    - Media Viewer configuration

    Note: This is a large interface that could be split into smaller
    domain-specific interfaces (INotesService, ITaskService, IFileSystemService,
    IBrowserService, IMediaViewerService) in a future refactoring.
    """

    # ============================================================================
    # Notes Operations
    # ============================================================================

    @abstractmethod
    def get_notes(self) -> List[Note]:
        """
        Get all notes.

        Returns:
            List of all notes
        """
        pass

    @abstractmethod
    def get_note(self, note_id: str) -> Note:
        """
        Get a specific note by ID.

        Args:
            note_id: ID of the note to retrieve

        Returns:
            The note

        Raises:
            ValueError: If note not found
        """
        pass

    @abstractmethod
    def create_note(self, data: Dict[str, Any]) -> Note:
        """
        Create a new note.

        Args:
            data: Note data (title, content)

        Returns:
            The created note
        """
        pass

    @abstractmethod
    def update_note(self, note_id: str, data: Dict[str, Any]) -> Note:
        """
        Update an existing note.

        Args:
            note_id: ID of the note to update
            data: Updated note data

        Returns:
            The updated note

        Raises:
            ValueError: If note not found
        """
        pass

    @abstractmethod
    def delete_note(self, note_id: str) -> None:
        """
        Delete a note.

        Args:
            note_id: ID of the note to delete
        """
        pass

    # ============================================================================
    # Task Operations
    # ============================================================================

    @abstractmethod
    def get_task_lists(self) -> List[TaskList]:
        """
        Get all task lists.

        Returns:
            List of all task lists
        """
        pass

    @abstractmethod
    def get_task_list(self, list_id: str) -> TaskList:
        """
        Get a specific task list by ID.

        Args:
            list_id: ID of the task list

        Returns:
            The task list

        Raises:
            ValueError: If task list not found
        """
        pass

    @abstractmethod
    def create_task_list(self, data: Dict[str, Any]) -> TaskList:
        """
        Create a new task list.

        Args:
            data: Task list data (name)

        Returns:
            The created task list
        """
        pass

    @abstractmethod
    def update_task_list(self, list_id: str, data: Dict[str, Any]) -> TaskList:
        """
        Update a task list.

        Args:
            list_id: ID of the task list
            data: Updated data

        Returns:
            The updated task list

        Raises:
            ValueError: If task list not found
        """
        pass

    @abstractmethod
    def delete_task_list(self, list_id: str) -> None:
        """
        Delete a task list.

        Args:
            list_id: ID of the task list to delete
        """
        pass

    @abstractmethod
    def create_task(self, list_id: str, data: Dict[str, Any]) -> Task:
        """
        Create a new task in a list.

        Args:
            list_id: ID of the task list
            data: Task data (title, completed, parent_id)

        Returns:
            The created task
        """
        pass

    @abstractmethod
    def update_task(self, list_id: str, task_id: str, data: Dict[str, Any]) -> Task:
        """
        Update a task.

        Args:
            list_id: ID of the task list
            task_id: ID of the task
            data: Updated task data

        Returns:
            The updated task

        Raises:
            ValueError: If task not found
        """
        pass

    @abstractmethod
    def delete_task(self, list_id: str, task_id: str) -> None:
        """
        Delete a task.

        Args:
            list_id: ID of the task list
            task_id: ID of the task to delete
        """
        pass

    # ============================================================================
    # FileSystem Operations
    # ============================================================================

    @abstractmethod
    def init_filesystem(self) -> FileNode:
        """
        Initialize the filesystem with a root directory.

        Returns:
            The root directory node
        """
        pass

    @abstractmethod
    def get_file(self, file_id: str) -> FileNode:
        """
        Get a file or directory by ID.

        Args:
            file_id: ID of the file/directory

        Returns:
            The file node

        Raises:
            ValueError: If file not found
        """
        pass

    @abstractmethod
    def create_directory(self, data: Dict[str, Any]) -> FileNode:
        """
        Create a new directory.

        Args:
            data: Directory data (name, parent_id)

        Returns:
            The created directory node
        """
        pass

    @abstractmethod
    def create_file(self, data: Dict[str, Any]) -> FileNode:
        """
        Create a new file.

        Args:
            data: File data (name, parent_id, content, mime_type)

        Returns:
            The created file node
        """
        pass

    @abstractmethod
    def update_file(self, file_id: str, data: Dict[str, Any]) -> FileNode:
        """
        Update a file.

        Args:
            file_id: ID of the file
            data: Updated file data

        Returns:
            The updated file node

        Raises:
            ValueError: If file not found
        """
        pass

    @abstractmethod
    def delete_file(self, file_id: str) -> None:
        """
        Delete a file or directory.

        Args:
            file_id: ID of the file/directory to delete
        """
        pass

    @abstractmethod
    def copy_file(
        self,
        file_id: str,
        target_parent_id: str,
        new_name: Optional[str] = None
    ) -> FileNode:
        """
        Copy a file or directory.

        Args:
            file_id: ID of the file/directory to copy
            target_parent_id: ID of destination parent
            new_name: Optional new name for the copy

        Returns:
            The created copy
        """
        pass

    @abstractmethod
    def move_file(self, file_id: str, target_parent_id: str) -> FileNode:
        """
        Move a file or directory.

        Args:
            file_id: ID of the file/directory to move
            target_parent_id: ID of destination parent

        Returns:
            The updated file node

        Raises:
            ValueError: If trying to move a directory into itself
        """
        pass

    @abstractmethod
    def list_directory(self, dir_id: str) -> List[FileNode]:
        """
        List contents of a directory.

        Args:
            dir_id: ID of the directory

        Returns:
            List of file nodes in the directory
        """
        pass

    @abstractmethod
    def save_filesystem_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """
        Save filesystem state to disk.

        Args:
            data_dir: Directory to save to
        """
        pass

    @abstractmethod
    def load_filesystem_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """
        Load filesystem state from disk.

        Args:
            data_dir: Directory to load from

        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        pass

    @abstractmethod
    def load_initial_filesystem(self, initial_fs_dir: str = "backend/initial_fs") -> None:
        """
        Load initial filesystem from a source directory.

        Args:
            initial_fs_dir: Directory containing initial file structure
        """
        pass

    # ============================================================================
    # Browser Operations
    # ============================================================================

    @abstractmethod
    def get_browser_pages(self) -> List[BrowserPage]:
        """
        Get all browser pages.

        Returns:
            List of browser pages
        """
        pass

    @abstractmethod
    def get_browser_page_by_url(self, url: str) -> Optional[BrowserPage]:
        """
        Get a browser page by URL.

        Args:
            url: Page URL

        Returns:
            The browser page, or None if not found
        """
        pass

    @abstractmethod
    def create_browser_page(self, data: Dict[str, Any]) -> BrowserPage:
        """
        Create a new browser page.

        Args:
            data: Page data (url, title, content)

        Returns:
            The created page
        """
        pass

    @abstractmethod
    def get_bookmarks(self) -> List[str]:
        """
        Get all bookmarks.

        Returns:
            List of bookmarked URLs
        """
        pass

    @abstractmethod
    def add_bookmark(self, url: str) -> None:
        """
        Add a bookmark.

        Args:
            url: URL to bookmark
        """
        pass

    @abstractmethod
    def remove_bookmark(self, url: str) -> None:
        """
        Remove a bookmark.

        Args:
            url: URL to remove from bookmarks
        """
        pass

    # ============================================================================
    # Media Viewer Operations
    # ============================================================================

    @abstractmethod
    def get_media_viewer_config(self) -> MediaViewerConfig:
        """
        Get media viewer configuration.

        Returns:
            Current media viewer config
        """
        pass

    @abstractmethod
    def update_media_viewer_config(self, data: Dict[str, Any]) -> MediaViewerConfig:
        """
        Update media viewer configuration.

        Args:
            data: Configuration data

        Returns:
            Updated configuration
        """
        pass

    @abstractmethod
    def add_media_viewer_message(self, message_data: Dict[str, Any]) -> TextMessage:
        """
        Add a text message to the media viewer sequence.

        Args:
            message_data: Message data

        Returns:
            The created message
        """
        pass

    @abstractmethod
    def set_media_viewer_style(self, style: str) -> MediaViewerConfig:
        """
        Set the media viewer spiral style.

        Args:
            style: Spiral style ("blackwhite" or "colorful")

        Returns:
            Updated configuration
        """
        pass

    @abstractmethod
    def initialize_default_media_viewer_messages(self) -> None:
        """
        Initialize media viewer with default messages.
        """
        pass
