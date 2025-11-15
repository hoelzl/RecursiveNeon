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


# ============================================================================
# Media Viewer Models (Hypnotic Spiral Display)
# ============================================================================


class TextMessage(BaseModel):
    """
    A text message to display over the spiral animation.

    Can represent either text to display or a pause (when text is None).
    """

    text: Optional[str] = None  # None means pause/blank screen
    duration: float = 3.0  # Duration in seconds
    size: int = 32  # Font size in pixels
    color: str = "#FFFFFF"  # Text color (CSS color)
    x: int = 50  # X position (percentage of screen width, 0-100)
    y: int = 50  # Y position (percentage of screen height, 0-100)
    font_weight: str = "normal"  # CSS font-weight: "normal", "bold", etc.


class MediaViewerConfig(BaseModel):
    """
    Configuration for the Media Viewer app.

    This "health and relaxation" feature displays hypnotic spirals with
    configurable text messages. In-universe, it's marketed for wellness
    but is actually used for subtle manipulation by corporations and
    the government.
    """

    spiral_style: str = "blackwhite"  # "blackwhite" or "colorful"
    rotation_speed: float = 1.0  # Speed multiplier for spiral rotation
    messages: List[TextMessage] = Field(default_factory=list)
    loop: bool = True  # Whether to loop messages continuously


class MediaViewerState(BaseModel):
    """State for the media viewer app"""

    config: MediaViewerConfig = Field(default_factory=MediaViewerConfig)
