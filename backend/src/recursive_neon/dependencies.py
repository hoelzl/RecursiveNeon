"""
Dependency Injection Container

Centralized container for managing service dependencies.
Implements the Service Locator pattern for clean dependency injection.
"""
from dataclasses import dataclass
from typing import Optional
import logging
from datetime import datetime

from langchain_ollama import ChatOllama

from recursive_neon.services.interfaces import INPCManager, IOllamaClient, IProcessManager
from recursive_neon.services.npc_manager import NPCManager
from recursive_neon.services.ollama_client import OllamaClient
from recursive_neon.services.process_manager import OllamaProcessManager
from recursive_neon.services.app_service import AppService
from recursive_neon.models.game_state import SystemState, GameState
from recursive_neon.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """
    Container for all application services.

    Holds singleton instances of all services and manages their lifecycle.
    """
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    system_state: SystemState
    game_state: GameState
    app_service: AppService
    start_time: datetime

    def __repr__(self) -> str:
        return (
            f"ServiceContainer("
            f"process_manager={type(self.process_manager).__name__}, "
            f"ollama_client={type(self.ollama_client).__name__}, "
            f"npc_manager={type(self.npc_manager).__name__})"
        )


class ServiceFactory:
    """Factory for creating service instances."""

    @staticmethod
    def create_process_manager(
        binary_path: str = None,
        host: str = None,
        port: int = None
    ) -> IProcessManager:
        return OllamaProcessManager(
            binary_path=binary_path or settings.ollama_binary_path,
            host=host or settings.ollama_host,
            port=port or settings.ollama_port
        )

    @staticmethod
    def create_ollama_client(
        host: str = None,
        port: int = None,
        timeout: int = None
    ) -> IOllamaClient:
        return OllamaClient(
            host=host or settings.ollama_host,
            port=port or settings.ollama_port,
            timeout=timeout or 60
        )

    @staticmethod
    def create_npc_manager(
        llm: Optional[any] = None,
        ollama_host: str = None,
        ollama_port: int = None
    ) -> INPCManager:
        if llm is None:
            host = ollama_host or settings.ollama_host
            port = ollama_port or settings.ollama_port
            llm = ChatOllama(
                base_url=f"http://{host}:{port}",
                model=settings.default_model,
                temperature=0.7,
            )
        return NPCManager(llm=llm)

    @classmethod
    def create_production_container(cls) -> ServiceContainer:
        """Create a service container configured for production use."""
        logger.info("Creating production service container")

        process_manager = cls.create_process_manager()
        ollama_client = cls.create_ollama_client()
        npc_manager = cls.create_npc_manager()

        system_state = SystemState()
        game_state = GameState()
        start_time = datetime.now()

        app_service = AppService(game_state)

        # Initialize filesystem: try to load from disk, otherwise load initial state
        logger.info("Initializing in-game filesystem...")
        if not app_service.load_filesystem_from_disk():
            initial_fs_path = str(settings.initial_fs_path)
            logger.info(f"No saved filesystem found, loading initial state from {initial_fs_path}")
            app_service.load_initial_filesystem(initial_fs_path)
        else:
            logger.info("Filesystem loaded from saved state")

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            start_time=start_time
        )

        logger.info(f"Production container created: {container}")
        return container

    @classmethod
    def create_test_container(
        cls,
        mock_process_manager: Optional[IProcessManager] = None,
        mock_ollama_client: Optional[IOllamaClient] = None,
        mock_npc_manager: Optional[INPCManager] = None,
        mock_system_state: Optional[SystemState] = None,
        mock_game_state: Optional[GameState] = None,
        mock_app_service: Optional[AppService] = None,
        mock_start_time: Optional[datetime] = None
    ) -> ServiceContainer:
        """Create a service container configured for testing."""
        logger.info("Creating test service container")

        process_manager = mock_process_manager or cls.create_process_manager()
        ollama_client = mock_ollama_client or cls.create_ollama_client()
        npc_manager = mock_npc_manager or cls.create_npc_manager()
        system_state = mock_system_state or SystemState()
        game_state = mock_game_state or GameState()
        app_service = mock_app_service or AppService(game_state)
        start_time = mock_start_time or datetime.now()

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            start_time=start_time
        )

        logger.info(f"Test container created: {container}")
        return container


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container (for FastAPI dependency injection)."""
    if _container is None:
        raise RuntimeError(
            "Service container not initialized. "
            "Call initialize_container() during app startup."
        )
    return _container


def initialize_container(container: ServiceContainer) -> None:
    """Initialize the global service container (called once at startup)."""
    global _container
    _container = container
    logger.info("Global service container initialized")


def reset_container() -> None:
    """Reset the global service container (for testing)."""
    global _container
    _container = None
    logger.info("Global service container reset")
