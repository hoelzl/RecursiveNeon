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
from typing import Any, Dict, List, Protocol

from recursive_neon.models.npc import NPC, ChatResponse

# ============================================================================
# LLM Interface (for LangChain compatibility)
# ============================================================================


class LLMInterface(Protocol):
    """
    Protocol for Language Model providers.

    This interface matches the LangChain BaseChatModel interface, allowing us to
    inject different LLM implementations (real or mock) into NPCManager.
    """

    def invoke(self, input: Any, *args: Any, **kwargs: Any) -> Any:
        """Synchronously invoke the LLM"""
        ...

    async def ainvoke(self, input: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously invoke the LLM"""
        ...


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
    def list_npcs(self) -> List[NPC]:
        """List all registered NPCs."""
        pass

    @abstractmethod
    async def chat(
        self, npc_id: str, message: str, player_id: str = "player_1"
    ) -> ChatResponse:
        """Send a chat message to an NPC and get a response."""
        pass

    @abstractmethod
    def create_default_npcs(self) -> List[NPC]:
        """Create and register default NPCs."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about NPC interactions."""
        pass


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
    async def list_models(self) -> List[str]:
        """List available models on the Ollama server."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str = "phi3:mini",
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
        stream: bool = False,
    ) -> Any:
        """Generate text using a model."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        pass


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
    def get_status(self) -> Dict[str, Any]:
        """Get status information about the process."""
        pass
