"""
Dependency Injection Container

This module provides a centralized container for managing service dependencies.
It implements the Service Locator pattern for clean dependency injection throughout
the application.

Benefits:
- Centralized service management
- Easy mocking for tests
- Clear dependency relationships
- Simplified FastAPI dependency injection
"""
from dataclasses import dataclass
from typing import Optional
import logging
from datetime import datetime

from langchain_ollama import ChatOllama

from recursive_neon.services.interfaces import INPCManager, IOllamaClient, IProcessManager, ICalendarService, INotificationService, ITimeService, ISettingsService
from recursive_neon.services.npc_manager import NPCManager
from recursive_neon.services.ollama_client import OllamaClient
from recursive_neon.services.process_manager import OllamaProcessManager
from recursive_neon.services.message_handler import MessageHandler
from recursive_neon.services.app_service import AppService
from recursive_neon.services.calendar_service import CalendarService
from recursive_neon.services.notification_service import NotificationService
from recursive_neon.services.time_service import TimeService
from recursive_neon.services.settings_service import SettingsService
from recursive_neon.models.game_state import SystemState, GameState
from recursive_neon.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """
    Container for all application services.

    This container holds singleton instances of all services and manages their
    lifecycle. Services are lazily initialized when first accessed.

    Attributes:
        process_manager: Manages Ollama server process
        ollama_client: HTTP client for Ollama API
        npc_manager: Manages NPCs and conversations
        message_handler: Handles WebSocket message business logic
        system_state: System state tracking
        game_state: Game state (player data, inventory, app data)
        app_service: Desktop app service
        calendar_service: Calendar event service
        notification_service: Notification management service
        time_service: Game time management service
        settings_service: Application settings service
        start_time: Application start time
    """
    process_manager: IProcessManager
    ollama_client: IOllamaClient
    npc_manager: INPCManager
    message_handler: MessageHandler
    system_state: SystemState
    game_state: GameState
    app_service: AppService
    calendar_service: ICalendarService
    notification_service: INotificationService
    time_service: ITimeService
    settings_service: ISettingsService
    start_time: datetime

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ServiceContainer("
            f"process_manager={type(self.process_manager).__name__}, "
            f"ollama_client={type(self.ollama_client).__name__}, "
            f"npc_manager={type(self.npc_manager).__name__}, "
            f"message_handler={type(self.message_handler).__name__})"
        )


class ServiceFactory:
    """
    Factory for creating service instances.

    This factory encapsulates the logic for creating and wiring up services
    with their dependencies. It supports both production and test configurations.
    """

    @staticmethod
    def create_process_manager(
        binary_path: str = None,
        host: str = None,
        port: int = None
    ) -> IProcessManager:
        """
        Create an Ollama process manager instance.

        Args:
            binary_path: Path to Ollama binary (defaults to settings)
            host: Ollama server host (defaults to settings)
            port: Ollama server port (defaults to settings)

        Returns:
            Process manager instance
        """
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
        """
        Create an Ollama HTTP client instance.

        Args:
            host: Ollama server host (defaults to settings)
            port: Ollama server port (defaults to settings)
            timeout: Request timeout in seconds (defaults to 60)

        Returns:
            Ollama client instance
        """
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
        """
        Create an NPC manager instance with injected LLM.

        Args:
            llm: Language model instance to inject (optional)
            ollama_host: Ollama server host (used if llm not provided)
            ollama_port: Ollama server port (used if llm not provided)

        Returns:
            NPC manager instance
        """
        if llm is None:
            # Create default LLM if not provided
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
        """
        Create a service container configured for production use.

        This creates all services with their default configurations,
        suitable for the production environment.

        Returns:
            Fully configured service container
        """
        logger.info("Creating production service container")

        # Create services in dependency order
        process_manager = cls.create_process_manager()
        ollama_client = cls.create_ollama_client()
        npc_manager = cls.create_npc_manager()

        # Create system state and game state
        system_state = SystemState()
        game_state = GameState()
        start_time = datetime.now()

        # Create app service for desktop apps
        app_service = AppService(game_state)

        # Initialize filesystem: try to load from disk, otherwise load initial state
        logger.info("Initializing in-game filesystem...")
        if not app_service.load_filesystem_from_disk():
            # No saved state, load initial filesystem from source directory
            initial_fs_path = str(settings.initial_fs_path)
            logger.info(f"No saved filesystem found, loading initial state from {initial_fs_path}")
            app_service.load_initial_filesystem(initial_fs_path)
            logger.info("Initial filesystem loaded successfully")
        else:
            logger.info("Filesystem loaded from saved state")

        # Initialize media viewer with default messages if not already configured
        if not game_state.media_viewer.config.messages:
            logger.info("Initializing media viewer with default wellness messages...")
            app_service.initialize_default_media_viewer_messages()
            logger.info("Media viewer initialized")

        # Create calendar service
        calendar_service = CalendarService()

        # Load calendar data from disk if it exists
        calendar_data_path = settings.game_data_path / "calendar.json"
        calendar_service.load_from_disk(str(calendar_data_path))

        # Create notification service
        notification_service = NotificationService(game_state)

        # Create time service
        time_data_path = settings.game_data_path / "time_state.json"
        time_service = TimeService(persistence_path=time_data_path)
        time_service.load_state()  # Load saved state if exists

        # Create settings service
        settings_data_path = settings.game_data_path / "settings.json"
        settings_service = SettingsService(persistence_path=settings_data_path)
        settings_service.load()  # Load saved settings if exists

        # Create message handler with dependencies
        message_handler = MessageHandler(
            npc_manager=npc_manager,
            ollama_client=ollama_client,
            system_state=system_state,
            start_time=start_time,
            app_service=app_service,
            calendar_service=calendar_service,
            time_service=time_service,
            settings_service=settings_service
        )

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            message_handler=message_handler,
            system_state=system_state,
            game_state=game_state,
            app_service=app_service,
            calendar_service=calendar_service,
            notification_service=notification_service,
            time_service=time_service,
            settings_service=settings_service,
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
        mock_message_handler: Optional[MessageHandler] = None,
        mock_system_state: Optional[SystemState] = None,
        mock_start_time: Optional[datetime] = None
    ) -> ServiceContainer:
        """
        Create a service container configured for testing.

        This allows injecting mock services for unit testing.

        Args:
            mock_process_manager: Mock process manager (optional)
            mock_ollama_client: Mock Ollama client (optional)
            mock_npc_manager: Mock NPC manager (optional)
            mock_message_handler: Mock message handler (optional)
            mock_system_state: Mock system state (optional)
            mock_start_time: Mock start time (optional)

        Returns:
            Service container with mock services
        """
        logger.info("Creating test service container")

        # Get or create dependencies
        process_manager = mock_process_manager or cls.create_process_manager()
        ollama_client = mock_ollama_client or cls.create_ollama_client()
        npc_manager = mock_npc_manager or cls.create_npc_manager()
        system_state = mock_system_state or SystemState()
        start_time = mock_start_time or datetime.now()

        # Create message handler if not provided
        message_handler = mock_message_handler or MessageHandler(
            npc_manager=npc_manager,
            ollama_client=ollama_client,
            system_state=system_state,
            start_time=start_time
        )

        container = ServiceContainer(
            process_manager=process_manager,
            ollama_client=ollama_client,
            npc_manager=npc_manager,
            message_handler=message_handler,
            system_state=system_state,
            start_time=start_time
        )

        logger.info(f"Test container created: {container}")
        return container


# Global container instance (will be initialized during app startup)
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the global service container.

    This function is used for FastAPI dependency injection.
    It should only be called after the container has been initialized
    during application startup.

    Returns:
        The global service container

    Raises:
        RuntimeError: If container hasn't been initialized
    """
    if _container is None:
        raise RuntimeError(
            "Service container not initialized. "
            "Call initialize_container() during app startup."
        )
    return _container


def initialize_container(container: ServiceContainer) -> None:
    """
    Initialize the global service container.

    This should be called once during application startup.

    Args:
        container: The service container to use globally
    """
    global _container
    _container = container
    logger.info("Global service container initialized")


def reset_container() -> None:
    """
    Reset the global service container.

    This is primarily useful for testing to ensure a clean state
    between test runs.
    """
    global _container
    _container = None
    logger.info("Global service container reset")
