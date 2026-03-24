"""
Shell session state.

Holds all mutable state for a shell session: current working directory,
environment variables, history, and convenience wrappers for path resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from recursive_neon.models.app_models import FileNode
from recursive_neon.shell.path_resolver import (
    get_node_path,
    resolve_parent_and_name,
    resolve_path,
)

if TYPE_CHECKING:
    from recursive_neon.dependencies import ServiceContainer


class ShellSession:
    """Mutable state for a single shell session.

    One session per running shell instance. Builtins receive this directly;
    programs get a restricted ProgramContext snapshot instead.
    """

    def __init__(
        self,
        container: ServiceContainer,
        username: str = "user",
        hostname: str = "neon-proxy",
    ) -> None:
        self.container = container
        self.username = username
        self.hostname = hostname
        self.last_exit_code: int = 0
        self.history: list[str] = []

        # Initialize cwd to filesystem root
        root_id = container.game_state.filesystem.root_id
        if root_id is None:
            raise RuntimeError(
                "Filesystem not initialized. "
                "Call app_service.init_filesystem() or load_initial_filesystem() first."
            )
        self.cwd_id: str = root_id

        # Virtual environment variables
        self.env: dict[str, str] = {
            "USER": username,
            "HOME": "/",
            "HOSTNAME": hostname,
            "SHELL": "/bin/nsh",
            "TERM": "neon-256color",
            "PATH": "/bin:/usr/local/bin",
            "PS1": r"\u@\h:\w\$ ",
        }

    def resolve_path(self, path: str) -> FileNode:
        """Resolve a path string to a FileNode."""
        return resolve_path(path, self.cwd_id, self.container.app_service)

    def resolve_parent_and_name(self, path: str) -> tuple[FileNode, str]:
        """Resolve all but the last path segment."""
        return resolve_parent_and_name(path, self.cwd_id, self.container.app_service)

    def get_cwd_path(self) -> str:
        """Get the full path string of the current working directory."""
        return get_node_path(self.cwd_id, self.container.app_service)

    def get_node_path(self, node: FileNode) -> str:
        """Get the full path string for a node."""
        return get_node_path(node.id, self.container.app_service)
