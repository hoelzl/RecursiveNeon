"""Tests for GameEventBus — simple pub/sub for in-game events."""

from recursive_neon.services.game_event_bus import GameEventBus


class TestPublishSubscribe:
    def test_subscribe_and_publish(self):
        bus = GameEventBus()
        received = []
        bus.subscribe("test.event", lambda t, d: received.append((t, d)))
        bus.publish("test.event", {"key": "value"})
        assert received == [("test.event", {"key": "value"})]

    def test_multiple_subscribers(self):
        bus = GameEventBus()
        a, b = [], []
        bus.subscribe("x", lambda t, d: a.append(d))
        bus.subscribe("x", lambda t, d: b.append(d))
        bus.publish("x", {"n": 1})
        assert len(a) == 1
        assert len(b) == 1

    def test_publish_no_subscribers(self):
        bus = GameEventBus()
        bus.publish("nothing")  # should not raise

    def test_publish_default_data(self):
        bus = GameEventBus()
        received = []
        bus.subscribe("e", lambda t, d: received.append(d))
        bus.publish("e")
        assert received == [{}]

    def test_unsubscribe(self):
        bus = GameEventBus()
        calls = []
        handler = lambda t, d: calls.append(1)  # noqa: E731
        bus.subscribe("e", handler)
        bus.unsubscribe("e", handler)
        bus.publish("e")
        assert calls == []

    def test_unsubscribe_nonexistent_handler(self):
        bus = GameEventBus()
        bus.unsubscribe("e", lambda t, d: None)  # no-op

    def test_unsubscribe_nonexistent_event(self):
        bus = GameEventBus()
        bus.unsubscribe("nope", lambda t, d: None)  # no-op

    def test_error_in_handler_does_not_block_others(self):
        bus = GameEventBus()
        received = []

        def bad_handler(t, d):
            raise RuntimeError("boom")

        bus.subscribe("e", bad_handler)
        bus.subscribe("e", lambda t, d: received.append(d))
        bus.publish("e", {"ok": True})
        assert received == [{"ok": True}]

    def test_different_event_types_isolated(self):
        bus = GameEventBus()
        a_calls, b_calls = [], []
        bus.subscribe("a", lambda t, d: a_calls.append(1))
        bus.subscribe("b", lambda t, d: b_calls.append(1))
        bus.publish("a")
        assert len(a_calls) == 1
        assert len(b_calls) == 0

    def test_multiple_publishes(self):
        bus = GameEventBus()
        calls = []
        bus.subscribe("e", lambda t, d: calls.append(d))
        bus.publish("e", {"n": 1})
        bus.publish("e", {"n": 2})
        assert len(calls) == 2
        assert calls[0]["n"] == 1
        assert calls[1]["n"] == 2
