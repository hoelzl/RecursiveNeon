"""
FileSystem Service

Manages the virtual in-game filesystem with complete isolation from the host system.
All files exist only in memory as FileNode objects with UUID-based identification.
"""
import base64
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from recursive_neon.models.app_models import FileNode, FileSystemState


class FileSystemService:
    """
    Service for managing the virtual filesystem.

    This service provides CRUD operations for an in-memory filesystem.
    All file operations work with FileNode objects identified by UUIDs,
    ensuring complete isolation from the host filesystem.

    The only real filesystem access is for:
    - Loading initial state from backend/initial_fs/
    - Persisting state to backend/game_data/filesystem.json
    """

    def __init__(self, filesystem_state: FileSystemState):
        """
        Initialize the filesystem service.

        Args:
            filesystem_state: The filesystem state to manage
        """
        self._state = filesystem_state

    # ============================================================================
    # Core Operations
    # ============================================================================

    def init(self) -> FileNode:
        """
        Initialize filesystem with root directory.

        Returns:
            The root directory node
        """
        if self._state.root_id:
            return self.get(self._state.root_id)

        timestamp = datetime.now().isoformat()
        root = FileNode(
            id=str(uuid.uuid4()),
            name="/",
            type="directory",
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._state.nodes.append(root)
        self._state.root_id = root.id
        return root

    def get(self, file_id: str) -> FileNode:
        """
        Get a file or directory by ID.

        Args:
            file_id: ID of the file/directory

        Returns:
            The file node

        Raises:
            ValueError: If file not found
        """
        for node in self._state.nodes:
            if node.id == file_id:
                return node
        raise ValueError(f"File not found: {file_id}")

    def create_directory(self, data: Dict[str, Any]) -> FileNode:
        """
        Create a new directory.

        Args:
            data: Directory data (name, parent_id)

        Returns:
            The created directory node
        """
        timestamp = datetime.now().isoformat()
        directory = FileNode(
            id=str(uuid.uuid4()),
            name=data.get("name", "Untitled Folder"),
            type="directory",
            parent_id=data.get("parent_id"),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._state.nodes.append(directory)
        return directory

    def create_file(self, data: Dict[str, Any]) -> FileNode:
        """
        Create a new file.

        Args:
            data: File data (name, parent_id, content, mime_type)

        Returns:
            The created file node
        """
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
        self._state.nodes.append(file)
        return file

    def update(self, file_id: str, data: Dict[str, Any]) -> FileNode:
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
        file = self.get(file_id)
        timestamp = datetime.now().isoformat()

        for i, node in enumerate(self._state.nodes):
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
                self._state.nodes[i] = updated
                return updated
        raise ValueError(f"File not found: {file_id}")

    def delete(self, file_id: str) -> None:
        """
        Delete a file or directory (with cascade for directories).

        Args:
            file_id: ID of the file/directory to delete
        """
        node = self.get(file_id)

        # If it's a directory, recursively delete all children
        if node.type == "directory":
            children = self.list_directory(file_id)
            for child in children:
                self.delete(child.id)

        # Delete the node itself
        self._state.nodes = [
            n for n in self._state.nodes if n.id != file_id
        ]

    def copy(
        self,
        file_id: str,
        target_parent_id: str,
        new_name: Optional[str] = None
    ) -> FileNode:
        """
        Copy a file or directory to a new location.

        Args:
            file_id: ID of the file/directory to copy
            target_parent_id: ID of the destination parent directory
            new_name: Optional new name for the copy

        Returns:
            The newly created copy
        """
        source = self.get(file_id)
        timestamp = datetime.now().isoformat()

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
        self._state.nodes.append(copy)

        # If it's a directory, recursively copy children
        if source.type == "directory":
            children = self.list_directory(file_id)
            for child in children:
                self.copy(child.id, copy.id)

        return copy

    def move(self, file_id: str, target_parent_id: str) -> FileNode:
        """
        Move a file or directory to a new location.

        Args:
            file_id: ID of the file/directory to move
            target_parent_id: ID of the destination parent directory

        Returns:
            The updated file node

        Raises:
            ValueError: If trying to move a directory into itself
        """
        file = self.get(file_id)
        timestamp = datetime.now().isoformat()

        # Prevent moving a directory into itself or its descendants
        if file.type == "directory":
            current = target_parent_id
            while current:
                if current == file_id:
                    raise ValueError(
                        "Cannot move a directory into itself or its descendants"
                    )
                parent = self.get(current)
                current = parent.parent_id

        # Update the parent_id
        for i, node in enumerate(self._state.nodes):
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
                self._state.nodes[i] = updated
                return updated

        raise ValueError(f"File not found: {file_id}")

    def list_directory(self, dir_id: str) -> List[FileNode]:
        """
        List contents of a directory.

        Args:
            dir_id: ID of the directory

        Returns:
            List of file nodes in the directory
        """
        self.get(dir_id)  # Verify directory exists
        return [
            node for node in self._state.nodes if node.parent_id == dir_id
        ]

    # ============================================================================
    # Persistence Operations
    # ============================================================================

    def save_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """
        Save the entire filesystem state to disk.

        Args:
            data_dir: Directory to save the filesystem state
        """
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "filesystem.json"

        filesystem_dict = {
            "nodes": [node.model_dump() for node in self._state.nodes],
            "root_id": self._state.root_id,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(filesystem_dict, f, indent=2, ensure_ascii=False)

    def load_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """
        Load the filesystem state from disk.

        Args:
            data_dir: Directory to load the filesystem state from

        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        filepath = Path(data_dir) / "filesystem.json"

        if not filepath.exists():
            return False

        with open(filepath, encoding="utf-8") as f:
            filesystem_dict = json.load(f)

        self._state.nodes = [
            FileNode(**node) for node in filesystem_dict["nodes"]
        ]
        self._state.root_id = filesystem_dict.get("root_id")

        return True

    def load_initial(self, initial_fs_dir: str = "backend/initial_fs") -> None:
        """
        Load initial filesystem state from a directory structure.

        Args:
            initial_fs_dir: Directory containing the initial file structure
        """
        initial_path = Path(initial_fs_dir)

        if not initial_path.exists():
            self.init()
            return

        # Clear existing filesystem
        self._state.nodes.clear()
        self._state.root_id = None

        # Create root directory
        root = self.init()

        # Recursively load directory structure
        self._load_directory_recursive(initial_path, root.id)

    def _load_directory_recursive(self, source_path: Path, parent_id: str) -> None:
        """
        Recursively load files and directories from a real directory.

        Args:
            source_path: Path to the real directory to load from
            parent_id: ID of the parent node in the virtual filesystem
        """
        if not source_path.exists() or not source_path.is_dir():
            return

        for item in sorted(source_path.iterdir()):
            # Skip hidden files and system files
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
                self._state.nodes.append(dir_node)
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
                self._state.nodes.append(file_node)

    def _get_mime_type(self, extension: str) -> str:
        """Determine MIME type from file extension."""
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
        """Read file content, encoding binary files as base64."""
        if mime_type.startswith("text/") or mime_type in ["application/json"]:
            try:
                with open(file_path, encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                pass

        # Binary files - encode as base64
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
