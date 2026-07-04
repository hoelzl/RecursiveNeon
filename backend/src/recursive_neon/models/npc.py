"""
NPC Data Models
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NPCPersonality(StrEnum):
    """NPC personality archetypes"""

    FRIENDLY = "friendly"
    MYSTERIOUS = "mysterious"
    GRUMPY = "grumpy"
    ENTHUSIASTIC = "enthusiastic"
    PROFESSIONAL = "professional"
    QUIRKY = "quirky"
    WISE = "wise"
    NERVOUS = "nervous"


class NPCRole(StrEnum):
    """NPC roles in the game world"""

    QUEST_GIVER = "quest_giver"
    MERCHANT = "merchant"
    COMPANION = "companion"
    INFORMANT = "informant"
    ANTAGONIST = "antagonist"
    CIVILIAN = "civilian"


class ConversationMessage(BaseModel):
    """A single message in a conversation"""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class NPCMemory(BaseModel):
    """Memory of past interactions with player"""

    npc_id: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    facts_learned: list[str] = Field(
        default_factory=list, description="Facts the NPC has learned about the player"
    )
    relationship_level: int = Field(
        default=0, description="Relationship score (-100 to 100)"
    )
    last_interaction: datetime | None = None


class PerceptionConfig(BaseModel):
    """Configuration for which game events an NPC perceives."""

    subscriptions: list[str] = Field(
        default_factory=list,
        description="Event-type prefixes this NPC subscribes to",
    )
    buffer_size: int = Field(
        default=50, description="Maximum perceived events to retain"
    )
    include_in_prompt: bool = Field(
        default=True, description="Whether to include perceptions in the system prompt"
    )


class KnowledgeGate(BaseModel):
    """A conditional knowledge assertion on an NPC's system prompt.

    Knowledge gates are evaluated at prompt-build time in ``NPCManager``.
    A gate whose conditions are all satisfied is *open*: its
    ``description`` is injected under a "What you know" section.  A gate
    whose conditions are not satisfied is *closed*: its
    ``counter_description`` (if any) is injected under a "What you do not
    know" section; closed gates without a ``counter_description`` are
    silent.

    The model intentionally holds no service references: evaluation is
    performed by ``NPCManager`` against the injected ``FlagService`` and
    the NPC's ``NPCPerceptionTracker``.

    ``requires_perception`` grammar:

        - ``"filesystem.read"``               — any event of that type
        - ``"filesystem.read:/tmp/review/"``  — event_type ``":"`` literal
          detail; for ``filesystem.*`` events the detail is matched as a
          path prefix on ``data["path"]``, and for ``shell.command_run``
          as a substring of the reconstructed command line.
    """

    topic: str = Field(..., description="Gate identifier, e.g. 'steadway_business'")
    description: str = Field(
        ...,
        description="Prompt text injected under 'What you know' when the gate is open",
    )
    counter_description: str | None = Field(
        default=None,
        description="Prompt text injected under 'What you do not know' when closed",
    )
    requires_flag: str | None = Field(
        default=None, description="Flag key that must be truthy for the gate to open"
    )
    requires_perception: str | None = Field(
        default=None,
        description="Event-type or 'event_type:detail' that must have been observed",
    )
    perception_min_count: int = Field(
        default=1, description="Minimum matching observed events for the gate to open"
    )
    min_relationship: int | None = Field(
        default=None,
        description="Floor on NPC.memory.relationship_level for the gate to open",
    )


class NPC(BaseModel):
    """NPC definition"""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    personality: NPCPersonality = Field(..., description="Personality archetype")
    role: NPCRole = Field(..., description="Role in game world")

    # Background
    background: str = Field(..., description="Character background/bio")
    occupation: str = Field(..., description="What they do")
    location: str = Field(..., description="Where they can be found")

    # Behavior
    greeting: str = Field(..., description="Initial greeting message")
    conversation_style: str = Field(
        ..., description="How they speak (formal, casual, etc.)"
    )
    topics_of_interest: list[str] = Field(
        default_factory=list, description="What they like to talk about"
    )
    secrets: list[str] = Field(
        default_factory=list,
        description="Information they might reveal under certain conditions",
    )

    # Appearance (for UI)
    avatar: str = Field(default="👤", description="Emoji or avatar identifier")
    theme_color: str = Field(default="#4a9eff", description="UI theme color")

    # System prompt template
    system_prompt_template: str | None = None

    # Memory
    memory: NPCMemory = Field(default_factory=lambda: NPCMemory(npc_id=""))

    # Perception
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)

    # Knowledge gates (Phase 9c) — evaluated by NPCManager at prompt-build time.
    knowledge_gates: list[KnowledgeGate] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        """Sync memory.npc_id with self.id after construction."""
        if not self.memory.npc_id:
            self.memory.npc_id = self.id

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "merchant_bob",
                "name": "Bob the Merchant",
                "personality": "friendly",
                "role": "merchant",
                "background": "A cheerful merchant who has traveled across many lands.",
                "occupation": "Traveling Merchant",
                "location": "Market Square",
                "greeting": "Greetings, traveler! Care to see my wares?",
                "conversation_style": "warm and welcoming",
                "topics_of_interest": ["trade", "rare items", "travel stories"],
                "secrets": ["knows location of ancient ruins"],
                "avatar": "🧙‍♂️",
                "theme_color": "#ff6b35",
            }
        }
    )

    def get_system_prompt(self) -> str:
        """Generate system prompt for LLM"""
        if self.system_prompt_template:
            return self.system_prompt_template

        # Default system prompt
        relationship_desc = "neutral"
        if self.memory.relationship_level > 50:
            relationship_desc = "friendly and trusting"
        elif self.memory.relationship_level < -50:
            relationship_desc = "cold and distrustful"

        recent_facts = (
            "\n".join(f"- {fact}" for fact in self.memory.facts_learned[-5:])
            if self.memory.facts_learned
            else "No prior knowledge about the player."
        )

        return f"""You are {self.name}, a {self.occupation} in the game world.

Background: {self.background}

Personality: {self.personality.value}
Conversation Style: {self.conversation_style}
Current Location: {self.location}

Topics you enjoy discussing: {", ".join(self.topics_of_interest)}

Your relationship with the player is {relationship_desc} (score: {self.memory.relationship_level}).

What you know about the player:
{recent_facts}

Rules:
- Stay in character at all times. Never break character or mention that you are an AI.
- Keep responses concise: 1-3 sentences. Do not ramble.
- Be {self.personality.value} in your tone and manner of speaking.
- Respond directly to what the player says. No meta-commentary.
"""

    def add_to_memory(self, role: str, content: str, max_history: int = 50) -> None:
        """Add a message to conversation history.

        Args:
            role: 'user' or 'assistant'
            content: Message content
            max_history: Maximum messages to retain. Defaults to 50.
        """
        message = ConversationMessage(role=role, content=content)
        self.memory.conversation_history.append(message)
        self.memory.last_interaction = datetime.now(tz=UTC)

        # Keep only last N messages to avoid unbounded growth
        if len(self.memory.conversation_history) > max_history:
            self.memory.conversation_history = self.memory.conversation_history[
                -max_history:
            ]

    def get_recent_conversation(self, n: int = 10) -> list[dict[str, str]]:
        """Get recent conversation messages in LLM format"""
        recent = self.memory.conversation_history[-n:]
        return [{"role": msg.role, "content": msg.content} for msg in recent]


class NPCListResponse(BaseModel):
    """Response containing list of NPCs"""

    npcs: list[NPC]


class ChatRequest(BaseModel):
    """Request to chat with an NPC"""

    npc_id: str
    message: str
    player_id: str = "player_1"


class ChatResponse(BaseModel):
    """Response from NPC chat"""

    npc_id: str
    npc_name: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
