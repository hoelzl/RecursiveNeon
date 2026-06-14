"""Tests for the world-flag / quest-state service."""

from __future__ import annotations

from recursive_neon.models.game_state import GameState
from recursive_neon.services.flag_service import FlagService
from recursive_neon.services.game_event_bus import GameEventBus


class TestFlagService:
    def test_set_and_get_flag(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("door.unlocked", True)
        assert service.get_flag("door.unlocked") is True
        assert service.has_flag("door.unlocked") is True

    def test_get_flag_with_default(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        assert service.get_flag("missing", "fallback") == "fallback"
        assert service.has_flag("missing") is False

    def test_set_overwrites_value(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("counter", 1)
        service.set_flag("counter", 2)
        assert service.get_flag("counter") == 2

    def test_clear_flag_removes_it(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("tmp", "value")
        service.clear_flag("tmp")
        assert service.has_flag("tmp") is False
        assert service.get_flag("tmp") is None

    def test_clear_missing_flag_is_no_op(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.clear_flag("never_set")
        assert service.has_flag("never_set") is False

    def test_list_flags_returns_copy(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("a", 1)
        service.set_flag("b", 2)
        flags = service.list_flags()
        assert flags == {"a": 1, "b": 2}
        flags["a"] = 99
        assert service.get_flag("a") == 1

    def test_set_publishes_flag_set_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.set", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("door.unlocked", True)
        assert len(events) == 1
        assert events[0][0] == "flag.set"
        assert events[0][1] == {
            "key": "door.unlocked",
            "value": True,
            "old_value": None,
        }

    def test_set_overwrite_includes_old_value(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append(data)

        bus.subscribe("flag.set", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("x", 1)
        service.set_flag("x", 2)
        assert events[-1] == {"key": "x", "value": 2, "old_value": 1}

    def test_clear_publishes_flag_cleared_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.cleared", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("door.unlocked", True)
        service.clear_flag("door.unlocked")
        assert len(events) == 1
        assert events[0][0] == "flag.cleared"
        assert events[0][1] == {"key": "door.unlocked", "old_value": True}

    def test_clear_missing_does_not_publish(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.cleared", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.clear_flag("missing")
        assert events == []
