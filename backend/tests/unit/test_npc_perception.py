"""Unit tests for the NPC perception filter (Phase 9b)."""

import pytest

from recursive_neon.dependencies import ServiceContainer
from recursive_neon.models.game_state import GameState
from recursive_neon.models.npc import NPC, NPCPersonality, NPCRole, PerceptionConfig
from recursive_neon.services.app_service import AppService
from recursive_neon.services.game_event_bus import GameEventBus
from recursive_neon.services.npc_manager import NPCManager
from recursive_neon.services.npc_perception import NPCPerceptionTracker
from recursive_neon.shell.output import Output
from recursive_neon.shell.shell import Shell


def _make_npc(npc_id: str, subscriptions: list[str], buffer_size: int = 50) -> NPC:
    return NPC(
        id=npc_id,
        name=npc_id.replace("_", " ").title(),
        personality=NPCPersonality.FRIENDLY,
        role=NPCRole.INFORMANT,
        background="A test NPC.",
        occupation="Tester",
        location="Test Suite",
        greeting="Hello.",
        conversation_style="friendly",
        perception=PerceptionConfig(
            subscriptions=subscriptions, buffer_size=buffer_size
        ),
    )


@pytest.mark.unit
class TestNPCPerceptionTracker:
    def test_subscription_prefix_matches(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("npc_1", ["shell.*"])
        tracker.register_npc(npc)

        tracker.handle_event(
            "shell.command_run", {"command": "ls", "args": [], "cwd": "/"}
        )
        tracker.handle_event("filesystem.read", {"file_id": "x", "path": "/readme.txt"})

        rendered = tracker.render_for("npc_1")
        assert "Player ran `ls`" in rendered
        assert "readme.txt" not in rendered

    def test_exact_subscription_only_own_chat_by_default(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("zero", ["npc.chat_sent"])
        tracker.register_npc(npc)

        tracker.handle_event(
            "npc.chat_sent", {"target_npc_id": "zero", "text": "hello zero"}
        )
        tracker.handle_event(
            "npc.chat_sent", {"target_npc_id": "warden", "text": "hello warden"}
        )

        rendered = tracker.render_for("zero")
        assert "hello zero" in rendered
        assert "hello warden" not in rendered

    def test_all_subscription_eavesdrops_on_chat(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("warden", ["npc.chat_sent.all"])
        tracker.register_npc(npc)

        tracker.handle_event(
            "npc.chat_sent", {"target_npc_id": "zero", "text": "plotting"}
        )

        rendered = tracker.render_for("warden")
        assert "plotting" in rendered

    def test_buffer_size_eviction(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("npc_1", ["shell.*"], buffer_size=2)
        tracker.register_npc(npc)

        for i in range(3):
            tracker.handle_event(
                "shell.command_run",
                {"command": "cmd", "args": [str(i)], "cwd": "/"},
            )

        rendered = tracker.render_for("npc_1")
        assert "cmd 0" not in rendered
        assert "cmd 1" in rendered
        assert "cmd 2" in rendered

    def test_render_preserves_order(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("npc_1", ["shell.*"])
        tracker.register_npc(npc)

        tracker.handle_event(
            "shell.command_run", {"command": "first", "args": [], "cwd": "/"}
        )
        tracker.handle_event(
            "shell.command_run", {"command": "second", "args": [], "cwd": "/"}
        )

        rendered = tracker.render_for("npc_1")
        assert rendered.index("first") < rendered.index("second")

    def test_cross_npc_isolation(self) -> None:
        tracker = NPCPerceptionTracker()
        warden = _make_npc("warden", ["npc.chat_sent.all"])
        zero = _make_npc("zero", ["npc.chat_sent"])
        archivist = _make_npc("archivist", ["filesystem.*"])
        for npc in (warden, zero, archivist):
            tracker.register_npc(npc)

        tracker.handle_event(
            "npc.chat_sent", {"target_npc_id": "zero", "text": "secret"}
        )

        assert "secret" in tracker.render_for("warden")
        assert "secret" in tracker.render_for("zero")
        assert tracker.render_for("archivist") == ""

    def test_include_in_prompt_false_ignores_events(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("npc_1", ["shell.*"])
        npc.perception.include_in_prompt = False
        tracker.register_npc(npc)

        tracker.handle_event(
            "shell.command_run", {"command": "ls", "args": [], "cwd": "/"}
        )

        assert tracker.render_for("npc_1") == ""

    def test_unknown_event_type_is_ignored(self) -> None:
        tracker = NPCPerceptionTracker()
        npc = _make_npc("npc_1", ["custom.*"])
        tracker.register_npc(npc)

        tracker.handle_event("custom.thing", {"x": 1})

        assert tracker.render_for("npc_1") == ""


@pytest.mark.unit
class TestNPCManagerPerceptionIntegration:
    @pytest.fixture
    def bus(self) -> GameEventBus:
        return GameEventBus()

    @pytest.fixture
    def manager(self, mock_llm, bus: GameEventBus) -> NPCManager:
        return NPCManager(llm=mock_llm, event_bus=bus)

    async def test_publishes_chat_events(
        self, manager: NPCManager, bus: GameEventBus
    ) -> None:
        npc = _make_npc("zero", ["npc.chat_sent"])
        manager.register_npc(npc)

        captured: list[tuple[str, dict]] = []
        for event_type in ("npc.chat_sent", "npc.chat_received"):
            bus.subscribe(
                event_type,
                lambda et, data, captured=captured, t=event_type: captured.append(
                    (t, data)
                ),
            )

        response = await manager.chat("zero", "hello")

        assert response.npc_id == "zero"
        sent = [p for t, p in captured if t == "npc.chat_sent"]
        received = [p for t, p in captured if t == "npc.chat_received"]
        assert len(sent) == 1
        assert sent[0]["target_npc_id"] == "zero"
        assert sent[0]["text"] == "hello"
        assert len(received) == 1
        assert received[0]["source_npc_id"] == "zero"

    async def test_includes_perception_in_system_prompt(
        self, manager: NPCManager, bus: GameEventBus
    ) -> None:
        npc = _make_npc("zero", ["shell.*"])
        manager.register_npc(npc)

        bus.publish(
            "shell.command_run",
            {"command": "find", "args": ["*.key"], "cwd": "/"},
        )

        await manager.chat("zero", "hello")

        call_args = manager.llm.ainvoke.call_args
        messages = call_args[0][0]
        system_content = messages[0].content
        assert "Recent events you have observed:" in system_content
        assert "Player ran `find *.key`" in system_content

    async def test_perception_not_duplicated_across_chat_turns(
        self, manager: NPCManager, bus: GameEventBus
    ) -> None:
        npc = _make_npc("zero", ["shell.*"])
        manager.register_npc(npc)

        bus.publish("shell.command_run", {"command": "ls", "args": [], "cwd": "/"})
        await manager.chat("zero", "hi")
        first_system = manager.llm.ainvoke.call_args[0][0][0].content

        await manager.chat("zero", "again")
        second_system = manager.llm.ainvoke.call_args[0][0][0].content

        # The same single event should appear in both prompts (it is observed
        # state, not conversation history), not duplicated within one prompt.
        assert first_system.count("Player ran `ls`") == 1
        assert second_system.count("Player ran `ls`") == 1


@pytest.mark.unit
class TestAppServiceFilesystemEvents:
    @pytest.fixture
    def bus(self) -> GameEventBus:
        return GameEventBus()

    @pytest.fixture
    def app(self, bus: GameEventBus) -> AppService:
        game_state = GameState()
        service = AppService(game_state, event_bus=bus)
        service.init_filesystem()
        return service

    def test_read_file_publishes_read_event(
        self, app: AppService, bus: GameEventBus
    ) -> None:
        captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "filesystem.read",
            lambda et, data, captured=captured: captured.append((et, data)),
        )

        root = app.get_filesystem_root_id()
        file = app.create_file({"parent_id": root, "name": "a.txt", "content": "hi"})
        app.read_file(file.id)

        assert len(captured) == 1
        assert captured[0][0] == "filesystem.read"
        assert captured[0][1]["file_id"] == file.id
        assert captured[0][1]["path"] == "/a.txt"

    def test_create_update_delete_publish_write_events(
        self, app: AppService, bus: GameEventBus
    ) -> None:
        captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "filesystem.write",
            lambda et, data, captured=captured: captured.append((et, data)),
        )

        root = app.get_filesystem_root_id()
        file = app.create_file({"parent_id": root, "name": "b.txt", "content": "x"})
        app.update_file(file.id, {"content": "y"})
        app.delete_file(file.id)

        ops = [data["operation"] for _, data in captured]
        assert ops == ["create", "update", "delete"]

    def test_copy_and_move_publish_events(
        self, app: AppService, bus: GameEventBus
    ) -> None:
        write_captured: list[tuple[str, dict]] = []
        bus.subscribe(
            "filesystem.write",
            lambda et, data, captured=write_captured: captured.append((et, data)),
        )

        root = app.get_filesystem_root_id()
        dir_a = app.create_directory({"parent_id": root, "name": "dir_a"})
        file = app.create_file({"parent_id": root, "name": "c.txt", "content": "z"})
        copied = app.copy_file(file.id, dir_a.id)
        app.move_file(copied.id, root, new_name="d.txt")

        ops = [data["operation"] for _, data in write_captured]
        assert "copy" in ops
        assert "move" in ops


@pytest.mark.unit
class TestShellCommandRunEvent:
    @pytest.fixture
    def container(self) -> "ServiceContainer":
        from recursive_neon.dependencies import ServiceFactory

        game_state = GameState()
        event_bus = GameEventBus()
        app_service = AppService(game_state, event_bus=event_bus)
        app_service.init_filesystem()
        return ServiceFactory.create_test_container(
            mock_game_state=game_state,
            mock_app_service=app_service,
        )

    def test_publish_command_run(self, container: "ServiceContainer") -> None:
        captured: list[tuple[str, dict]] = []
        container.event_bus.subscribe(
            "shell.command_run",
            lambda et, data, captured=captured: captured.append((et, data)),
        )
        shell = Shell(container=container, output=Output())

        shell._publish_command_run(["ls", "/"])

        assert len(captured) == 1
        event_type, payload = captured[0]
        assert event_type == "shell.command_run"
        assert payload["command"] == "ls"
        assert payload["args"] == ["/"]
        assert payload["cwd"] == "/"
