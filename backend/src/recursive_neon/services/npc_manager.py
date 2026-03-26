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
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from recursive_neon.config import settings
from recursive_neon.models.npc import NPC, ChatResponse, NPCPersonality, NPCRole
from recursive_neon.services.interfaces import INPCManager, LLMInterface

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
        ollama_host: str | None = None,
        ollama_port: int | None = None,
    ):
        """
        Initialize NPCManager with dependency injection.

        Args:
            llm: Language model instance (injected dependency). If None, creates default ChatOllama.
            ollama_host: Ollama server host (deprecated, use llm parameter instead)
            ollama_port: Ollama server port (deprecated, use llm parameter instead)
        """
        self.npcs: dict[str, NPC] = {}

        # Support both new dependency injection and legacy initialization
        if llm is not None:
            # New approach: injected dependency
            self.llm = llm
            logger.info("NPCManager initialized with injected LLM")
        else:
            # Legacy approach: create LLM internally (for backward compatibility)
            self.ollama_host = ollama_host or settings.ollama_host
            self.ollama_port = ollama_port or settings.ollama_port
            self.llm = ChatOllama(
                base_url=f"http://{self.ollama_host}:{self.ollama_port}",
                model=settings.default_model,
                temperature=0.7,
            )
            logger.info("NPCManager initialized with default LLM")

    @classmethod
    def create_with_ollama(
        cls, ollama_host: str | None = None, ollama_port: int | None = None
    ) -> "NPCManager":
        """
        Factory method to create NPCManager with Ollama LLM.

        This is a convenience method for production use cases.

        Args:
            ollama_host: Ollama server host
            ollama_port: Ollama server port

        Returns:
            NPCManager instance configured with ChatOllama
        """
        host = ollama_host or settings.ollama_host
        port = ollama_port or settings.ollama_port
        llm = ChatOllama(
            base_url=f"http://{host}:{port}",
            model=settings.default_model,
            temperature=0.7,
        )
        return cls(llm=llm)

    def register_npc(self, npc: NPC):
        """Register a new NPC"""
        self.npcs[npc.id] = npc
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
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=npc.get_system_prompt())
        ]
        for msg in npc.get_recent_conversation(
            n=settings.npc_memory_context_length
        ):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages

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

        try:
            # Add player message to NPC's memory
            max_hist = settings.npc_max_conversation_history
            npc.add_to_memory("user", message, max_history=max_hist)

            # Build chat messages from history (includes the user message
            # just added) and invoke the LLM directly.
            messages = self._build_messages(npc)
            logger.debug(f"Generating response for {npc.name}")
            response = await asyncio.to_thread(self.llm.invoke, messages)

            # Strip think-tags BEFORE storing in memory so they don't
            # pollute conversation history or get fed back to the LLM.
            cleaned = _strip_think_tags(response.content).strip()

            # Add cleaned response to NPC's memory
            npc.add_to_memory("assistant", cleaned, max_history=max_hist)

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

            return ChatResponse(npc_id=npc.id, npc_name=npc.name, message=cleaned)

        except Exception as e:
            logger.error(f"Error in chat with {npc.name}: {e}")
            # Return fallback response
            return ChatResponse(
                npc_id=npc.id,
                npc_name=npc.name,
                message="I... I'm not sure what to say. Perhaps we can talk later?",
            )

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

    def save_npcs_to_disk(self, data_dir: str = "backend/game_data") -> None:
        """Save NPC state (definitions + memory) to disk."""
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(data_dir) / "npcs.json"
        npcs_data = [npc.model_dump(mode="json") for npc in self.npcs.values()]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"npcs": npcs_data}, f, indent=2, ensure_ascii=False)

    def load_npcs_from_disk(self, data_dir: str = "backend/game_data") -> bool:
        """Load NPC state from disk. Returns False if missing or corrupt."""
        filepath = Path(data_dir) / "npcs.json"
        if not filepath.exists():
            return False
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            for npc_data in data.get("npcs", []):
                npc = NPC(**npc_data)
                self.register_npc(npc)
            logger.info(f"Loaded {len(self.npcs)} NPCs from disk")
            return True
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError) as e:
            logger.warning("Failed to load NPCs from %s: %s", filepath, e)
            return False
