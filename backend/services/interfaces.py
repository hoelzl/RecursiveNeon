"""
Service Interfaces for Dependency Injection

This module defines abstract interfaces (protocols) for all backend services.
These interfaces enable:
- Dependency injection
- Mocking in tests
- Loose coupling between components
- Clear service contracts
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator, Protocol
from dataclasses import dataclass

from models.npc import NPC, ChatResponse


# ============================================================================
# LLM Interface (for LangChain compatibility)
# ============================================================================

class LLMInterface(Protocol):
    """
    Protocol for Language Model providers.

    This interface matches the LangChain LLM interface, allowing us to
    inject different LLM implementations (real or mock) into NPCManager.
    """

    def invoke(self, messages: Any) -> Any:
        """Synchronously invoke the LLM"""
        ...

    async def ainvoke(self, messages: Any) -> Any:
        """Asynchronously invoke the LLM"""
        ...


# ============================================================================
# NPC Manager Interface
# ============================================================================

class INPCManager(ABC):
    """
    Abstract interface for NPC management.

    Defines the contract for managing NPCs and their conversations.
    """

    @abstractmethod
    def register_npc(self, npc: NPC) -> None:
        """
        Register a new NPC.

        Args:
            npc: The NPC instance to register
        """
        pass

    @abstractmethod
    def unregister_npc(self, npc_id: str) -> None:
        """
        Unregister an NPC.

        Args:
            npc_id: ID of the NPC to unregister
        """
        pass

    @abstractmethod
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """
        Get an NPC by ID.

        Args:
            npc_id: ID of the NPC to retrieve

        Returns:
            The NPC instance if found, None otherwise
        """
        pass

    @abstractmethod
    def list_npcs(self) -> List[NPC]:
        """
        List all registered NPCs.

        Returns:
            List of all NPC instances
        """
        pass

    @abstractmethod
    async def chat(
        self,
        npc_id: str,
        message: str,
        player_id: str = "player_1"
    ) -> ChatResponse:
        """
        Send a chat message to an NPC and get a response.

        Args:
            npc_id: ID of the NPC to chat with
            message: The message to send
            player_id: ID of the player sending the message

        Returns:
            The NPC's response
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about NPC interactions.

        Returns:
            Dictionary containing stats
        """
        pass


# ============================================================================
# Ollama Client Interface
# ============================================================================

class IOllamaClient(ABC):
    """
    Abstract interface for Ollama HTTP client.

    Defines the contract for communicating with the Ollama server.
    """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if Ollama server is healthy.

        Returns:
            True if server is responding, False otherwise
        """
        pass

    @abstractmethod
    async def wait_for_ready(
        self,
        max_wait: int = 30,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for Ollama server to become ready.

        Args:
            max_wait: Maximum seconds to wait
            check_interval: Seconds between health checks

        Returns:
            True if server became ready, False if timeout
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models on the Ollama server.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any
    ) -> Any:
        """
        Generate text using a model.

        Args:
            model: Name of the model to use
            prompt: The prompt text
            **kwargs: Additional generation parameters

        Returns:
            Generation response
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        pass


# ============================================================================
# Process Manager Interface
# ============================================================================

class IProcessManager(ABC):
    """
    Abstract interface for Ollama process management.

    Defines the contract for managing the Ollama server process lifecycle.
    """

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the Ollama server process.

        Returns:
            True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop(self, timeout: int = 10) -> bool:
        """
        Stop the Ollama server process.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the Ollama server process is running.

        Returns:
            True if process is running, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information about the process.

        Returns:
            Dictionary containing process status
        """
        pass
