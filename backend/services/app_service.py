"""
Desktop App Service

Manages state for desktop applications (notes, tasks, filesystem, browser).
"""
import uuid
import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from ..models.game_state import GameState
from ..models.app_models import (
    Note,
    Task,
    TaskList,
    FileNode,
    BrowserPage,
    FileSystemState,
)


class AppService:
    """
    Service for managing desktop app data.

    This service provides CRUD operations for:
    - Notes (note-taking app)
    - Tasks and TaskLists (task management app)
    - FileSystem (file browser, text editor, image viewer)
    - Browser pages and bookmarks (web browser app)
    """

    def __init__(self, game_state: GameState):
        """
        Initialize the app service.

        Args:
            game_state: The game state instance to manage
        """
        self.game_state = game_state

    # ============================================================================
    # Notes Service
    # ============================================================================

    def get_notes(self) -> List[Note]:
        """Get all notes"""
        return self.game_state.notes.notes

    def get_note(self, note_id: str) -> Note:
        """Get a specific note by ID"""
        for note in self.game_state.notes.notes:
            if note.id == note_id:
                return note
        raise ValueError(f"Note not found: {note_id}")

    def create_note(self, data: Dict[str, Any]) -> Note:
        """Create a new note"""
        timestamp = datetime.now().isoformat()
        note = Note(
            id=str(uuid.uuid4()),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.notes.notes.append(note)
        return note

    def update_note(self, note_id: str, data: Dict[str, Any]) -> Note:
        """Update an existing note"""
        note = self.get_note(note_id)
        timestamp = datetime.now().isoformat()

        # Update note in the list
        for i, n in enumerate(self.game_state.notes.notes):
            if n.id == note_id:
                updated = Note(
                    id=note.id,
                    title=data.get("title", note.title),
                    content=data.get("content", note.content),
                    created_at=note.created_at,
                    updated_at=timestamp,
                )
                self.game_state.notes.notes[i] = updated
                return updated
        raise ValueError(f"Note not found: {note_id}")

    def delete_note(self, note_id: str) -> None:
        """Delete a note"""
        self.game_state.notes.notes = [
            note for note in self.game_state.notes.notes if note.id != note_id
        ]

    # ============================================================================
    # Tasks Service
    # ============================================================================

    def get_task_lists(self) -> List[TaskList]:
        """Get all task lists"""
        return self.game_state.tasks.lists

    def get_task_list(self, list_id: str) -> TaskList:
        """Get a specific task list by ID"""
        for task_list in self.game_state.tasks.lists:
            if task_list.id == list_id:
                return task_list
        raise ValueError(f"Task list not found: {list_id}")

    def create_task_list(self, data: Dict[str, Any]) -> TaskList:
        """Create a new task list"""
        task_list = TaskList(
            id=str(uuid.uuid4()),
            name=data.get("name", "Untitled List"),
            tasks=[],
        )
        self.game_state.tasks.lists.append(task_list)
        return task_list

    def update_task_list(self, list_id: str, data: Dict[str, Any]) -> TaskList:
        """Update a task list"""
        task_list = self.get_task_list(list_id)
        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                updated = TaskList(
                    id=task_list.id,
                    name=data.get("name", task_list.name),
                    tasks=task_list.tasks,
                )
                self.game_state.tasks.lists[i] = updated
                return updated
        raise ValueError(f"Task list not found: {list_id}")

    def delete_task_list(self, list_id: str) -> None:
        """Delete a task list"""
        self.game_state.tasks.lists = [
            tl for tl in self.game_state.tasks.lists if tl.id != list_id
        ]

    def create_task(self, list_id: str, data: Dict[str, Any]) -> Task:
        """Create a new task in a list"""
        task_list = self.get_task_list(list_id)
        task = Task(
            id=str(uuid.uuid4()),
            title=data.get("title", "Untitled Task"),
            completed=data.get("completed", False),
            parent_id=data.get("parent_id"),
        )

        # Update the task list with the new task
        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                updated_tasks = list(tl.tasks)
                updated_tasks.append(task)
                self.game_state.tasks.lists[i] = TaskList(
                    id=tl.id,
                    name=tl.name,
                    tasks=updated_tasks,
                )
                break

        return task

    def update_task(self, list_id: str, task_id: str, data: Dict[str, Any]) -> Task:
        """Update a task"""
        task_list = self.get_task_list(list_id)

        # Find and update the task
        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                updated_tasks = []
                updated_task = None
                for task in tl.tasks:
                    if task.id == task_id:
                        updated_task = Task(
                            id=task.id,
                            title=data.get("title", task.title),
                            completed=data.get("completed", task.completed),
                            parent_id=data.get("parent_id", task.parent_id),
                        )
                        updated_tasks.append(updated_task)
                    else:
                        updated_tasks.append(task)

                if updated_task:
                    self.game_state.tasks.lists[i] = TaskList(
                        id=tl.id,
                        name=tl.name,
                        tasks=updated_tasks,
                    )
                    return updated_task

        raise ValueError(f"Task not found: {task_id}")

    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task"""
        task_list = self.get_task_list(list_id)

        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                self.game_state.tasks.lists[i] = TaskList(
                    id=tl.id,
                    name=tl.name,
                    tasks=[t for t in tl.tasks if t.id != task_id],
                )
                break

    # ============================================================================
    # FileSystem Service
    # ============================================================================

    def init_filesystem(self) -> FileNode:
        """Initialize filesystem with root directory"""
        if self.game_state.filesystem.root_id:
            # Already initialized
            return self.get_file(self.game_state.filesystem.root_id)

        timestamp = datetime.now().isoformat()
        root = FileNode(
            id=str(uuid.uuid4()),
            name="/",
            type="directory",
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.filesystem.nodes.append(root)
        self.game_state.filesystem.root_id = root.id
        return root

    def get_file(self, file_id: str) -> FileNode:
        """Get a file or directory by ID"""
        for node in self.game_state.filesystem.nodes:
            if node.id == file_id:
                return node
        raise ValueError(f"File not found: {file_id}")

    def create_directory(self, data: Dict[str, Any]) -> FileNode:
        """Create a new directory"""
        timestamp = datetime.now().isoformat()
        directory = FileNode(
            id=str(uuid.uuid4()),
            name=data.get("name", "Untitled Folder"),
            type="directory",
            parent_id=data.get("parent_id"),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.filesystem.nodes.append(directory)
        return directory

    def create_file(self, data: Dict[str, Any]) -> FileNode:
        """Create a new file"""
        timestamp = datetime.now().isoformat()
        file = FileNode(
            id=str(uuid.uuid4()),
            name=data.get("name", "untitled.txt"),
            type="file",
            parent_id=data.get("parent_id"),
            content=data.get("content", ""),
            mime_type=data.get("mime_type", "text/plain"),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.filesystem.nodes.append(file)
        return file

    def update_file(self, file_id: str, data: Dict[str, Any]) -> FileNode:
        """Update a file"""
        file = self.get_file(file_id)
        timestamp = datetime.now().isoformat()

        for i, node in enumerate(self.game_state.filesystem.nodes):
            if node.id == file_id:
                updated = FileNode(
                    id=file.id,
                    name=data.get("name", file.name),
                    type=file.type,
                    parent_id=file.parent_id,
                    content=data.get("content", file.content),
                    mime_type=data.get("mime_type", file.mime_type),
                    created_at=file.created_at,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes[i] = updated
                return updated
        raise ValueError(f"File not found: {file_id}")

    def delete_file(self, file_id: str) -> None:
        """Delete a file or directory (with cascade for directories)"""
        node = self.get_file(file_id)

        # If it's a directory, recursively delete all children
        if node.type == "directory":
            children = self.list_directory(file_id)
            for child in children:
                self.delete_file(child.id)

        # Delete the node itself
        self.game_state.filesystem.nodes = [
            n for n in self.game_state.filesystem.nodes if n.id != file_id
        ]

    def copy_file(self, file_id: str, target_parent_id: str, new_name: Optional[str] = None) -> FileNode:
        """
        Copy a file or directory to a new location.

        Args:
            file_id: ID of the file/directory to copy
            target_parent_id: ID of the destination parent directory
            new_name: Optional new name for the copy

        Returns:
            The newly created copy
        """
        source = self.get_file(file_id)
        timestamp = datetime.now().isoformat()

        # Create the copy with a new ID
        copy = FileNode(
            id=str(uuid.uuid4()),
            name=new_name if new_name else source.name,
            type=source.type,
            parent_id=target_parent_id,
            content=source.content,
            mime_type=source.mime_type,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.filesystem.nodes.append(copy)

        # If it's a directory, recursively copy children
        if source.type == "directory":
            children = self.list_directory(file_id)
            for child in children:
                self.copy_file(child.id, copy.id)

        return copy

    def move_file(self, file_id: str, target_parent_id: str) -> FileNode:
        """
        Move a file or directory to a new location.

        Args:
            file_id: ID of the file/directory to move
            target_parent_id: ID of the destination parent directory

        Returns:
            The updated file node
        """
        file = self.get_file(file_id)
        timestamp = datetime.now().isoformat()

        # Prevent moving a directory into itself or its descendants
        if file.type == "directory":
            current = target_parent_id
            while current:
                if current == file_id:
                    raise ValueError("Cannot move a directory into itself or its descendants")
                parent = self.get_file(current)
                current = parent.parent_id

        # Update the parent_id
        for i, node in enumerate(self.game_state.filesystem.nodes):
            if node.id == file_id:
                updated = FileNode(
                    id=file.id,
                    name=file.name,
                    type=file.type,
                    parent_id=target_parent_id,
                    content=file.content,
                    mime_type=file.mime_type,
                    created_at=file.created_at,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes[i] = updated
                return updated

        raise ValueError(f"File not found: {file_id}")

    def list_directory(self, dir_id: str) -> List[FileNode]:
        """List contents of a directory"""
        # Verify directory exists
        self.get_file(dir_id)

        # Return all nodes with this directory as parent
        return [
            node
            for node in self.game_state.filesystem.nodes
            if node.parent_id == dir_id
        ]

    def save_filesystem_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """
        Save the entire filesystem state to disk.

        Args:
            data_dir: Directory to save the filesystem state (default: backend/game_data)

        This saves to a single JSON file, ensuring complete isolation from the user's
        real file system.
        """
        # Create the data directory if it doesn't exist
        Path(data_dir).mkdir(parents=True, exist_ok=True)

        # Save filesystem state to JSON
        filepath = Path(data_dir) / "filesystem.json"
        filesystem_dict = {
            "nodes": [node.model_dump() for node in self.game_state.filesystem.nodes],
            "root_id": self.game_state.filesystem.root_id,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(filesystem_dict, f, indent=2, ensure_ascii=False)

    def load_filesystem_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """
        Load the filesystem state from disk.

        Args:
            data_dir: Directory to load the filesystem state from

        Returns:
            True if loaded successfully, False if file doesn't exist

        This only reads from the controlled game_data directory.
        """
        filepath = Path(data_dir) / "filesystem.json"

        if not filepath.exists():
            return False

        with open(filepath, "r", encoding="utf-8") as f:
            filesystem_dict = json.load(f)

        # Replace the current filesystem state
        self.game_state.filesystem = FileSystemState(
            nodes=[FileNode(**node) for node in filesystem_dict["nodes"]],
            root_id=filesystem_dict.get("root_id"),
        )

        return True

    def load_initial_filesystem(self, initial_fs_dir: str = "backend/initial_fs") -> None:
        """
        Load initial filesystem state from a directory structure.

        Args:
            initial_fs_dir: Directory containing the initial file structure

        This reads files from the source code directory and populates the in-game
        filesystem. This is a one-way read operation - the source directory is never
        modified by the game.
        """
        initial_path = Path(initial_fs_dir)

        if not initial_path.exists():
            # No initial filesystem provided, just create empty root
            self.init_filesystem()
            return

        # Clear existing filesystem
        self.game_state.filesystem.nodes.clear()
        self.game_state.filesystem.root_id = None

        # Create root directory
        root = self.init_filesystem()

        # Recursively load directory structure
        self._load_directory_recursive(initial_path, root.id)

    def _load_directory_recursive(self, source_path: Path, parent_id: str) -> None:
        """
        Recursively load files and directories from a real directory into the virtual filesystem.

        Args:
            source_path: Path to the real directory to load from
            parent_id: ID of the parent node in the virtual filesystem
        """
        if not source_path.exists() or not source_path.is_dir():
            return

        # Process all items in the directory
        for item in sorted(source_path.iterdir()):
            # Skip hidden files and system files
            if item.name.startswith('.'):
                continue

            timestamp = datetime.now().isoformat()

            if item.is_dir():
                # Create directory node
                dir_node = FileNode(
                    id=str(uuid.uuid4()),
                    name=item.name,
                    type="directory",
                    parent_id=parent_id,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes.append(dir_node)

                # Recursively load subdirectory
                self._load_directory_recursive(item, dir_node.id)

            elif item.is_file():
                # Determine MIME type based on extension
                mime_type = self._get_mime_type(item.suffix)

                # Read file content
                content = self._read_file_content(item, mime_type)

                # Create file node
                file_node = FileNode(
                    id=str(uuid.uuid4()),
                    name=item.name,
                    type="file",
                    parent_id=parent_id,
                    content=content,
                    mime_type=mime_type,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes.append(file_node)

    def _get_mime_type(self, extension: str) -> str:
        """
        Determine MIME type from file extension.

        Args:
            extension: File extension (including the dot)

        Returns:
            MIME type string
        """
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/plain',
            '.json': 'application/json',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'text/javascript',
            '.py': 'text/x-python',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')

    def _read_file_content(self, file_path: Path, mime_type: str) -> str:
        """
        Read file content, encoding binary files as base64.

        Args:
            file_path: Path to the file to read
            mime_type: MIME type of the file

        Returns:
            File content (text or base64 encoded)
        """
        # Text MIME types
        if mime_type.startswith('text/') or mime_type in ['application/json']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fall back to binary if can't decode as text
                pass

        # Binary files - encode as base64
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('ascii')

    # ============================================================================
    # Browser Service
    # ============================================================================

    def get_browser_pages(self) -> List[BrowserPage]:
        """Get all browser pages"""
        return self.game_state.browser.pages

    def get_browser_page_by_url(self, url: str) -> Optional[BrowserPage]:
        """Get a browser page by URL"""
        for page in self.game_state.browser.pages:
            if page.url == url:
                return page
        return None

    def create_browser_page(self, data: Dict[str, Any]) -> BrowserPage:
        """Create a new browser page"""
        page = BrowserPage(
            id=str(uuid.uuid4()),
            url=data.get("url", ""),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
        )
        self.game_state.browser.pages.append(page)
        return page

    def get_bookmarks(self) -> List[str]:
        """Get all bookmarks"""
        return self.game_state.browser.bookmarks

    def add_bookmark(self, url: str) -> None:
        """Add a bookmark"""
        if url not in self.game_state.browser.bookmarks:
            self.game_state.browser.bookmarks.append(url)

    def remove_bookmark(self, url: str) -> None:
        """Remove a bookmark"""
        self.game_state.browser.bookmarks = [
            b for b in self.game_state.browser.bookmarks if b != url
        ]
