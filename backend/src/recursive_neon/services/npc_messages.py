"""Pending NPC→player message queue (Phase 9d).

Holds NPC-originated messages for delivery at the next session start, so
NPCs can initiate contact rather than only responding to ``chat``.

The queue is a thin synchronous mutator over ``game_state.npc_messages``
(mirroring the FlagService pattern from Phase 9a): the service holds no
state of its own, and persistence is owned by ``AppService``.

Events published on the ``GameEventBus``:

    - ``npc.message.queued``    → {"message_id", "npc_id", "text",
                                  "deliver_after": datetime | None}
    - ``npc.message.delivered`` → {"message_id", "npc_id"}

A message is *pending* when ``delivered_at`` is None AND ``deliver_after``
is in the past (or None).  ``pending()`` returns only those messages;
``mark_delivered`` stamps ``delivered_at`` so they do not re-show.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from recursive_neon.models.game_state import GameState
from recursive_neon.models.npc import QueuedMessage
from recursive_neon.services.game_event_bus import GameEventBus

logger = logging.getLogger(__name__)


class NPCMessageQueue:
    """Key/value-ish store for NPC→player messages awaiting delivery."""

    def __init__(
        self,
        game_state: GameState,
        event_bus: GameEventBus,
    ) -> None:
        self._game_state = game_state
        self._event_bus = event_bus

    def queue(
        self,
        npc_id: str,
        text: str,
        deliver_after: datetime | None = None,
    ) -> str:
        """Stage a message for the next session.

        Args:
            npc_id: Source NPC.
            text: Message body.
            deliver_after: Optional time after which the message becomes
                deliverable.  ``None`` (the default) means "deliverable
                immediately at the next session".

        Returns:
            The newly-created message's id.
        """
        message_id = str(uuid.uuid4())
        message = QueuedMessage(
            id=message_id,
            npc_id=npc_id,
            text=text,
            deliver_after=deliver_after,
        )
        self._game_state.npc_messages.append(message)
        self._event_bus.publish(
            "npc.message.queued",
            {
                "message_id": message_id,
                "npc_id": npc_id,
                "text": text,
                "deliver_after": deliver_after,
            },
        )
        logger.debug(
            "Queued message %s from %s (deliver_after=%s)",
            message_id,
            npc_id,
            deliver_after,
        )
        return message_id

    def pending(self, npc_id: str | None = None) -> list[QueuedMessage]:
        """Return undelivered, time-eligible messages in queue order.

        Args:
            npc_id: When given, restrict to messages from this NPC.  When
                ``None`` (the default), return pending messages from all
                NPCs.

        Messages whose ``deliver_after`` is still in the future are
        excluded.  Already-delivered messages are excluded.
        """
        now = datetime.now(tz=UTC)
        pending: list[QueuedMessage] = []
        for message in self._game_state.npc_messages:
            if message.delivered_at is not None:
                continue
            if message.deliver_after is not None and message.deliver_after > now:
                continue
            if npc_id is not None and message.npc_id != npc_id:
                continue
            pending.append(message)
        return pending

    def mark_delivered(self, message_id: str) -> None:
        """Mark *message_id* as shown to the player.

        No-op for unknown ids and for messages already delivered (idempotent).
        """
        for message in self._game_state.npc_messages:
            if message.id == message_id:
                if message.delivered_at is not None:
                    return
                message.delivered_at = datetime.now(tz=UTC)
                self._event_bus.publish(
                    "npc.message.delivered",
                    {"message_id": message_id, "npc_id": message.npc_id},
                )
                logger.debug("Marked message %s delivered", message_id)
                return
        logger.debug("mark_delivered: unknown message id %s", message_id)

    # ------------------------------------------------------------------
    # Introspection helpers (used by tests / debugging)
    # ------------------------------------------------------------------

    def all_messages(self) -> list[QueuedMessage]:
        """Return a shallow copy of every queued message, delivered or not."""
        return list(self._game_state.npc_messages)

    def get_message(self, message_id: str) -> QueuedMessage | None:
        """Return the message with *message_id*, or ``None`` if absent."""
        for message in self._game_state.npc_messages:
            if message.id == message_id:
                return message
        return None

    def clear(self) -> None:
        """Remove every queued message.  Intended for tests / reset hooks."""
        self._game_state.npc_messages.clear()

    def _reset_event_bus(self, event_bus: GameEventBus) -> None:
        """Test helper: swap the bus after construction."""
        self._event_bus = event_bus
