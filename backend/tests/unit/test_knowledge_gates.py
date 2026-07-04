"""Unit tests for NPC knowledge gates (Phase 9c).

Knowledge gates resolve conditional prompt text — "what you know" vs
"what you do not know" — against the ``FlagService`` and an NPC's
perception buffer.  These tests cover pure gate evaluation, prompt
injection through ``NPCManager._build_messages``, and the seeded
canonical gates on warden / archivist / zero.
"""

from __future__ import annotations

import pytest

from recursive_neon.dependencies import ServiceFactory
from recursive_neon.models.game_state import GameState
from recursive_neon.models.npc import (
    NPC,
    KnowledgeGate,
    NPCMemory,
    NPCPersonality,
    NPCRole,
    PerceptionConfig,
)
from recursive_neon.services.flag_service import FlagService
from recursive_neon.services.game_event_bus import GameEventBus
from recursive_neon.services.npc_manager import NPCManager
from recursive_neon.services.npc_perception import NPCPerceptionTracker


def _gate(
    *,
    topic: str = "t",
    description: str = "OPEN",
    counter_description: str | None = "CLOSED",
    requires_flag: str | None = None,
    requires_perception: str | None = None,
    perception_min_count: int = 1,
    min_relationship: int | None = None,
) -> KnowledgeGate:
    """Build a gate with terse defaults for brevity."""
    return KnowledgeGate(
        topic=topic,
        description=description,
        counter_description=counter_description,
        requires_flag=requires_flag,
        requires_perception=requires_perception,
        perception_min_count=perception_min_count,
        min_relationship=min_relationship,
    )


def _npc(
    npc_id: str = "npc_1",
    *,
    relationship: int = 0,
    gates: list[KnowledgeGate] | None = None,
    subscriptions: list[str] | None = None,
) -> NPC:
    return NPC(
        id=npc_id,
        name=npc_id,
        personality=NPCPersonality.FRIENDLY,
        role=NPCRole.INFORMANT,
        background="bg",
        occupation="occ",
        location="loc",
        greeting="hi",
        conversation_style="friendly",
        memory=NPCMemory(npc_id=npc_id, relationship_level=relationship),
        perception=PerceptionConfig(
            subscriptions=subscriptions or ["shell.*", "filesystem.*"]
        ),
        knowledge_gates=gates or [],
    )


def _manager(
    mock_llm,
    *,
    flag_service: FlagService | None = None,
    perception_tracker: NPCPerceptionTracker | None = None,
) -> NPCManager:
    """Build an NPCManager with the requested services injected directly."""
    return NPCManager(
        llm=mock_llm,
        event_bus=None,
        perception_tracker=perception_tracker,
        flag_service=flag_service,
    )


def _flag_service() -> FlagService:
    return FlagService(game_state=GameState(), event_bus=GameEventBus())


def _tracker() -> NPCPerceptionTracker:
    return NPCPerceptionTracker()


@pytest.mark.unit
class TestGateEvaluation:
    """Pure ``_evaluate_gates`` behaviour against constructed services."""

    def test_unconditional_gate_is_open(self, mock_llm) -> None:
        manager = _manager(mock_llm, flag_service=_flag_service())
        npc = _npc(gates=[_gate()])

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == ["OPEN"]
        assert closed_lines == []

    def test_flag_gate_closed_without_flag(self, mock_llm) -> None:
        manager = _manager(mock_llm, flag_service=_flag_service())
        npc = _npc(gates=[_gate(requires_flag="learned.steadway")])

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == ["CLOSED"]

    def test_flag_gate_open_with_flag(self, mock_llm) -> None:
        fs = _flag_service()
        fs.set_flag("learned.steadway")
        manager = _manager(mock_llm, flag_service=fs)
        npc = _npc(gates=[_gate(requires_flag="learned.steadway")])

        open_lines, _ = manager._evaluate_gates(npc)

        assert open_lines == ["OPEN"]

    def test_flag_gate_closed_without_flag_service(self, mock_llm) -> None:
        # No flag_service injected — graceful degradation to closed.
        manager = _manager(mock_llm, flag_service=None)
        npc = _npc(gates=[_gate(requires_flag="learned.steadway")])

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == ["CLOSED"]

    def test_min_relationship_boundary(self, mock_llm) -> None:
        manager = _manager(mock_llm, flag_service=_flag_service())
        npc_low = _npc(relationship=29, gates=[_gate(min_relationship=30)])
        npc_eq = _npc(relationship=30, gates=[_gate(min_relationship=30)])

        assert manager._evaluate_gates(npc_low)[0] == []
        assert manager._evaluate_gates(npc_eq)[0] == ["OPEN"]

    def test_perception_gate_closed_without_observation(self, mock_llm) -> None:
        tracker = _tracker()
        tracker.register_npc(_npc(gates=[_gate(requires_perception="filesystem.read")]))
        manager = _manager(
            mock_llm, flag_service=_flag_service(), perception_tracker=tracker
        )
        npc = _npc(gates=[_gate(requires_perception="filesystem.read")])

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == ["CLOSED"]

    def test_perception_gate_open_after_matching_event(self, mock_llm) -> None:
        tracker = _tracker()
        npc = _npc(
            gates=[_gate(requires_perception="filesystem.read:/tmp/review/")],
        )
        tracker.register_npc(npc)
        tracker.handle_event(
            "filesystem.read",
            {"file_id": "f1", "path": "/tmp/review/log.txt"},
        )
        manager = _manager(
            mock_llm, flag_service=_flag_service(), perception_tracker=tracker
        )

        open_lines, _ = manager._evaluate_gates(npc)

        assert open_lines == ["OPEN"]

    def test_perception_gate_closed_with_non_matching_path(self, mock_llm) -> None:
        tracker = _tracker()
        npc = _npc(
            gates=[_gate(requires_perception="filesystem.read:/tmp/review/")],
        )
        tracker.register_npc(npc)
        tracker.handle_event(
            "filesystem.read", {"file_id": "f1", "path": "/etc/passwd"}
        )
        manager = _manager(
            mock_llm, flag_service=_flag_service(), perception_tracker=tracker
        )

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == ["CLOSED"]

    def test_perception_min_count(self, mock_llm) -> None:
        tracker = _tracker()
        npc = _npc(
            subscriptions=["npc.chat_sent"],
            gates=[
                _gate(
                    requires_perception="npc.chat_sent",
                    perception_min_count=3,
                )
            ],
        )
        tracker.register_npc(npc)
        for _ in range(2):
            tracker.handle_event(
                "npc.chat_sent", {"target_npc_id": "npc_1", "text": "hi"}
            )
        manager = _manager(
            mock_llm, flag_service=_flag_service(), perception_tracker=tracker
        )

        # Two observations, gate needs three — closed.
        assert manager._evaluate_gates(npc)[0] == []

        tracker.handle_event(
            "npc.chat_sent", {"target_npc_id": "npc_1", "text": "third"}
        )
        # Third observation opens the gate.
        assert manager._evaluate_gates(npc)[0] == ["OPEN"]

    def test_composite_gate_all_conditions_met(self, mock_llm) -> None:
        fs = _flag_service()
        fs.set_flag("archivist_named")
        tracker = _tracker()
        npc = _npc(
            relationship=20,
            gates=[
                _gate(
                    requires_flag="archivist_named",
                    min_relationship=20,
                    requires_perception="filesystem.read:/tmp/review/",
                )
            ],
        )
        tracker.register_npc(npc)
        tracker.handle_event(
            "filesystem.read",
            {"file_id": "f1", "path": "/tmp/review/notes.txt"},
        )
        manager = _manager(mock_llm, flag_service=fs, perception_tracker=tracker)

        assert manager._evaluate_gates(npc)[0] == ["OPEN"]

    def test_composite_gate_any_missing_closes(self, mock_llm) -> None:
        fs = _flag_service()
        fs.set_flag("archivist_named")
        tracker = _tracker()
        npc = _npc(
            relationship=20,
            gates=[
                _gate(
                    requires_flag="archivist_named",
                    min_relationship=20,
                    requires_perception="filesystem.read:/tmp/review/",
                )
            ],
        )
        tracker.register_npc(npc)
        # No matching perception event.
        manager = _manager(mock_llm, flag_service=fs, perception_tracker=tracker)

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == ["CLOSED"]

    def test_closed_gate_without_counter_description_is_silent(self, mock_llm) -> None:
        manager = _manager(mock_llm, flag_service=_flag_service())
        npc = _npc(
            gates=[
                _gate(
                    counter_description=None,
                    requires_flag="never.set",
                )
            ]
        )

        open_lines, closed_lines = manager._evaluate_gates(npc)

        assert open_lines == []
        assert closed_lines == []

    def test_evaluation_is_deterministic(self, mock_llm) -> None:
        fs = _flag_service()
        fs.set_flag("learned.steadway")
        manager = _manager(mock_llm, flag_service=fs)
        npc = _npc(
            relationship=50,
            gates=[
                _gate(
                    requires_flag="learned.steadway",
                    min_relationship=30,
                )
            ],
        )

        first = manager._evaluate_gates(npc)
        second = manager._evaluate_gates(npc)
        third = manager._evaluate_gates(npc)

        assert first == second == third

    def test_shell_command_perception_with_substring_detail(self, mock_llm) -> None:
        tracker = _tracker()
        npc = _npc(
            gates=[_gate(requires_perception="shell.command_run:find -name *.key")],
        )
        tracker.register_npc(npc)
        tracker.handle_event(
            "shell.command_run",
            {"command": "find", "args": ["-name", "*.key"], "cwd": "/"},
        )
        manager = _manager(
            mock_llm, flag_service=_flag_service(), perception_tracker=tracker
        )

        assert manager._evaluate_gates(npc)[0] == ["OPEN"]


@pytest.mark.unit
class TestKnowledgeGatePromptInjection:
    """Gate text surfaces into the system prompt via _build_messages."""

    @pytest.fixture
    def wired_manager(self, mock_llm) -> NPCManager:
        """Manager with a real FlagService and perception tracker wired."""
        return NPCManager(
            llm=mock_llm,
            event_bus=GameEventBus(),
            flag_service=_flag_service(),
        )

    def test_open_gate_description_in_prompt(
        self, mock_llm, wired_manager: NPCManager
    ) -> None:
        npc = _npc(
            gates=[
                _gate(
                    description="You may speak of Steadway.",
                    counter_description="You must hide Steadway.",
                    requires_flag="learned.steadway",
                )
            ]
        )
        wired_manager.register_npc(npc)
        wired_manager._flag_service.set_flag("learned.steadway")

        prompt = wired_manager._build_messages(npc)[0].content

        assert "What you know:" in prompt
        assert "You may speak of Steadway." in prompt
        assert "What you do not know:" not in prompt

    def test_closed_gate_counter_in_prompt(
        self, mock_llm, wired_manager: NPCManager
    ) -> None:
        npc = _npc(
            gates=[
                _gate(
                    description="You may speak of Steadway.",
                    counter_description="You must hide Steadway.",
                    requires_flag="learned.steadway",
                )
            ]
        )
        wired_manager.register_npc(npc)
        # Flag deliberately not set.

        prompt = wired_manager._build_messages(npc)[0].content

        assert "What you do not know:" in prompt
        assert "You must hide Steadway." in prompt
        assert "What you know:" not in prompt

    def test_closed_gate_without_counter_emits_no_section(
        self, mock_llm, wired_manager: NPCManager
    ) -> None:
        npc = _npc(
            gates=[
                _gate(
                    counter_description=None,
                    requires_flag="never.set",
                )
            ]
        )
        wired_manager.register_npc(npc)

        prompt = wired_manager._build_messages(npc)[0].content

        assert "What you know:" not in prompt
        assert "What you do not know:" not in prompt

    def test_gate_flips_when_flag_set_between_calls(
        self, mock_llm, wired_manager: NPCManager
    ) -> None:
        npc = _npc(
            gates=[
                _gate(
                    description="OPEN TEXT",
                    counter_description="CLOSED TEXT",
                    requires_flag="flipped",
                )
            ]
        )
        wired_manager.register_npc(npc)

        closed_prompt = wired_manager._build_messages(npc)[0].content
        assert "CLOSED TEXT" in closed_prompt
        assert "OPEN TEXT" not in closed_prompt

        wired_manager._flag_service.set_flag("flipped")
        open_prompt = wired_manager._build_messages(npc)[0].content
        assert "OPEN TEXT" in open_prompt
        assert "CLOSED TEXT" not in open_prompt

    def test_contradictory_truths_across_npcs(
        self, mock_llm, wired_manager: NPCManager
    ) -> None:
        """The architectural test: same topic, divergent counter-text."""
        warden = _npc(
            npc_id="warden",
            gates=[
                _gate(
                    topic="steadway_business",
                    description="warden-open",
                    counter_description="warden-closed-secret",
                    requires_flag="learned.steadway",
                )
            ],
        )
        archivist = _npc(
            npc_id="archivist",
            gates=[
                _gate(
                    topic="steadway_business",
                    description="archivist-open",
                    counter_description="archivist-closed-stonewall",
                    requires_flag="learned.steadway",
                )
            ],
        )
        wired_manager.register_npc(warden)
        wired_manager.register_npc(archivist)
        # Flag deliberately unset: both gates closed.

        warden_prompt = wired_manager._build_messages(warden)[0].content
        archivist_prompt = wired_manager._build_messages(archivist)[0].content

        assert "warden-closed-secret" in warden_prompt
        assert "archivist-closed-stonewall" in archivist_prompt
        # The whole point: the two NPCs hold divergent truths on the same topic.
        assert warden_prompt != archivist_prompt


@pytest.mark.unit
class TestSeededGates:
    """The canonical warden/archivist/zero NPCs ship well-formed gates."""

    @pytest.fixture
    def seeded_manager(self, mock_llm) -> NPCManager:
        manager = NPCManager(
            llm=mock_llm,
            event_bus=GameEventBus(),
            flag_service=_flag_service(),
        )
        manager.create_default_npcs()
        return manager

    def _gate_topics(self, manager: NPCManager, npc_id: str) -> set[str]:
        npc = manager.get_npc(npc_id)
        assert npc is not None, f"{npc_id} not seeded"
        return {g.topic for g in npc.knowledge_gates}

    def test_warden_seeded_with_steadway_gate(self, seeded_manager) -> None:
        topics = self._gate_topics(seeded_manager, "warden")
        assert "steadway_business" in topics
        assert "warden_self_disclosed" in topics

    def test_archivist_seeded_with_steadway_gate(self, seeded_manager) -> None:
        topics = self._gate_topics(seeded_manager, "archivist")
        assert "steadway_business" in topics
        assert "archivist_brother_revealed" in topics

    def test_zero_seeded_with_honeypot_gate(self, seeded_manager) -> None:
        topics = self._gate_topics(seeded_manager, "zero")
        assert "zero_acknowledges_honeypot" in topics

    def test_seeded_gates_evaluate_without_error(self, seeded_manager) -> None:
        """Every seeded gate resolves cleanly against a fresh game state."""
        for npc in seeded_manager.list_npcs():
            if not npc.knowledge_gates:
                continue
            open_lines, closed_lines = seeded_manager._evaluate_gates(npc)
            # All seeded gates must produce strings (not None), regardless of
            # open/closed state.
            assert all(isinstance(line, str) for line in open_lines)
            assert all(isinstance(line, str) for line in closed_lines)

    def test_seeded_contradictory_truths_on_steadway_topic(
        self, seeded_manager
    ) -> None:
        """Warden and archivist share the steadway_business topic but must
        carry *different* counter-descriptions — the divergent-truth test."""
        warden = seeded_manager.get_npc("warden")
        archivist = seeded_manager.get_npc("archivist")
        assert warden is not None and archivist is not None

        warden_counter = next(
            g.counter_description
            for g in warden.knowledge_gates
            if g.topic == "steadway_business"
        )
        archivist_counter = next(
            g.counter_description
            for g in archivist.knowledge_gates
            if g.topic == "steadway_business"
        )

        assert warden_counter is not None
        assert archivist_counter is not None
        assert warden_counter != archivist_counter

    def test_seeded_gates_visible_in_full_container(self, mock_llm) -> None:
        """End-to-end: a full DI container carries the seeded NPCs and
        their gates through create_test_container + create_npc_manager."""
        container = ServiceFactory.create_test_container(
            mock_npc_manager=ServiceFactory.create_npc_manager(
                llm=mock_llm, flag_service=_flag_service()
            )
        )
        container.npc_manager.create_default_npcs()

        warden = container.npc_manager.get_npc("warden")
        assert warden is not None
        assert any(g.topic == "steadway_business" for g in warden.knowledge_gates)
