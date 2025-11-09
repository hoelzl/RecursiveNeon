"""
NPC Manager - Orchestrates NPC conversations using LangChain
"""
import logging
import asyncio
from typing import Dict, List, Optional
from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

from ..models.npc import NPC, NPCPersonality, NPCRole, ChatResponse
from ..config import settings

logger = logging.getLogger(__name__)


class NPCManager:
    """
    Manages all NPCs and their conversations

    Uses LangChain for:
    - Conversation management
    - Memory/context handling
    - Prompt templating
    """

    def __init__(self, ollama_host: str = None, ollama_port: int = None):
        self.ollama_host = ollama_host or settings.ollama_host
        self.ollama_port = ollama_port or settings.ollama_port
        self.npcs: Dict[str, NPC] = {}
        self.chains: Dict[str, ConversationChain] = {}

        # Initialize LangChain LLM
        self.llm = ChatOllama(
            base_url=f"http://{self.ollama_host}:{self.ollama_port}",
            model=settings.default_model,
            temperature=0.7,
        )

        logger.info("NPCManager initialized")

    def register_npc(self, npc: NPC):
        """Register a new NPC"""
        self.npcs[npc.id] = npc

        # Create conversation chain for this NPC
        prompt = PromptTemplate(
            input_variables=["history", "input"],
            template=f"""{npc.get_system_prompt()}

Previous conversation:
{{history}}

Player: {{input}}
{npc.name}:"""
        )

        memory = ConversationBufferMemory()

        # Load existing conversation history into memory
        for msg in npc.get_recent_conversation():
            if msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.chat_memory.add_ai_message(msg["content"])

        self.chains[npc.id] = ConversationChain(
            llm=self.llm,
            prompt=prompt,
            memory=memory,
            verbose=False
        )

        logger.info(f"Registered NPC: {npc.name} ({npc.id})")

    def unregister_npc(self, npc_id: str):
        """Remove an NPC"""
        if npc_id in self.npcs:
            del self.npcs[npc_id]
        if npc_id in self.chains:
            del self.chains[npc_id]
        logger.info(f"Unregistered NPC: {npc_id}")

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get NPC by ID"""
        return self.npcs.get(npc_id)

    def list_npcs(self) -> List[NPC]:
        """Get list of all NPCs"""
        return list(self.npcs.values())

    async def chat(self, npc_id: str, message: str, player_id: str = "player_1") -> ChatResponse:
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

        chain = self.chains.get(npc_id)
        if not chain:
            raise ValueError(f"Conversation chain not found for NPC: {npc_id}")

        try:
            # Add player message to NPC's memory
            npc.add_to_memory("user", message)

            # Generate response using LangChain
            logger.debug(f"Generating response for {npc.name}")
            response = await asyncio.to_thread(
                chain.predict,
                input=message
            )

            # Add response to NPC's memory
            npc.add_to_memory("assistant", response)

            # Update relationship based on sentiment (simple heuristic)
            # In a real game, this would be more sophisticated
            if any(word in message.lower() for word in ["thank", "please", "appreciate"]):
                npc.memory.relationship_level = min(100, npc.memory.relationship_level + 1)
            elif any(word in message.lower() for word in ["stupid", "hate", "idiot"]):
                npc.memory.relationship_level = max(-100, npc.memory.relationship_level - 5)

            return ChatResponse(
                npc_id=npc.id,
                npc_name=npc.name,
                message=response.strip()
            )

        except Exception as e:
            logger.error(f"Error in chat with {npc.name}: {e}")
            # Return fallback response
            return ChatResponse(
                npc_id=npc.id,
                npc_name=npc.name,
                message="I... I'm not sure what to say. Perhaps we can talk later?"
            )

    def create_default_npcs(self) -> List[NPC]:
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
                topics_of_interest=["building directory", "recent events", "local news"],
                avatar="👩‍💼",
                theme_color="#4a9eff"
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
                topics_of_interest=["security vulnerabilities", "hidden files", "system secrets"],
                secrets=["access to restricted areas", "admin passwords"],
                avatar="🕵️",
                theme_color="#00ff00"
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
                theme_color="#ff6b35"
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
                topics_of_interest=["technical problems", "system architecture", "old stories"],
                secrets=["system backdoors", "hidden maintenance tunnels"],
                avatar="👨‍🔧",
                theme_color="#ff9500"
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
                topics_of_interest=["how things work", "tips and tricks", "getting started"],
                avatar="🤖",
                theme_color="#ff69b4"
            )
        ]

        # Register all default NPCs
        for npc in default_npcs:
            npc.memory.npc_id = npc.id  # Set memory NPC ID
            self.register_npc(npc)

        return default_npcs

    def get_stats(self) -> Dict:
        """Get manager statistics"""
        return {
            "total_npcs": len(self.npcs),
            "npcs": [
                {
                    "id": npc.id,
                    "name": npc.name,
                    "conversation_length": len(npc.memory.conversation_history),
                    "relationship_level": npc.memory.relationship_level,
                    "last_interaction": npc.memory.last_interaction.isoformat() if npc.memory.last_interaction else None
                }
                for npc in self.npcs.values()
            ]
        }
