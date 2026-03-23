"""
Game State Models
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from recursive_neon.models.app_models import FileSystemState, NotesState, TasksState


class SystemStatus(StrEnum):
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
    active_quests: List[str] = Field(default_factory=list)
    completed_quests: List[str] = Field(default_factory=list)
    inventory: Dict[str, int] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)

    # App states
    notes: NotesState = Field(default_factory=NotesState)
    tasks: TasksState = Field(default_factory=TasksState)
    filesystem: FileSystemState = Field(default_factory=FileSystemState)


class SystemState(BaseModel):
    """Backend system state"""

    status: SystemStatus = SystemStatus.INITIALIZING
    ollama_running: bool = False
    ollama_models_loaded: List[str] = Field(default_factory=list)
    npcs_loaded: int = 0
    uptime_seconds: float = 0
    last_error: str | None = None


class StatusResponse(BaseModel):
    """Status response for health checks"""

    status: str
    system: SystemState
    timestamp: datetime = Field(default_factory=datetime.now)
