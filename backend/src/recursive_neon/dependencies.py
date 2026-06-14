"""
Dependency Injection Container

Centralized container for managing service dependencies.
Implements the Service Locator pattern for clean dependency injection.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from recursive_neon.config import settings
from recursive_neon.models.game_state import GameState, SystemState
from recursive_neon.models.process import ProcessTable
from recursive_neon.services.app_service import AppService
from recursive_neon.services.game_event_bus import GameEventBus
from recursive_neon.services.interfaces import (
    IAppService,
    IGameEventBus,
    INPCManager,
    IOllamaClient,
    IProcessManager,
    LLMInterface,
)
from recursive_neon.services.npc_manager import NPCManager
from recursive_neon.services.ollama_client import OllamaClient, OllamaLangChainAdapter
from recursive_neon.services.process_manager import OllamaProcessManager

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
    app_service: IAppService
    start_time: datetime
    process_table: ProcessTable = field(default_factory=ProcessTable)
    event_bus: IGameEventBus = field(default_factory=GameEventBus)

    def __repr__(self) -> str:
        return (
            f"ServiceContainer("
            f"process_manager={type(self.process_manager).__name__}, "
            f"ollama_client={type(self.ollama_client).__name__}, "
            f"npc_manager={type(self.npc_manager).__name__}, "
            f"system_state={type(self.system_state).__name__}, "
            f"game_state={type(self.game_state).__name__}, "
            f"app_service={type(self.app_service).__name__}, "
            f"event_bus={type(self.event_bus).__name__}, "
            f"process_table={type(self.process_table).__name__}, "
            f"start_time={self.start_time.isoformat()})"
        )


class ServiceFactory:
    """Factory for creating service instances."""

    @staticmethod
    def create_process_manager(
        binary_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> IProcessManager:
        return OllamaProcessManager(
            binary_path=binary_path
            if binary_path is not None
            else settings.ollama_binary_path,
            host=host if host is not None else settings.ollama_host,
            port=port if port is not None else settings.ollama_port,
        )

    @staticmethod
    def create_ollama_client(
        host: str | None = None,
        port: int | None = None,
        timeout: int | None = None,
    ) -> IOllamaClient:
        return OllamaClient(
            host=host if host is not None else settings.ollama_host,
            port=port if port is not None else settings.ollama_port,
            timeout=timeout if timeout is not None else 60,
        )

    @staticmethod
    def create_npc_manager(
        ollama_client: IOllamaClient | None = None,
        llm: LLMInterface | None = None,
    ) -> INPCManager:
        if llm is not None:
            return NPCManager(llm=llm)
        if ollama_client is None:
            raise TypeError(
                "create_npc_manager requires either an ollama_client or an injected llm"
            )
        adapter = OllamaLangChainAdapter(
            client=ollama_client,
            model=settings.default_model,
            temperature=0.7,
            max_tokens=settings.max_response_tokens,
        )
        return NPCManager(llm=adapter)

    @classmethod
    async def create_production_container(cls) -> ServiceContainer:
        """Create a service container configured for production use."""
        logger.info("Creating production service container")

        process_manager = cls.create_process_manager()
        ollama_client = cls.create_ollama_client()
        npc_manager = cls.create_npc_manager(ollama_client=ollama_client)

        system_state = SystemState()
        game_state = GameState()
        start_time = datetime.now(tz=UTC)

        app_service = AppService(game_state)

        # Initialize state: try to load from disk, otherwise load initial state
        data_dir = str(settings.data_dir)
        logger.info("Initializing game state...")
        if not await app_service.load_filesystem_from_disk(data_dir):
            initial_fs_path = str(settings.initial_fs_path)
            logger.info(
                f"No saved filesystem found, loading initial state from {initial_fs_path}"
            )
            # load_initial_filesystem is synchronous; run it in a thread so the
            # async event loop is not blocked during startup.
            await asyncio.to_thread(
                app_service.load_initial_filesystem, initial_fs_path
            )
        else:
            logger.info("Filesystem loaded from saved state")

        # Load notes and tasks (non-fatal if missing)
        await app_service.load_notes_from_disk(data_dir)
        await app_service.load_tasks_from_disk(data_dir)

        # Load NPC state from disk, or create defaults
        if not await npc_manager.load_npcs_from_disk(data_dir):
            npc_manager.create_default_npcs()
            logger.info("Created default NPCs")
        else:
            logger.info("NPCs loaded from saved state")

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            start_time=start_time,
            process_table=ProcessTable.with_defaults(),
        )

        logger.info(f"Production container created: {container}")
        return container

    @classmethod
    def create_test_container(
        cls,
        mock_process_manager: IProcessManager | None = None,
        mock_ollama_client: IOllamaClient | None = None,
        mock_npc_manager: INPCManager | None = None,
        mock_system_state: SystemState | None = None,
        mock_game_state: GameState | None = None,
        mock_app_service: AppService | None = None,
        mock_start_time: datetime | None = None,
    ) -> ServiceContainer:
        """Create a service container configured for testing.

        When mocks are not provided, lightweight no-op stubs are used
        instead of real service instances (which would try to connect to
        Ollama, etc.).
        """
        from unittest.mock import AsyncMock, Mock

        logger.info("Creating test service container")

        process_manager = mock_process_manager or Mock(spec=IProcessManager)
        ollama_client = mock_ollama_client or AsyncMock(spec=IOllamaClient)
        npc_manager = mock_npc_manager or Mock(spec=INPCManager)
        system_state = mock_system_state or SystemState()
        game_state = mock_game_state or GameState()
        app_service = mock_app_service or AppService(game_state)
        start_time = mock_start_time or datetime.now(tz=UTC)

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            start_time=start_time,
        )

        logger.info(f"Test container created: {container}")
        return container


# Global container instance
_container: ServiceContainer | None = None


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
