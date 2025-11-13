"""
NPC Data Models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NPCPersonality(str, Enum):
    """NPC personality archetypes"""
    FRIENDLY = "friendly"
    MYSTERIOUS = "mysterious"
    GRUMPY = "grumpy"
    ENTHUSIASTIC = "enthusiastic"
    PROFESSIONAL = "professional"
    QUIRKY = "quirky"
    WISE = "wise"
    NERVOUS = "nervous"


class NPCRole(str, Enum):
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
    timestamp: datetime = Field(default_factory=datetime.now)


class NPCMemory(BaseModel):
    """Memory of past interactions with player"""
    npc_id: str
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    facts_learned: List[str] = Field(
        default_factory=list,
        description="Facts the NPC has learned about the player"
    )
    relationship_level: int = Field(
        default=0,
        description="Relationship score (-100 to 100)"
    )
    last_interaction: Optional[datetime] = None


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
        ...,
        description="How they speak (formal, casual, etc.)"
    )
    topics_of_interest: List[str] = Field(
        default_factory=list,
        description="What they like to talk about"
    )
    secrets: List[str] = Field(
        default_factory=list,
        description="Information they might reveal under certain conditions"
    )

    # Appearance (for UI)
    avatar: str = Field(default="👤", description="Emoji or avatar identifier")
    theme_color: str = Field(default="#4a9eff", description="UI theme color")

    # System prompt template
    system_prompt_template: Optional[str] = None

    # Memory
    memory: NPCMemory = Field(default_factory=lambda: NPCMemory(npc_id=""))

    class Config:
        json_schema_extra = {
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
                "theme_color": "#ff6b35"
            }
        }

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

Topics you enjoy discussing: {', '.join(self.topics_of_interest)}

Your relationship with the player is {relationship_desc} (score: {self.memory.relationship_level}).

What you know about the player:
{recent_facts}

Stay in character at all times. Keep responses concise (2-3 sentences typically).
Be {self.personality.value} in your tone and manner of speaking.
"""

    def add_to_memory(self, role: str, content: str):
        """Add a message to conversation history"""
        message = ConversationMessage(role=role, content=content)
        self.memory.conversation_history.append(message)
        self.memory.last_interaction = datetime.now()

        # Keep only last N messages to avoid token overflow
        max_history = 20
        if len(self.memory.conversation_history) > max_history:
            self.memory.conversation_history = self.memory.conversation_history[-max_history:]

    def get_recent_conversation(self, n: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation messages in LLM format"""
        recent = self.memory.conversation_history[-n:]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent
        ]


class NPCListResponse(BaseModel):
    """Response containing list of NPCs"""
    npcs: List[NPC]


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
    timestamp: datetime = Field(default_factory=datetime.now)
