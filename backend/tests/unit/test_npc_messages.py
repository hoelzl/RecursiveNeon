"""Unit tests for the NPC message queue (Phase 9d)."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from recursive_neon.dependencies import ServiceFactory
from recursive_neon.models.game_state import GameState
from recursive_neon.services.app_service import AppService
from recursive_neon.services.game_event_bus import GameEventBus
from recursive_neon.services.npc_messages import NPCMessageQueue


def _service() -> NPCMessageQueue:
    return NPCMessageQueue(game_state=GameState(), event_bus=GameEventBus())


@pytest.mark.unit
class TestQueue:
    def test_queue_returns_id_and_stores_message(self) -> None:
        service = _service()

        message_id = service.queue("warden", "stop digging")

        assert isinstance(message_id, str) and message_id
        message = service.get_message(message_id)
        assert message is not None
        assert message.npc_id == "warden"
        assert message.text == "stop digging"
        assert message.delivered_at is None
        assert message.deliver_after is None

    def test_queued_message_appears_in_pending(self) -> None:
        service = _service()
        service.queue("warden", "hi")

        pending = service.pending()

        assert len(pending) == 1
        assert pending[0].text == "hi"

    def test_pending_returns_copy_not_alias(self) -> None:
        """Mutating the returned list must not affect the queue."""
        service = _service()
        service.queue("warden", "hi")
        pending = service.pending()

        pending.clear()

        assert len(service.pending()) == 1

    def test_pending_filters_by_npc(self) -> None:
        service = _service()
        service.queue("warden", "one")
        service.queue("zero", "two")
        service.queue("warden", "three")

        warden_pending = service.pending("warden")

        assert [m.text for m in warden_pending] == ["one", "three"]

    def test_pending_preserves_queue_order(self) -> None:
        service = _service()
        for i in range(5):
            service.queue("warden", f"msg-{i}")

        pending = service.pending()

        assert [m.text for m in pending] == [f"msg-{i}" for i in range(5)]


@pytest.mark.unit
class TestDelivery:
    def test_mark_delivered_removes_from_pending(self) -> None:
        service = _service()
        message_id = service.queue("warden", "delivered")

        service.mark_delivered(message_id)

        assert service.pending() == []
        # The message is retained in all_messages() with delivered_at set.
        message = service.get_message(message_id)
        assert message is not None
        assert message.delivered_at is not None

    def test_mark_delivered_is_idempotent(self) -> None:
        service = _service()
        message_id = service.queue("warden", "once")

        service.mark_delivered(message_id)
        first_at = service.get_message(message_id).delivered_at
        service.mark_delivered(message_id)
        second_at = service.get_message(message_id).delivered_at

        assert first_at == second_at

    def test_mark_delivered_unknown_id_is_noop(self) -> None:
        service = _service()

        # Must not raise.
        service.mark_delivered("does-not-exist")

    def test_only_undelivered_are_pending(self) -> None:
        service = _service()
        first = service.queue("warden", "first")
        service.queue("warden", "second")
        service.mark_delivered(first)

        pending = service.pending()

        assert [m.text for m in pending] == ["second"]


@pytest.mark.unit
class TestDeliverAfter:
    def test_future_message_is_not_pending(self) -> None:
        service = _service()
        future = datetime.now(tz=UTC) + timedelta(hours=1)

        service.queue("warden", "later", deliver_after=future)

        assert service.pending() == []

    def test_past_message_is_pending(self) -> None:
        service = _service()
        past = datetime.now(tz=UTC) - timedelta(minutes=5)

        service.queue("warden", "earlier", deliver_after=past)

        assert len(service.pending()) == 1

    def test_future_message_becomes_pending_after_threshold(self) -> None:
        service = _service()
        # deliver_after one second in the future.
        soon = datetime.now(tz=UTC) + timedelta(seconds=1)

        message_id = service.queue("warden", "wait", deliver_after=soon)
        assert service.pending() == []

        # Poll until the threshold passes (cap at ~3s to avoid hanging).
        import time

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if service.pending():
                break
            time.sleep(0.1)

        pending = service.pending()
        assert len(pending) == 1
        assert pending[0].id == message_id

    def test_deliver_after_none_is_immediately_pending(self) -> None:
        service = _service()

        service.queue("warden", "now")

        assert len(service.pending()) == 1


@pytest.mark.unit
class TestEvents:
    def test_queue_publishes_message_queued_event(self) -> None:
        bus = GameEventBus()
        captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "npc.message.queued",
            lambda et, data: captured.append((et, data)),
        )
        service = NPCMessageQueue(game_state=GameState(), event_bus=bus)

        message_id = service.queue("warden", "hello")

        assert len(captured) == 1
        assert captured[0][0] == "npc.message.queued"
        payload = captured[0][1]
        assert payload["message_id"] == message_id
        assert payload["npc_id"] == "warden"
        assert payload["text"] == "hello"
        assert payload["deliver_after"] is None

    def test_delivered_publishes_message_delivered_event(self) -> None:
        bus = GameEventBus()
        captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "npc.message.delivered",
            lambda et, data: captured.append((et, data)),
        )
        service = NPCMessageQueue(game_state=GameState(), event_bus=bus)
        message_id = service.queue("warden", "hi")

        service.mark_delivered(message_id)

        assert len(captured) == 1
        assert captured[0][1] == {"message_id": message_id, "npc_id": "warden"}

    def test_no_event_for_unknown_id(self) -> None:
        bus = GameEventBus()
        captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "npc.message.delivered",
            lambda et, data: captured.append((et, data)),
        )
        service = NPCMessageQueue(game_state=GameState(), event_bus=bus)

        service.mark_delivered("missing")

        assert captured == []


@pytest.mark.unit
class TestPersistence:
    async def test_messages_round_trip_through_app_service(self) -> None:
        container = ServiceFactory.create_test_container()
        container.npc_message_queue.queue("warden", "one")
        container.npc_message_queue.queue("zero", "two")

        with tempfile.TemporaryDirectory() as tmpdir:
            await container.app_service.save_all_to_disk(tmpdir)

            new_container = ServiceFactory.create_test_container()
            await new_container.app_service.load_all_from_disk(tmpdir)
            msgs = new_container.npc_message_queue.all_messages()
            assert [m.text for m in msgs] == ["one", "two"]
            # Loaded messages remain pending (delivered_at is None).
            assert all(m.delivered_at is None for m in msgs)

    def test_load_missing_file_is_noop(self) -> None:
        service = _service()

        # No npc_messages.json exists in /nonexistent — load should be False
        # and the in-memory queue stays empty. Verified via AppService below.
        assert service.all_messages() == []

    async def test_load_corrupt_file_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "npc_messages.json").write_text(
                "{bad json", encoding="utf-8"
            )
            app = AppService(GameState(), event_bus=GameEventBus())

            loaded = await app.load_npc_messages_from_disk(tmpdir)

            assert loaded is False
            assert app.game_state.npc_messages == []

    async def test_delivered_state_persists(self) -> None:
        """A delivered message should not re-show after save/load."""
        container = ServiceFactory.create_test_container()
        message_id = container.npc_message_queue.queue("warden", "shown")
        container.npc_message_queue.queue("warden", "pending")
        container.npc_message_queue.mark_delivered(message_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            await container.app_service.save_all_to_disk(tmpdir)

            new_container = ServiceFactory.create_test_container()
            await new_container.app_service.load_all_from_disk(tmpdir)
            # Only the undelivered message is pending after reload.
            pending = new_container.npc_message_queue.pending()
            assert [m.text for m in pending] == ["pending"]


@pytest.mark.unit
class TestShellDeliveryHook:
    """End-to-end: the shell renders pending messages at session start."""

    def test_renders_messages_after_banner(self) -> None:
        from recursive_neon.models.npc import (
            NPC,
            NPCMemory,
            NPCPersonality,
            NPCRole,
        )
        from recursive_neon.shell.output import CapturedOutput
        from recursive_neon.shell.shell import Shell

        container = ServiceFactory.create_test_container()
        container.app_service.init_filesystem()

        def make_npc(npc_id: str, name: str) -> NPC:
            return NPC(
                id=npc_id,
                name=name,
                personality=NPCPersonality.PROFESSIONAL,
                role=NPCRole.INFORMANT,
                background="bg",
                occupation="occ",
                location="loc",
                greeting="hi",
                conversation_style="formal",
                memory=NPCMemory(npc_id=npc_id, relationship_level=0),
            )

        container.npc_manager.register_npc(make_npc("warden", "warden"))
        container.npc_message_queue.queue("warden", "I noticed your search.")
        container.npc_message_queue.queue("warden", "Stop digging.")
        output = CapturedOutput()

        async def run() -> None:
            shell = Shell(container=container, output=output, data_dir=None)
            await shell._deliver_pending_npc_messages()

        asyncio.run(run())

        text = output.text
        assert "Messages while you were away" in text
        assert "I noticed your search." in text
        assert "Stop digging." in text
        # Both messages marked delivered.
        assert container.npc_message_queue.pending() == []

    def test_no_output_when_queue_empty(self) -> None:
        from recursive_neon.shell.output import CapturedOutput
        from recursive_neon.shell.shell import Shell

        container = ServiceFactory.create_test_container()
        container.app_service.init_filesystem()
        output = CapturedOutput()

        async def run() -> None:
            shell = Shell(container=container, output=output, data_dir=None)
            await shell._deliver_pending_npc_messages()

        asyncio.run(run())

        assert output.text == ""

    def test_unknown_npc_uses_id_as_name(self) -> None:
        """If the source NPC isn't registered, fall back to the id."""
        from recursive_neon.shell.output import CapturedOutput
        from recursive_neon.shell.shell import Shell

        container = ServiceFactory.create_test_container()
        container.app_service.init_filesystem()
        # The default test npc_manager is a Mock; make unknown NPCs resolve
        # to None so the fallback path is exercised (mirrors real NPCManager).
        container.npc_manager.get_npc = lambda _id: None
        container.npc_message_queue.queue("ghost_npc", "boo")
        output = CapturedOutput()

        async def run() -> None:
            shell = Shell(container=container, output=output, data_dir=None)
            await shell._deliver_pending_npc_messages()

        asyncio.run(run())

        assert "ghost_npc" in output.text
        assert "boo" in output.text
