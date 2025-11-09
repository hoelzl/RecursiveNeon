"""
Data models for desktop applications
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# ============================================================================
# Notes App Models
# ============================================================================


class Note(BaseModel):
    """A single note in the note-taking app"""

    id: str
    title: str
    content: str
    created_at: str
    updated_at: str


class NotesState(BaseModel):
    """State for the note-taking app"""

    notes: List[Note] = Field(default_factory=list)


# ============================================================================
# Task List App Models
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
    """State for the task list app"""

    lists: List[TaskList] = Field(default_factory=list)


# ============================================================================
# File System Models (for File Browser, Text Editor, Image Viewer)
# ============================================================================


class FileNode(BaseModel):
    """A file or directory node in the virtual filesystem"""

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
# Web Browser Models
# ============================================================================


class BrowserPage(BaseModel):
    """A web page that can be displayed in the sandboxed browser"""

    id: str
    url: str  # Virtual URL/address
    title: str
    content: str  # HTML content to display


class BrowserState(BaseModel):
    """State for the web browser app"""

    pages: List[BrowserPage] = Field(default_factory=list)
    bookmarks: List[str] = Field(default_factory=list)  # List of URLs
