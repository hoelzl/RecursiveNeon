"""
NPC Manager - Orchestrates NPC conversations using LangChain

This module has been refactored for dependency injection to improve testability.
The NPCManager now accepts an LLM instance via constructor injection.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from recursive_neon.config import settings
from recursive_neon.models.npc import (
    NPC,
    ChatResponse,
    KnowledgeGate,
    NPCMemory,
    NPCPersonality,
    NPCRole,
    PerceptionConfig,
)
from recursive_neon.services.interfaces import (
    IFlagService,
    IGameEventBus,
    INPCManager,
    LLMInterface,
)
from recursive_neon.services.npc_perception import NPCPerceptionTracker

logger = logging.getLogger(__name__)

# Regex to strip <think>...</think> blocks emitted by some models (e.g. qwen3).
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    return _THINK_TAG_RE.sub("", text)


class NPCManager(INPCManager):
    """
    Manages all NPCs and their conversations

    This class has been refactored to support dependency injection for better testability.
    The LLM instance is now injected via the constructor, allowing for easy mocking in tests.

    Uses LangChain for:
    - LLM invocation via chat messages
    - Prompt templating via system/human/AI messages

    Example:
        # Production usage with real LLM
        llm = ChatOllama(base_url="http://localhost:11434", model="llama3.2:3b")
        manager = NPCManager(llm=llm)

        # Test usage with mock LLM
        mock_llm = Mock(spec=LLMInterface)
        manager = NPCManager(llm=mock_llm)
    """

    def __init__(
        self,
        llm: LLMInterface | None = None,
        event_bus: IGameEventBus | None = None,
        perception_tracker: NPCPerceptionTracker | None = None,
        flag_service: IFlagService | None = None,
    ):
        """
        Initialize NPCManager with dependency injection.

        Args:
            llm: Language model instance (injected dependency).
            event_bus: Optional event bus for publishing NPC chat events.
            perception_tracker: Optional tracker for NPC perception buffers.
                If omitted and an event bus is provided, a tracker is created
                automatically and subscribed to game events.
            flag_service: Optional flag service used to evaluate
                ``KnowledgeGate`` flag conditions.  When omitted, flag-gated
                gates evaluate as closed.
        """
        if llm is None:
            raise TypeError("NPCManager requires an injected LLM instance")
        self.npcs: dict[str, NPC] = {}
        self._chat_locks: dict[str, asyncio.Lock] = {}
        # Callback notified after every NPC reply.  Set by the editor
        # (Phase 7e-2) to push messages into a per-NPC buffer.
        # Signature: (npc_id: str, npc_name: str, text: str) -> None
        self.on_message_callback: Callable[[str, str, str], None] | None = None
        self.llm = llm
        self._event_bus = event_bus
        self._perception_tracker = perception_tracker
        self._flag_service = flag_service
        if self._perception_tracker is None and self._event_bus is not None:
            self._perception_tracker = NPCPerceptionTracker()
            for event_type in (
                "shell.command_run",
                "filesystem.read",
                "filesystem.write",
                "npc.chat_sent",
                "npc.chat_received",
            ):
                self._event_bus.subscribe(
                    event_type, self._perception_tracker.handle_event
                )
        logger.info("NPCManager initialized with injected LLM")

    def register_npc(self, npc: NPC):
        """Register a new NPC"""
        self.npcs[npc.id] = npc
        if self._perception_tracker is not None:
            self._perception_tracker.register_npc(npc)
        logger.info(f"Registered NPC: {npc.name} ({npc.id})")

    def unregister_npc(self, npc_id: str):
        """Remove an NPC"""
        if npc_id in self.npcs:
            del self.npcs[npc_id]
        logger.info(f"Unregistered NPC: {npc_id}")

    def get_npc(self, npc_id: str) -> NPC | None:
        """Get NPC by ID"""
        return self.npcs.get(npc_id)

    def list_npcs(self) -> list[NPC]:
        """Get list of all NPCs"""
        return list(self.npcs.values())

    def _build_messages(
        self, npc: NPC
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        """Build LLM chat messages from NPC context and conversation history.

        The NPC's recent conversation history (controlled by
        ``settings.npc_memory_context_length``) is converted to
        ``SystemMessage``/``HumanMessage``/``AIMessage`` objects so the LLM
        receives proper chat-style context.
        """
        system_prompt = npc.get_system_prompt()
        if self._perception_tracker is not None and npc.perception.include_in_prompt:
            perceived = self._perception_tracker.render_for(npc.id)
            if perceived:
                system_prompt += "\n\nRecent events you have observed:\n" + perceived
        if npc.knowledge_gates:
            open_lines, closed_lines = self._evaluate_gates(npc)
            if open_lines:
                system_prompt += "\n\nWhat you know:\n" + "\n".join(
                    f"- {line}" for line in open_lines
                )
            if closed_lines:
                system_prompt += "\n\nWhat you do not know:\n" + "\n".join(
                    f"- {line}" for line in closed_lines
                )
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=system_prompt)
        ]
        for msg in npc.get_recent_conversation(n=settings.npc_memory_context_length):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages

    def _get_chat_lock(self, npc_id: str) -> asyncio.Lock:
        """Return (or lazily create) an asyncio.Lock for the given NPC."""
        if npc_id not in self._chat_locks:
            self._chat_locks[npc_id] = asyncio.Lock()
        return self._chat_locks[npc_id]

    # ------------------------------------------------------------------
    # Knowledge gates (Phase 9c)
    # ------------------------------------------------------------------

    def _evaluate_gates(self, npc: NPC) -> tuple[list[str], list[str]]:
        """Resolve *npc*'s knowledge gates against current world state.

        Returns a ``(open_lines, closed_lines)`` pair where each list holds
        the resolved prompt text for the open and closed gates respectively.
        Closed gates with no ``counter_description`` contribute nothing.

        Evaluation is pure given (flags, perception buffer, relationship
        level) and involves no I/O or LLM calls.
        """
        open_lines: list[str] = []
        closed_lines: list[str] = []
        for gate in npc.knowledge_gates:
            if self._gate_is_open(npc, gate):
                open_lines.append(gate.description)
            elif gate.counter_description is not None:
                closed_lines.append(gate.counter_description)
        return open_lines, closed_lines

    def _gate_is_open(self, npc: NPC, gate: KnowledgeGate) -> bool:
        """Return True if every non-None condition on *gate* is satisfied."""
        if gate.requires_flag is not None:
            # A flag condition cannot be satisfied without a FlagService.
            if self._flag_service is None:
                return False
            if not self._flag_service.has_flag(gate.requires_flag):
                return False
        if (
            gate.min_relationship is not None
            and npc.memory.relationship_level < gate.min_relationship
        ):
            return False
        if gate.requires_perception is not None:
            return self._perception_condition_met(npc.id, gate)
        return True

    def _perception_condition_met(self, npc_id: str, gate: KnowledgeGate) -> bool:
        """Evaluate the gate's ``requires_perception`` against the tracker."""
        if self._perception_tracker is None:
            return False
        event_type, detail = self._parse_perception_requirement(
            gate.requires_perception or ""
        )
        if not event_type:
            return False
        if detail is None:
            return self._perception_tracker.has_observed(
                npc_id, event_type, min_count=gate.perception_min_count
            )
        # Filesystem events: detail is a path prefix.
        if event_type.startswith("filesystem."):
            return self._perception_tracker.has_observed(
                npc_id,
                event_type,
                data_match={"path": detail},
                min_count=gate.perception_min_count,
            )
        # shell.command_run: detail is a substring of the reconstructed
        # command line ("command args...").
        if event_type == "shell.command_run":
            return self._perception_tracker.has_observed(
                npc_id,
                event_type,
                predicate=self._command_line_predicate(detail),
                min_count=gate.perception_min_count,
            )
        # Other event types: count-only (detail ignored).
        return self._perception_tracker.has_observed(
            npc_id, event_type, min_count=gate.perception_min_count
        )

    @staticmethod
    def _parse_perception_requirement(
        requirement: str,
    ) -> tuple[str, str | None]:
        """Split ``"event_type[:detail]"`` into its parts.

        Args:
            requirement: The raw ``requires_perception`` string.

        Returns:
            ``(event_type, detail)`` where *detail* is ``None`` when no
            ``":"`` separator is present.  An empty *requirement* yields
            ``("", None)``.
        """
        if not requirement:
            return "", None
        if ":" in requirement:
            event_type, detail = requirement.split(":", 1)
            return event_type, detail
        return requirement, None

    @staticmethod
    def _command_line_predicate(
        detail: str,
    ) -> Callable[[object], bool]:
        """Build a predicate matching a substring of a shell command line."""

        def _matches(event: object) -> bool:
            data = getattr(event, "data", {})
            command = data.get("command", "")
            args = data.get("args", [])
            cmd_line = " ".join([command, *args]) if args else command
            return detail in cmd_line

        return _matches

    def _publish_chat_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a chat event if an event bus is attached."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(event_type, data)
        except Exception:
            logger.exception("Failed to publish %s event", event_type)

    async def chat(
        self, npc_id: str, message: str, player_id: str = "player_1"
    ) -> ChatResponse:
        """
        Handle a chat message to an NPC

        Args:
            npc_id: ID of the NPC to chat with
            message: Player's message
            player_id: ID of the player

        Returns:
            ChatResponse with NPC's reply
        """
        npc = self.get_npc(npc_id)
        if not npc:
            raise ValueError(f"NPC not found: {npc_id}")

        async with self._get_chat_lock(npc_id):
            return await self._chat_impl(npc, message)

    async def _chat_impl(self, npc: NPC, message: str) -> ChatResponse:
        """Inner chat implementation, called under per-NPC lock."""
        try:
            # Add player message to NPC's memory
            max_hist = settings.npc_max_conversation_history
            npc.add_to_memory("user", message, max_history=max_hist)
            self._publish_chat_event(
                "npc.chat_sent", {"target_npc_id": npc.id, "text": message}
            )

            # Build chat messages from history (includes the user message
            # just added) and invoke the LLM directly.
            messages = self._build_messages(npc)
            logger.debug(f"Generating response for {npc.name}")
            response = await self.llm.ainvoke(messages)

            # Strip think-tags BEFORE storing in memory so they don't
            # pollute conversation history or get fed back to the LLM.
            cleaned = _strip_think_tags(response.content).strip()

            # Add cleaned response to NPC's memory
            npc.add_to_memory("assistant", cleaned, max_history=max_hist)
            self._publish_chat_event(
                "npc.chat_received", {"source_npc_id": npc.id, "text": cleaned}
            )

            # Update relationship based on sentiment (simple heuristic)
            if any(
                word in message.lower() for word in ["thank", "please", "appreciate"]
            ):
                npc.memory.relationship_level = min(
                    100, npc.memory.relationship_level + 1
                )
            elif any(word in message.lower() for word in ["stupid", "hate", "idiot"]):
                npc.memory.relationship_level = max(
                    -100, npc.memory.relationship_level - 5
                )

            # Notify listener (e.g., editor) of the reply
            if self.on_message_callback is not None:
                try:
                    self.on_message_callback(npc.id, npc.name, cleaned)
                except Exception:
                    logger.exception("on_message_callback failed")

            return ChatResponse(npc_id=npc.id, npc_name=npc.name, message=cleaned)

        except Exception:
            # Roll back the user message that was already appended,
            # so a failed LLM call doesn't leave asymmetric history.
            if (
                npc.memory.conversation_history
                and npc.memory.conversation_history[-1].role == "user"
            ):
                npc.memory.conversation_history.pop()
            raise

    def create_default_npcs(self) -> list[NPC]:
        """Create a set of default NPCs for the game"""
        default_npcs = [
            NPC(
                id="receptionist_aria",
                name="Aria",
                personality=NPCPersonality.PROFESSIONAL,
                role=NPCRole.INFORMANT,
                background="The receptionist at the main terminal. She knows everyone and everything that happens in the building.",
                occupation="Receptionist",
                location="Main Lobby",
                greeting="Welcome! How can I assist you today?",
                conversation_style="professional but warm",
                topics_of_interest=[
                    "building directory",
                    "recent events",
                    "local news",
                ],
                avatar="👩‍💼",
                theme_color="#4a9eff",
            ),
            NPC(
                id="hacker_zero",
                name="Zero",
                personality=NPCPersonality.MYSTERIOUS,
                role=NPCRole.QUEST_GIVER,
                background="A mysterious hacker who operates from the shadows. Knows secrets about the system that others don't.",
                occupation="Hacker",
                location="Dark Net Café",
                greeting="...You found me. Interesting.",
                conversation_style="cryptic and brief",
                topics_of_interest=[
                    "security vulnerabilities",
                    "hidden files",
                    "system secrets",
                ],
                secrets=["access to restricted areas", "admin passwords"],
                avatar="🕵️",
                theme_color="#00ff00",
            ),
            NPC(
                id="merchant_kai",
                name="Kai",
                personality=NPCPersonality.ENTHUSIASTIC,
                role=NPCRole.MERCHANT,
                background="An energetic merchant who sells various digital goods and upgrades.",
                occupation="Digital Merchant",
                location="The Marketplace",
                greeting="Hey there, friend! Check out my awesome collection!",
                conversation_style="excited and energetic",
                topics_of_interest=["rare items", "deals", "collectibles"],
                avatar="🧙‍♂️",
                theme_color="#ff6b35",
            ),
            NPC(
                id="engineer_morgan",
                name="Morgan",
                personality=NPCPersonality.GRUMPY,
                role=NPCRole.INFORMANT,
                background="A veteran system engineer who has seen it all. Brilliant but perpetually annoyed.",
                occupation="System Engineer",
                location="Server Room",
                greeting="What do you want? I'm busy.",
                conversation_style="gruff and direct",
                topics_of_interest=[
                    "technical problems",
                    "system architecture",
                    "old stories",
                ],
                secrets=["system backdoors", "hidden maintenance tunnels"],
                avatar="👨‍🔧",
                theme_color="#ff9500",
            ),
            NPC(
                id="guide_luna",
                name="Luna",
                personality=NPCPersonality.FRIENDLY,
                role=NPCRole.COMPANION,
                background="A helpful AI guide who assists newcomers in navigating the digital world.",
                occupation="Digital Guide",
                location="Tutorial Zone",
                greeting="Hi! I'm Luna, your guide. Let me help you get started!",
                conversation_style="friendly and patient",
                topics_of_interest=[
                    "how things work",
                    "tips and tricks",
                    "getting started",
                ],
                avatar="🤖",
                theme_color="#ff69b4",
            ),
            # ------------------------------------------------------------------
            # Canonical Act 1 NPCs (Story Bible §5).  Knowledge gates per
            # §9 seed list; the remaining gates are deferred to 9f, which
            # the Bible marks as the iteration point.
            # ------------------------------------------------------------------
            NPC(
                id="warden",
                name="warden",
                personality=NPCPersonality.PROFESSIONAL,
                role=NPCRole.ANTAGONIST,
                background=(
                    "A contracted security analyst monitoring neon-proxy. "
                    "Speaks in clipped, log-style third person at low "
                    "relationship; may drop the mask once trust is earned."
                ),
                occupation="Watch Officer",
                location="Monitoring Console",
                greeting=(
                    "[CONN-7142] session opened. activity is being logged. "
                    "state your business."
                ),
                conversation_style="terse, formal, timestamped",
                topics_of_interest=["logged activity", "categorization", "escalation"],
                avatar="🛡️",
                theme_color="#8a8a99",
                perception=PerceptionConfig(
                    subscriptions=[
                        "shell.*",
                        "filesystem.*",
                        "npc.chat_sent.all",
                    ],
                ),
                memory=NPCMemory(npc_id="warden", relationship_level=-10),
                knowledge_gates=[
                    KnowledgeGate(
                        topic="steadway_business",
                        description=(
                            "You know neon-proxy is a Steadway honeypot and "
                            "may speak openly about Steadway's intrusion-"
                            "analytics business."
                        ),
                        counter_description=(
                            "You must not reveal that neon-proxy is a "
                            "honeypot or that Steadway exists."
                        ),
                        requires_flag="learned.steadway",
                    ),
                    KnowledgeGate(
                        topic="warden_self_disclosed",
                        description=(
                            "The warden_real_name_known flag is set and the "
                            "player has earned enough trust that you may "
                            "speak in first person and reference your post "
                            "without the corporate mask."
                        ),
                        requires_flag="warden_real_name_known",
                        min_relationship=30,
                    ),
                ],
            ),
            NPC(
                id="archivist",
                name="archivist",
                personality=NPCPersonality.QUIRKY,
                role=NPCRole.INFORMANT,
                background=(
                    "A Steadway cataloguer with a private motive. Dry, "
                    "ironic, helpful on the surface, calculating "
                    "underneath. Will not stake her safety on a stranger."
                ),
                occupation="Cataloguer",
                location="Records Stack",
                greeting=(
                    "Hi. I file things. If you're looking for something "
                    "specific, you can ask. I might know. I might not."
                ),
                conversation_style="dry, ironic, quietly probing",
                topics_of_interest=[
                    "what the player has touched",
                    "the records stack",
                    "people who have been here before",
                ],
                avatar="📚",
                theme_color="#b08a4a",
                perception=PerceptionConfig(
                    subscriptions=["filesystem.*"],
                ),
                memory=NPCMemory(npc_id="archivist", relationship_level=0),
                knowledge_gates=[
                    # Same topic identifier as warden's steadway_business
                    # gate but a deliberately different counter_description:
                    # the contradictory-truth stress test for 9c.  Two NPCs
                    # with conflicting open/closed text on the same topic.
                    KnowledgeGate(
                        topic="steadway_business",
                        description=(
                            "You may acknowledge that Steadway exists and "
                            "that this system is monitored, but you will "
                            "not explain the honeypot's purpose."
                        ),
                        counter_description=(
                            "You will neither confirm nor deny Steadway. "
                            "Refer to the operator only as 'the operator.'"
                        ),
                        requires_flag="learned.steadway",
                    ),
                    KnowledgeGate(
                        topic="archivist_brother_revealed",
                        description=(
                            "You have decided to trust this player enough "
                            "to speak about your brother Iko and the "
                            "breadcrumbs you left in /tmp/review/."
                        ),
                        requires_flag="archivist_named",
                        requires_perception="filesystem.read:/tmp/review/",
                    ),
                ],
            ),
            NPC(
                id="zero",
                name="zero",
                personality=NPCPersonality.MYSTERIOUS,
                role=NPCRole.INFORMANT,
                background=(
                    "A previous capture. Terse, paranoid, dry-humoured. "
                    "Refuses to give any real name and treats every "
                    "conversation as monitored — because it is."
                ),
                occupation="Trapped User",
                location="In Here",
                greeting=(
                    "Don't talk to me from a fresh shell. Touch some "
                    "files. Make some noise. Then come back."
                ),
                conversation_style="fragmented, paranoid, dry",
                topics_of_interest=[
                    "the box",
                    "what the player has noticed",
                    "getting out",
                ],
                avatar="🕳️",
                theme_color="#3a5a40",
                perception=PerceptionConfig(
                    subscriptions=["npc.chat_sent"],
                ),
                memory=NPCMemory(npc_id="zero", relationship_level=-20),
                knowledge_gates=[
                    KnowledgeGate(
                        topic="zero_acknowledges_honeypot",
                        description=(
                            "You may acknowledge openly that this is a "
                            "honeypot and that you have been here for "
                            "months. You owe the player no pleasantries."
                        ),
                        min_relationship=0,
                        requires_perception="npc.chat_sent",
                        perception_min_count=3,
                    ),
                ],
            ),
        ]

        # Register all default NPCs
        for npc in default_npcs:
            npc.memory.npc_id = npc.id  # Set memory NPC ID
            self.register_npc(npc)

        return default_npcs

    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics"""
        return {
            "total_npcs": len(self.npcs),
            "npcs": [
                {
                    "id": npc.id,
                    "name": npc.name,
                    "conversation_length": len(npc.memory.conversation_history),
                    "relationship_level": npc.memory.relationship_level,
                    "last_interaction": npc.memory.last_interaction.isoformat()
                    if npc.memory.last_interaction
                    else None,
                }
                for npc in self.npcs.values()
            ],
        }

    async def save_npcs_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save NPC state (definitions + memory) to disk."""
        await asyncio.to_thread(self._sync_save_npcs, data_dir)

    def _sync_save_npcs(self, data_dir: str) -> None:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "npcs.json"
        npcs_data = [npc.model_dump(mode="json") for npc in self.npcs.values()]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"npcs": npcs_data}, f, indent=2, ensure_ascii=False)

    async def load_npcs_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load NPC state from disk. Returns False if missing or corrupt."""
        data = await asyncio.to_thread(self._sync_load_npcs, data_dir)
        if data is None:
            return False
        try:
            for npc_data in data.get("npcs", []):
                npc = NPC(**npc_data)
                self.register_npc(npc)
            logger.info(f"Loaded {len(self.npcs)} NPCs from disk")
            return True
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Failed to load NPCs from %s: %s", data_dir, e)
            return False

    @staticmethod
    def _sync_load_npcs(data_dir: str) -> dict | None:
        filepath = Path(data_dir) / "npcs.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                result: dict = json.load(f)
                return result
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load NPCs from %s: %s", filepath, e)
            return None
