"""
App Service

Manages state for game applications: virtual filesystem, notes, and tasks.
Presentation-agnostic — works with CLI, TUI, and GUI interfaces.
"""

import base64
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from recursive_neon.models.app_models import (
    FileNode,
    FileSystemState,
    Note,
    Task,
    TaskList,
)
from recursive_neon.models.game_state import GameState


class AppService:
    """
    Service for managing game app data.

    Provides CRUD operations for:
    - FileSystem (virtual filesystem with security isolation)
    - Notes
    - Tasks and TaskLists
    """

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def handle_action(self, app_type: str, action: str, data: dict) -> dict:
        """Route an app action to the appropriate handler."""
        handlers = {
            "filesystem": self._handle_filesystem_action,
            "notes": self._handle_notes_action,
            "tasks": self._handle_tasks_action,
        }
        handler = handlers.get(app_type)
        if not handler:
            raise ValueError(f"Unknown app type: {app_type}")
        return handler(action, data)

    # ============================================================================
    # Notes
    # ============================================================================

    def get_notes(self) -> List[Note]:
        return self.game_state.notes.notes

    def get_note(self, note_id: str) -> Note:
        for note in self.game_state.notes.notes:
            if note.id == note_id:
                return note
        raise ValueError(f"Note not found: {note_id}")

    def create_note(self, data: Dict[str, Any]) -> Note:
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
        timestamp = datetime.now().isoformat()
        for i, n in enumerate(self.game_state.notes.notes):
            if n.id == note_id:
                updated = Note(
                    id=n.id,
                    title=data.get("title", n.title),
                    content=data.get("content", n.content),
                    created_at=n.created_at,
                    updated_at=timestamp,
                )
                self.game_state.notes.notes[i] = updated
                return updated
        raise ValueError(f"Note not found: {note_id}")

    def delete_note(self, note_id: str) -> None:
        self.game_state.notes.notes = [
            n for n in self.game_state.notes.notes if n.id != note_id
        ]

    def _handle_notes_action(self, action: str, data: dict) -> dict:
        if action == "get_all":
            return {"notes": [n.model_dump() for n in self.get_notes()]}
        elif action == "create":
            note = self.create_note(data)
            return {"note": note.model_dump()}
        elif action == "update":
            note = self.update_note(data["note_id"], data)
            return {"note": note.model_dump()}
        elif action == "delete":
            self.delete_note(data["note_id"])
            return {"success": True}
        raise ValueError(f"Unknown notes action: {action}")

    # ============================================================================
    # Tasks
    # ============================================================================

    def get_task_lists(self) -> List[TaskList]:
        return self.game_state.tasks.lists

    def get_task_list(self, list_id: str) -> TaskList:
        for task_list in self.game_state.tasks.lists:
            if task_list.id == list_id:
                return task_list
        raise ValueError(f"Task list not found: {list_id}")

    def create_task_list(self, data: Dict[str, Any]) -> TaskList:
        task_list = TaskList(
            id=str(uuid.uuid4()),
            name=data.get("name", "Untitled List"),
            tasks=[],
        )
        self.game_state.tasks.lists.append(task_list)
        return task_list

    def delete_task_list(self, list_id: str) -> None:
        self.game_state.tasks.lists = [
            tl for tl in self.game_state.tasks.lists if tl.id != list_id
        ]

    def create_task(self, list_id: str, data: Dict[str, Any]) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            title=data.get("title", "Untitled Task"),
            completed=data.get("completed", False),
            parent_id=data.get("parent_id"),
        )
        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                updated_tasks = list(tl.tasks)
                updated_tasks.append(task)
                self.game_state.tasks.lists[i] = TaskList(
                    id=tl.id, name=tl.name, tasks=updated_tasks
                )
                return task
        raise ValueError(f"Task list not found: {list_id}")

    def update_task(self, list_id: str, task_id: str, data: Dict[str, Any]) -> Task:
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
                        id=tl.id, name=tl.name, tasks=updated_tasks
                    )
                    return updated_task
        raise ValueError(f"Task not found: {task_id}")

    def delete_task(self, list_id: str, task_id: str) -> None:
        for i, tl in enumerate(self.game_state.tasks.lists):
            if tl.id == list_id:
                self.game_state.tasks.lists[i] = TaskList(
                    id=tl.id,
                    name=tl.name,
                    tasks=[t for t in tl.tasks if t.id != task_id],
                )
                break

    def _handle_tasks_action(self, action: str, data: dict) -> dict:
        if action == "get_lists":
            return {"lists": [tl.model_dump() for tl in self.get_task_lists()]}
        elif action == "create_list":
            tl = self.create_task_list(data)
            return {"list": tl.model_dump()}
        elif action == "delete_list":
            self.delete_task_list(data["list_id"])
            return {"success": True}
        elif action == "create_task":
            task = self.create_task(data["list_id"], data)
            return {"task": task.model_dump()}
        elif action == "update_task":
            task = self.update_task(data["list_id"], data["task_id"], data)
            return {"task": task.model_dump()}
        elif action == "delete_task":
            self.delete_task(data["list_id"], data["task_id"])
            return {"success": True}
        raise ValueError(f"Unknown tasks action: {action}")

    # ============================================================================
    # Virtual FileSystem
    # ============================================================================

    def init_filesystem(self) -> FileNode:
        """Initialize filesystem with root directory"""
        if self.game_state.filesystem.root_id:
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
        for node in self.game_state.filesystem.nodes:
            if node.id == file_id:
                return node
        raise ValueError(f"File not found: {file_id}")

    def create_directory(self, data: Dict[str, Any]) -> FileNode:
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
        timestamp = datetime.now().isoformat()
        for i, node in enumerate(self.game_state.filesystem.nodes):
            if node.id == file_id:
                updated = FileNode(
                    id=node.id,
                    name=data.get("name", node.name),
                    type=node.type,
                    parent_id=node.parent_id,
                    content=data.get("content", node.content),
                    mime_type=data.get("mime_type", node.mime_type),
                    created_at=node.created_at,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes[i] = updated
                return updated
        raise ValueError(f"File not found: {file_id}")

    def delete_file(self, file_id: str) -> None:
        node = self.get_file(file_id)
        if node.type == "directory":
            for child in self.list_directory(file_id):
                self.delete_file(child.id)
        self.game_state.filesystem.nodes = [
            n for n in self.game_state.filesystem.nodes if n.id != file_id
        ]

    def copy_file(
        self, file_id: str, target_parent_id: str, new_name: str | None = None
    ) -> FileNode:
        source = self.get_file(file_id)
        timestamp = datetime.now().isoformat()
        copy = FileNode(
            id=str(uuid.uuid4()),
            name=new_name or source.name,
            type=source.type,
            parent_id=target_parent_id,
            content=source.content,
            mime_type=source.mime_type,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.game_state.filesystem.nodes.append(copy)
        if source.type == "directory":
            for child in self.list_directory(file_id):
                self.copy_file(child.id, copy.id)
        return copy

    def move_file(self, file_id: str, target_parent_id: str) -> FileNode:
        file = self.get_file(file_id)
        timestamp = datetime.now().isoformat()
        if file.type == "directory":
            current: str | None = target_parent_id
            while current:
                if current == file_id:
                    raise ValueError(
                        "Cannot move a directory into itself or its descendants"
                    )
                parent = self.get_file(current)
                current = parent.parent_id
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
        self.get_file(dir_id)
        return [
            node
            for node in self.game_state.filesystem.nodes
            if node.parent_id == dir_id
        ]

    def _handle_filesystem_action(self, action: str, data: dict) -> dict:
        if action == "init":
            root = self.init_filesystem()
            return {"root": root.model_dump()}
        elif action == "list":
            nodes = self.list_directory(data["dir_id"])
            return {"nodes": [n.model_dump() for n in nodes]}
        elif action == "get":
            node = self.get_file(data["file_id"])
            return {"node": node.model_dump()}
        elif action == "create_file":
            node = self.create_file(data)
            return {"node": node.model_dump()}
        elif action == "create_directory":
            node = self.create_directory(data)
            return {"node": node.model_dump()}
        elif action == "update":
            node = self.update_file(data["file_id"], data)
            return {"node": node.model_dump()}
        elif action == "delete":
            self.delete_file(data["file_id"])
            return {"success": True}
        elif action == "copy":
            node = self.copy_file(
                data["file_id"], data["target_parent_id"], data.get("new_name")
            )
            return {"node": node.model_dump()}
        elif action == "move":
            node = self.move_file(data["file_id"], data["target_parent_id"])
            return {"node": node.model_dump()}
        raise ValueError(f"Unknown filesystem action: {action}")

    # ============================================================================
    # Persistence
    # ============================================================================

    def save_filesystem_to_disk(self, data_dir: str = "backend/game_data") -> None:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "filesystem.json"
        filesystem_dict = {
            "nodes": [node.model_dump() for node in self.game_state.filesystem.nodes],
            "root_id": self.game_state.filesystem.root_id,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(filesystem_dict, f, indent=2, ensure_ascii=False)

    def load_filesystem_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        filepath = Path(data_dir) / "filesystem.json"
        if not filepath.exists():
            return False
        with open(filepath, encoding="utf-8") as f:
            filesystem_dict = json.load(f)
        self.game_state.filesystem = FileSystemState(
            nodes=[FileNode(**node) for node in filesystem_dict["nodes"]],
            root_id=filesystem_dict.get("root_id"),
        )
        return True

    def save_notes_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save notes state to disk as JSON."""
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "notes.json"
        notes_dict = {
            "notes": [note.model_dump() for note in self.game_state.notes.notes],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(notes_dict, f, indent=2, ensure_ascii=False)

    def load_notes_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load notes state from disk. Returns False if no saved state exists."""
        filepath = Path(data_dir) / "notes.json"
        if not filepath.exists():
            return False
        with open(filepath, encoding="utf-8") as f:
            notes_dict = json.load(f)
        from recursive_neon.models.app_models import NotesState

        self.game_state.notes = NotesState(
            notes=[Note(**n) for n in notes_dict.get("notes", [])],
        )
        return True

    def save_tasks_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save tasks state to disk as JSON."""
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "tasks.json"
        tasks_dict = {
            "lists": [tl.model_dump() for tl in self.game_state.tasks.lists],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tasks_dict, f, indent=2, ensure_ascii=False)

    def load_tasks_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load tasks state from disk. Returns False if no saved state exists."""
        filepath = Path(data_dir) / "tasks.json"
        if not filepath.exists():
            return False
        with open(filepath, encoding="utf-8") as f:
            tasks_dict = json.load(f)
        from recursive_neon.models.app_models import TasksState

        self.game_state.tasks = TasksState(
            lists=[TaskList(**tl) for tl in tasks_dict.get("lists", [])],
        )
        return True

    def save_all_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save all state (filesystem, notes, tasks) to disk."""
        self.save_filesystem_to_disk(data_dir)
        self.save_notes_to_disk(data_dir)
        self.save_tasks_to_disk(data_dir)

    def load_all_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load all state from disk. Returns True if filesystem was loaded."""
        fs_loaded = self.load_filesystem_from_disk(data_dir)
        self.load_notes_from_disk(data_dir)
        self.load_tasks_from_disk(data_dir)
        return fs_loaded

    def load_initial_filesystem(
        self, initial_fs_dir: str = "backend/initial_fs"
    ) -> None:
        initial_path = Path(initial_fs_dir)
        if not initial_path.exists():
            self.init_filesystem()
            return
        self.game_state.filesystem.nodes.clear()
        self.game_state.filesystem.root_id = None
        root = self.init_filesystem()
        self._load_directory_recursive(initial_path, root.id)

    def _load_directory_recursive(self, source_path: Path, parent_id: str) -> None:
        if not source_path.exists() or not source_path.is_dir():
            return
        for item in sorted(source_path.iterdir()):
            if item.name.startswith("."):
                continue
            timestamp = datetime.now().isoformat()
            if item.is_dir():
                dir_node = FileNode(
                    id=str(uuid.uuid4()),
                    name=item.name,
                    type="directory",
                    parent_id=parent_id,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self.game_state.filesystem.nodes.append(dir_node)
                self._load_directory_recursive(item, dir_node.id)
            elif item.is_file():
                mime_type = self._get_mime_type(item.suffix)
                content = self._read_file_content(item, mime_type)
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
        mime_types = {
            ".txt": "text/plain",
            ".md": "text/plain",
            ".json": "application/json",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "text/javascript",
            ".py": "text/x-python",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".pdf": "application/pdf",
        }
        return mime_types.get(extension.lower(), "application/octet-stream")

    def _read_file_content(self, file_path: Path, mime_type: str) -> str:
        if mime_type.startswith("text/") or mime_type in ["application/json"]:
            try:
                with open(file_path, encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                pass
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
