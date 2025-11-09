"""
Desktop App Service

Manages state for desktop applications (notes, tasks, filesystem, browser).
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.game_state import GameState
from models.app_models import (
    Note,
    Task,
    TaskList,
    FileNode,
    BrowserPage,
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
        """Delete a file or directory"""
        self.game_state.filesystem.nodes = [
            node for node in self.game_state.filesystem.nodes if node.id != file_id
        ]

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
