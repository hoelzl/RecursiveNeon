"""
Path resolution for the virtual filesystem.

Translates human-readable paths (e.g., "/Documents/readme.txt")
to FileNode UUIDs. This is a standalone module so it can be used by
ShellSession, ProgramContext, and (future) virtual_open() without coupling.
"""

from __future__ import annotations

from recursive_neon.models.app_models import FileNode
from recursive_neon.services.app_service import AppService


def resolve_path(
    path: str,
    cwd_id: str,
    app_service: AppService,
) -> FileNode:
    """Resolve a path string to a FileNode.

    Args:
        path: Absolute (starts with /) or relative path.
        cwd_id: UUID of the current working directory.
        app_service: AppService for filesystem access.

    Returns:
        The FileNode at the resolved path.

    Raises:
        FileNotFoundError: If a path segment doesn't match any child.
        NotADirectoryError: If traversing through a file.
    """
    root_id = app_service.game_state.filesystem.root_id
    if root_id is None:
        raise FileNotFoundError("Filesystem not initialized")

    # Determine starting node
    if path == "/":
        return app_service.get_file(root_id)

    is_absolute = path.startswith("/")
    if is_absolute:
        current_id = root_id
        path = path[1:]  # Strip leading /
    else:
        current_id = cwd_id

    segments = [s for s in path.split("/") if s]

    for i, segment in enumerate(segments):
        current = app_service.get_file(current_id)

        if segment == ".":
            continue

        if segment == "..":
            if current.parent_id is not None:
                current_id = current.parent_id
            # At root, .. stays at root
            continue

        # Must be in a directory to traverse into children
        if current.type != "directory":
            traversed = "/".join(segments[:i])
            raise NotADirectoryError(f"Not a directory: {traversed or current.name}")

        # Find child with matching name
        children = app_service.list_directory(current_id)
        match = None
        for child in children:
            if child.name == segment:
                match = child
                break

        if match is None:
            # Build the full path for the error message
            if is_absolute or cwd_id == root_id:
                full_path = "/" + "/".join(segments[: i + 1])
            else:
                full_path = "/".join(segments[: i + 1])
            raise FileNotFoundError(f"No such file or directory: {full_path}")

        current_id = match.id

    return app_service.get_file(current_id)


def resolve_parent_and_name(
    path: str,
    cwd_id: str,
    app_service: AppService,
) -> tuple[FileNode, str]:
    """Resolve all but the last segment, returning (parent_dir, name).

    Used by commands that create new files/directories.

    Args:
        path: Path where the last segment is the new name.
        cwd_id: UUID of the current working directory.
        app_service: AppService for filesystem access.

    Returns:
        Tuple of (parent FileNode, name string).

    Raises:
        FileNotFoundError: If the parent path doesn't exist.
        NotADirectoryError: If the parent is not a directory.
        ValueError: If the path is empty or just "/".
    """
    path = path.rstrip("/")
    if not path or path == "/":
        raise ValueError("Path must include a name component")

    last_slash = path.rfind("/")
    if last_slash == -1:
        # Relative name with no directory part — parent is cwd
        parent = app_service.get_file(cwd_id)
        name = path
    elif last_slash == 0:
        # /name — parent is root
        root_id = app_service.game_state.filesystem.root_id
        if root_id is None:
            raise FileNotFoundError("Filesystem not initialized")
        parent = app_service.get_file(root_id)
        name = path[1:]
    else:
        # dir/subdir/name — resolve parent path
        parent_path = path[:last_slash]
        name = path[last_slash + 1 :]
        parent = resolve_path(parent_path, cwd_id, app_service)

    if parent.type != "directory":
        raise NotADirectoryError(f"Not a directory: {parent.name}")

    if not name:
        raise ValueError("Name component is empty")

    return parent, name


def get_node_path(node_id: str, app_service: AppService) -> str:
    """Get the full path string for a node by walking parent links.

    Args:
        node_id: UUID of the node.
        app_service: AppService for filesystem access.

    Returns:
        Full path string (e.g., "/Documents/readme.txt").
    """
    root_id = app_service.game_state.filesystem.root_id
    parts: list[str] = []
    current_id: str | None = node_id
    visited: set[str] = set()

    while current_id is not None:
        if current_id in visited:
            break  # cycle detected — corrupt parent links
        visited.add(current_id)
        node = app_service.get_file(current_id)
        if current_id == root_id:
            break
        parts.append(node.name)
        current_id = node.parent_id

    if not parts:
        return "/"

    parts.reverse()
    return "/" + "/".join(parts)
