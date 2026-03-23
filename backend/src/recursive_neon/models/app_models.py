"""
Data models for game applications.

Core models for the virtual filesystem, notes, and tasks.
These are presentation-agnostic and work with both CLI and GUI interfaces.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# ============================================================================
# File System Models (Virtual filesystem - security-critical)
# ============================================================================


class FileNode(BaseModel):
    """A file or directory node in the virtual filesystem.

    All nodes are identified by UUID, not file paths.
    Content is stored in memory, never touching the real filesystem.
    See FILESYSTEM_SECURITY.md for details.
    """

    id: str
    name: str
    type: str  # "file" or "directory"
    parent_id: Optional[str] = None
    content: Optional[str] = None  # For files: text content or base64 for images
    mime_type: Optional[str] = None  # For files: "text/plain", "image/jpeg", etc.
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FileSystemState(BaseModel):
    """State for the virtual filesystem"""

    nodes: List[FileNode] = Field(default_factory=list)
    root_id: Optional[str] = None  # ID of the root directory


# ============================================================================
# Notes Models
# ============================================================================


class Note(BaseModel):
    """A single note"""

    id: str
    title: str
    content: str
    created_at: str
    updated_at: str


class NotesState(BaseModel):
    """State for notes"""

    notes: List[Note] = Field(default_factory=list)


# ============================================================================
# Task List Models
# ============================================================================


class Task(BaseModel):
    """A single task or subtask"""

    id: str
    title: str
    completed: bool
    parent_id: Optional[str] = None  # For subtasks, ID of parent task


class TaskList(BaseModel):
    """A list of tasks (e.g., "Personal", "Work", "Quests")"""

    id: str
    name: str
    tasks: List[Task] = Field(default_factory=list)


class TasksState(BaseModel):
    """State for task lists"""

    lists: List[TaskList] = Field(default_factory=list)
