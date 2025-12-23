"""
Desktop App Service

Manages state for desktop applications using composition of smaller services.
This is the main facade that delegates to specialized domain services.
"""
from typing import List, Dict, Any, Optional

from recursive_neon.models.game_state import GameState
from recursive_neon.models.app_models import (
    Note,
    Task,
    TaskList,
    FileNode,
    BrowserPage,
    MediaViewerConfig,
    TextMessage,
)
from recursive_neon.services.interfaces import IAppService
from recursive_neon.services.notes_service import NotesService
from recursive_neon.services.task_service import TaskService
from recursive_neon.services.filesystem_service import FileSystemService
from recursive_neon.services.browser_service import BrowserService
from recursive_neon.services.media_viewer_service import MediaViewerService


class AppService(IAppService):
    """
    Facade service for managing desktop app data.

    This service delegates to specialized domain services:
    - NotesService: Note-taking app
    - TaskService: Task management app
    - FileSystemService: File browser, text editor, image viewer
    - BrowserService: Web browser pages and bookmarks
    - MediaViewerService: Hypnotic spiral display with text overlays

    This composition pattern improves:
    - Single Responsibility: Each service handles one domain
    - Testability: Services can be tested in isolation
    - Maintainability: Changes are localized to specific services
    """

    def __init__(self, game_state: GameState):
        """
        Initialize the app service with composed domain services.

        Args:
            game_state: The game state instance to manage
        """
        self.game_state = game_state

        # Compose domain services
        self._notes = NotesService(game_state.notes)
        self._tasks = TaskService(game_state.tasks)
        self._filesystem = FileSystemService(game_state.filesystem)
        self._browser = BrowserService(game_state.browser)
        self._media_viewer = MediaViewerService(game_state.media_viewer)

    # ============================================================================
    # Notes Service (delegated)
    # ============================================================================

    def get_notes(self) -> List[Note]:
        """Get all notes."""
        return self._notes.get_all()

    def get_note(self, note_id: str) -> Note:
        """Get a specific note by ID."""
        return self._notes.get(note_id)

    def create_note(self, data: Dict[str, Any]) -> Note:
        """Create a new note."""
        return self._notes.create(data)

    def update_note(self, note_id: str, data: Dict[str, Any]) -> Note:
        """Update an existing note."""
        return self._notes.update(note_id, data)

    def delete_note(self, note_id: str) -> None:
        """Delete a note."""
        self._notes.delete(note_id)

    # ============================================================================
    # Tasks Service (delegated)
    # ============================================================================

    def get_task_lists(self) -> List[TaskList]:
        """Get all task lists."""
        return self._tasks.get_lists()

    def get_task_list(self, list_id: str) -> TaskList:
        """Get a specific task list by ID."""
        return self._tasks.get_list(list_id)

    def create_task_list(self, data: Dict[str, Any]) -> TaskList:
        """Create a new task list."""
        return self._tasks.create_list(data)

    def update_task_list(self, list_id: str, data: Dict[str, Any]) -> TaskList:
        """Update a task list."""
        return self._tasks.update_list(list_id, data)

    def delete_task_list(self, list_id: str) -> None:
        """Delete a task list."""
        self._tasks.delete_list(list_id)

    def create_task(self, list_id: str, data: Dict[str, Any]) -> Task:
        """Create a new task in a list."""
        return self._tasks.create_task(list_id, data)

    def update_task(self, list_id: str, task_id: str, data: Dict[str, Any]) -> Task:
        """Update a task."""
        return self._tasks.update_task(list_id, task_id, data)

    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task."""
        self._tasks.delete_task(list_id, task_id)

    # ============================================================================
    # FileSystem Service (delegated)
    # ============================================================================

    def init_filesystem(self) -> FileNode:
        """Initialize filesystem with root directory."""
        return self._filesystem.init()

    def get_file(self, file_id: str) -> FileNode:
        """Get a file or directory by ID."""
        return self._filesystem.get(file_id)

    def create_directory(self, data: Dict[str, Any]) -> FileNode:
        """Create a new directory."""
        return self._filesystem.create_directory(data)

    def create_file(self, data: Dict[str, Any]) -> FileNode:
        """Create a new file."""
        return self._filesystem.create_file(data)

    def update_file(self, file_id: str, data: Dict[str, Any]) -> FileNode:
        """Update a file."""
        return self._filesystem.update(file_id, data)

    def delete_file(self, file_id: str) -> None:
        """Delete a file or directory (with cascade for directories)."""
        self._filesystem.delete(file_id)

    def copy_file(
        self,
        file_id: str,
        target_parent_id: str,
        new_name: Optional[str] = None
    ) -> FileNode:
        """Copy a file or directory to a new location."""
        return self._filesystem.copy(file_id, target_parent_id, new_name)

    def move_file(self, file_id: str, target_parent_id: str) -> FileNode:
        """Move a file or directory to a new location."""
        return self._filesystem.move(file_id, target_parent_id)

    def list_directory(self, dir_id: str) -> List[FileNode]:
        """List contents of a directory."""
        return self._filesystem.list_directory(dir_id)

    def save_filesystem_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save the entire filesystem state to disk."""
        self._filesystem.save_to_disk(data_dir)

    def load_filesystem_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load the filesystem state from disk."""
        return self._filesystem.load_from_disk(data_dir)

    def load_initial_filesystem(self, initial_fs_dir: str = "backend/initial_fs") -> None:
        """Load initial filesystem state from a directory structure."""
        self._filesystem.load_initial(initial_fs_dir)

    # ============================================================================
    # Browser Service (delegated)
    # ============================================================================

    def get_browser_pages(self) -> List[BrowserPage]:
        """Get all browser pages."""
        return self._browser.get_pages()

    def get_browser_page_by_url(self, url: str) -> Optional[BrowserPage]:
        """Get a browser page by URL."""
        return self._browser.get_page_by_url(url)

    def create_browser_page(self, data: Dict[str, Any]) -> BrowserPage:
        """Create a new browser page."""
        return self._browser.create_page(data)

    def get_bookmarks(self) -> List[str]:
        """Get all bookmarks."""
        return self._browser.get_bookmarks()

    def add_bookmark(self, url: str) -> None:
        """Add a bookmark."""
        self._browser.add_bookmark(url)

    def remove_bookmark(self, url: str) -> None:
        """Remove a bookmark."""
        self._browser.remove_bookmark(url)

    # ============================================================================
    # Media Viewer Service (delegated)
    # ============================================================================

    def get_media_viewer_config(self) -> MediaViewerConfig:
        """Get the media viewer configuration."""
        return self._media_viewer.get_config()

    def update_media_viewer_config(self, data: Dict[str, Any]) -> MediaViewerConfig:
        """Update the media viewer configuration."""
        return self._media_viewer.update_config(data)

    def add_media_viewer_message(self, message_data: Dict[str, Any]) -> TextMessage:
        """Add a text message to the media viewer sequence."""
        return self._media_viewer.add_message(message_data)

    def set_media_viewer_style(self, style: str) -> MediaViewerConfig:
        """Set the spiral style for the media viewer."""
        return self._media_viewer.set_style(style)

    def initialize_default_media_viewer_messages(self) -> None:
        """Initialize the media viewer with default corporate messages."""
        self._media_viewer.initialize_default_messages()

    # ============================================================================
    # Convenience Methods
    # ============================================================================

    def load_or_initialize_filesystem(
        self,
        data_dir: str = "backend/game_data",
        initial_fs_dir: str = "backend/initial_fs"
    ) -> None:
        """
        Load filesystem from disk or initialize from initial files.

        Args:
            data_dir: Directory for saved game data
            initial_fs_dir: Directory containing initial filesystem template
        """
        if not self.load_filesystem_from_disk(data_dir):
            self.load_initial_filesystem(initial_fs_dir)
