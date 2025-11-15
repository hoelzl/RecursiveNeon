"""
Game State Models
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from recursive_neon.models.app_models import NotesState, TasksState, FileSystemState, BrowserState, MediaViewerState
from recursive_neon.models.notification import Notification, NotificationConfig


class SystemStatus(str, Enum):
    """System status states"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class GameState(BaseModel):
    """Overall game state"""
    player_id: str = "player_1"
    current_location: str = "main_lobby"
    active_quests: list = Field(default_factory=list)
    completed_quests: list = Field(default_factory=list)
    inventory: Dict[str, int] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)

    # Desktop app states
    notes: NotesState = Field(default_factory=NotesState)
    tasks: TasksState = Field(default_factory=TasksState)
    filesystem: FileSystemState = Field(default_factory=FileSystemState)
    browser: BrowserState = Field(default_factory=BrowserState)
    media_viewer: MediaViewerState = Field(default_factory=MediaViewerState)

    # Notification system
    notifications: List[Notification] = Field(default_factory=list)
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig)


class SystemState(BaseModel):
    """Backend system state"""
    status: SystemStatus = SystemStatus.INITIALIZING
    ollama_running: bool = False
    ollama_models_loaded: list = Field(default_factory=list)
    npcs_loaded: int = 0
    uptime_seconds: float = 0
    last_error: Optional[str] = None


class StatusResponse(BaseModel):
    """Status response for health checks"""
    status: str
    system: SystemState
    timestamp: datetime = Field(default_factory=datetime.now)
