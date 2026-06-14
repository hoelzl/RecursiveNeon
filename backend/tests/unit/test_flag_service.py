"""Tests for the world-flag / quest-state service."""

from __future__ import annotations

import tempfile

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

    def test_set_flag_default_value_is_true(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("feature.enabled")
        assert service.get_flag("feature.enabled") is True

    def test_set_flag_same_value_still_publishes_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append(data)

        bus.subscribe("flag.set", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("x", 1)
        service.set_flag("x", 1)
        assert len(events) == 2
        assert events[0] == {"key": "x", "value": 1, "old_value": None}
        assert events[1] == {"key": "x", "value": 1, "old_value": 1}

    def test_list_flags_empty(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        assert service.list_flags() == {}

    def test_has_flag_false_after_clear(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("tmp", "value")
        assert service.has_flag("tmp") is True
        service.clear_flag("tmp")
        assert service.has_flag("tmp") is False

    def test_multiple_subscribers_receive_flag_set(self):
        game_state = GameState()
        bus = GameEventBus()
        first_events = []
        second_events = []

        bus.subscribe("flag.set", lambda _event_type, data: first_events.append(data))
        bus.subscribe("flag.set", lambda _event_type, data: second_events.append(data))
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("x", 1)
        expected = {"key": "x", "value": 1, "old_value": None}
        assert first_events == [expected]
        assert second_events == [expected]

    def test_multiple_subscribers_receive_flag_cleared(self):
        game_state = GameState()
        bus = GameEventBus()
        first_events = []
        second_events = []

        bus.subscribe(
            "flag.cleared", lambda _event_type, data: first_events.append(data)
        )
        bus.subscribe(
            "flag.cleared", lambda _event_type, data: second_events.append(data)
        )
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("x", 1)
        service.clear_flag("x")
        expected = {"key": "x", "old_value": 1}
        assert first_events == [expected]
        assert second_events == [expected]

    def test_clear_flag_removes_from_underlying_dict(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("x", 1)
        service.clear_flag("x")
        assert "x" not in game_state.flags

    def test_flags_survive_second_service_instance(self):
        game_state = GameState()
        bus = GameEventBus()
        first_service = FlagService(game_state=game_state, event_bus=bus)

        first_service.set_flag("persisted", "value")
        second_service = FlagService(game_state=game_state, event_bus=bus)

        assert second_service.get_flag("persisted") == "value"
        assert second_service.has_flag("persisted") is True

    def test_scalar_values_round_trip(self):
        game_state = GameState()
        service = FlagService(game_state=game_state, event_bus=GameEventBus())

        service.set_flag("string", "hello")
        service.set_flag("integer", 42)
        service.set_flag("boolean", True)
        service.set_flag("floating", 3.14)

        assert service.get_flag("string") == "hello"
        assert service.get_flag("integer") == 42
        assert service.get_flag("boolean") is True
        assert service.get_flag("floating") == 3.14

    def test_clear_none_value_publishes_cleared_event(self):
        game_state = GameState()
        bus = GameEventBus()
        events = []

        def handler(event_type, data):
            events.append((event_type, data))

        bus.subscribe("flag.cleared", handler)
        service = FlagService(game_state=game_state, event_bus=bus)

        service.set_flag("nil_flag", None)
        service.clear_flag("nil_flag")
        assert len(events) == 1
        assert events[0] == (
            "flag.cleared",
            {"key": "nil_flag", "old_value": None},
        )


class TestFlagServicePersistence:
    async def test_flags_round_trip_through_app_service(self):
        from recursive_neon.dependencies import ServiceFactory

        container = ServiceFactory.create_test_container()
        container.flag_service.set_flag("door.unlocked", True)
        container.flag_service.set_flag("counter", 42)

        with tempfile.TemporaryDirectory() as tmpdir:
            await container.app_service.save_all_to_disk(tmpdir)

            new_container = ServiceFactory.create_test_container()
            await new_container.app_service.load_all_from_disk(tmpdir)
            assert new_container.flag_service.get_flag("door.unlocked") is True
            assert new_container.flag_service.get_flag("counter") == 42
