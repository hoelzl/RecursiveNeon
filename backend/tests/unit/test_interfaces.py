"""
Tests that the concrete services structurally satisfy their DI interfaces.
"""

from typing import get_type_hints

from recursive_neon.dependencies import ServiceContainer
from recursive_neon.models.game_state import GameState
from recursive_neon.services.app_service import AppService
from recursive_neon.services.game_event_bus import GameEventBus
from recursive_neon.services.interfaces import IAppService, IGameEventBus


def test_app_service_implements_interface():
    app_service = AppService(GameState())
    assert isinstance(app_service, IAppService)


def test_game_event_bus_implements_interface():
    bus = GameEventBus()
    assert isinstance(bus, IGameEventBus)


def test_container_fields_are_interfaces():
    hints = get_type_hints(ServiceContainer)
    assert hints["app_service"] is IAppService
    assert hints["event_bus"] is IGameEventBus
