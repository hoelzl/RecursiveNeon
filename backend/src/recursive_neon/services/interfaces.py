"""
Service Interfaces for Dependency Injection

This module defines abstract interfaces for all backend services.
These interfaces enable:
- Dependency injection
- Mocking in tests
- Loose coupling between components
- Clear service contracts
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from recursive_neon.models.app_models import FileNode, Note, Task, TaskList
from recursive_neon.models.npc import NPC, ChatResponse

# ============================================================================
# LLM Interface (for LangChain compatibility)
# ============================================================================


@runtime_checkable
class LLMInterface(Protocol):
    """
    Protocol for Language Model providers.

    This interface matches the LangChain BaseChatModel interface, allowing us to
    inject different LLM implementations (real or mock) into NPCManager.
    """

    def invoke(self, prompt: Any, *args: Any, **kwargs: Any) -> Any:
        """Synchronously invoke the LLM"""
        ...

    async def ainvoke(self, prompt: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously invoke the LLM"""
        ...


# ============================================================================
# Application Service Interface
# ============================================================================


@runtime_checkable
class IAppService(Protocol):
    """Protocol for the main application service."""

    # Notes
    def get_notes(self) -> list[Note]: ...
    def get_note(self, note_id: str) -> Note: ...
    def create_note(self, data: dict[str, Any]) -> Note: ...
    def update_note(self, note_id: str, data: dict[str, Any]) -> Note: ...
    def delete_note(self, note_id: str) -> None: ...

    # Tasks
    def get_task_lists(self) -> list[TaskList]: ...
    def get_task_list(self, list_id: str) -> TaskList: ...
    def create_task_list(self, data: dict[str, Any]) -> TaskList: ...
    def delete_task_list(self, list_id: str) -> None: ...
    def create_task(self, list_id: str, data: dict[str, Any]) -> Task: ...
    def update_task(self, list_id: str, task_id: str, data: dict[str, Any]) -> Task: ...
    def delete_task(self, list_id: str, task_id: str) -> None: ...

    # Filesystem
    def init_filesystem(self) -> FileNode: ...
    def get_file(self, file_id: str) -> FileNode: ...
    def create_directory(self, data: dict[str, Any]) -> FileNode: ...
    def create_file(self, data: dict[str, Any]) -> FileNode: ...
    def update_file(self, file_id: str, data: dict[str, Any]) -> FileNode: ...
    def delete_file(self, file_id: str) -> None: ...
    def copy_file(
        self,
        file_id: str,
        target_parent_id: str,
        new_name: str | None = None,
        *,
        overwrite: bool = False,
    ) -> FileNode: ...
    def move_file(
        self,
        file_id: str,
        target_parent_id: str,
        new_name: str | None = None,
        *,
        overwrite: bool = False,
    ) -> FileNode: ...
    def list_directory(self, dir_id: str) -> list[FileNode]: ...
    def get_filesystem_root_id(self) -> str | None: ...
    def load_initial_filesystem(
        self, initial_fs_dir: str = "backend/initial_fs"
    ) -> None: ...

    # Action dispatcher
    def handle_action(self, app_type: str, action: str, data: dict) -> dict: ...

    # Persistence
    async def save_filesystem_to_disk(
        self, data_dir: str = "backend/game_data"
    ) -> None: ...
    async def load_filesystem_from_disk(
        self, data_dir: str = "backend/game_data"
    ) -> bool: ...
    async def save_notes_to_disk(self, data_dir: str = "backend/game_data") -> None: ...
    async def load_notes_from_disk(
        self, data_dir: str = "backend/game_data"
    ) -> bool: ...
    async def save_tasks_to_disk(self, data_dir: str = "backend/game_data") -> None: ...
    async def load_tasks_from_disk(
        self, data_dir: str = "backend/game_data"
    ) -> bool: ...
    async def save_all_to_disk(self, data_dir: str = "backend/game_data") -> None: ...
    async def load_all_from_disk(self, data_dir: str = "backend/game_data") -> bool: ...


# ============================================================================
# NPC Manager Interface
# ============================================================================


class INPCManager(ABC):
    """Abstract interface for NPC management."""

    @abstractmethod
    def register_npc(self, npc: NPC) -> None:
        """Register a new NPC."""
        pass

    @abstractmethod
    def unregister_npc(self, npc_id: str) -> None:
        """Unregister an NPC."""
        pass

    @abstractmethod
    def get_npc(self, npc_id: str) -> NPC | None:
        """Get an NPC by ID."""
        pass

    @abstractmethod
    def list_npcs(self) -> list[NPC]:
        """List all registered NPCs."""
        pass

    @abstractmethod
    async def chat(
        self, npc_id: str, message: str, player_id: str = "player_1"
    ) -> ChatResponse:
        """Send a chat message to an NPC and get a response."""
        pass

    @abstractmethod
    def create_default_npcs(self) -> list[NPC]:
        """Create and register default NPCs."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about NPC interactions."""
        pass

    @abstractmethod
    async def save_npcs_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save NPC state to disk."""
        pass

    @abstractmethod
    async def load_npcs_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load NPC state from disk. Returns False if no saved state exists."""
        pass


# ============================================================================
# Game Event Bus Interface
# ============================================================================


EventHandler = Any


@runtime_checkable
class IGameEventBus(Protocol):
    """Protocol for the in-game publish/subscribe event bus."""

    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def publish(self, event_type: str, data: dict[str, Any] | None = None) -> None: ...


# ============================================================================
# Ollama Client Interface
# ============================================================================


class IOllamaClient(ABC):
    """Abstract interface for Ollama HTTP client."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if Ollama server is healthy."""
        pass

    @abstractmethod
    async def wait_for_ready(
        self, max_wait: int = 30, check_interval: float = 0.5
    ) -> bool:
        """Wait for Ollama server to become ready."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
        stream: bool = False,
    ) -> Any:
        """Generate text using a model."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
    ) -> AsyncIterator[str]:
        """Generate text using a model, yielding streamed chunks."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "phi3:mini",
        temperature: float = 0.7,
        max_tokens: int = 200,
    ) -> str:
        """Chat completion (multi-turn conversation)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        pass

    async def __aenter__(self) -> "IOllamaClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# ============================================================================
# Process Manager Interface
# ============================================================================


class IProcessManager(ABC):
    """Abstract interface for Ollama process management."""

    @abstractmethod
    async def start(self) -> bool:
        """Start the Ollama server process."""
        pass

    @abstractmethod
    async def stop(self, timeout: int = 10) -> bool:
        """Stop the Ollama server process."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the Ollama server process is running."""
        pass

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Get status information about the process."""
        pass
