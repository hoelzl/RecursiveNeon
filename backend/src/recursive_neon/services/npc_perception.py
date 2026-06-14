"""NPC Perception Filter

Tracks game-world events each NPC is configured to perceive, stores them in
bounded per-NPC buffers, and renders a human-readable summary for injection
into NPC system prompts.
"""

from collections import defaultdict, deque
from typing import Any

from recursive_neon.models.npc import NPC, PerceptionConfig


class NPCPerceptionTracker:
    """Accumulates perceived events for registered NPCs.

    Subscriptions are event-type prefixes such as ``shell.*`` or
    ``filesystem.*``.  Chat events (``npc.chat_sent`` / ``npc.chat_received``)
    are filtered to the NPC by default; an NPC can opt into eavesdropping on
    all chat by subscribing to ``npc.chat_sent.all`` /
    ``npc.chat_received.all``.
    """

    def __init__(self) -> None:
        self._configs: dict[str, PerceptionConfig] = {}
        self._buffers: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=NPCPerceptionTracker._default_buffer_size())
        )

    @staticmethod
    def _default_buffer_size() -> int:
        # Deque maxlen is set at creation time, so we use a static default and
        # resize when an NPC is registered with a different size.
        return 50

    def register_npc(self, npc: NPC) -> None:
        """Register an NPC and allocate its bounded perception buffer."""
        self._configs[npc.id] = npc.perception
        size = npc.perception.buffer_size
        existing = self._buffers.get(npc.id)
        if existing is None or existing.maxlen != size:
            new_buffer: deque[str] = deque(maxlen=size)
            if existing:
                new_buffer.extend(existing)
            self._buffers[npc.id] = new_buffer

    def handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Process a published event for every registered NPC."""
        for npc_id, config in self._configs.items():
            if not config.include_in_prompt:
                continue
            if not self._is_subscribed(npc_id, config, event_type, data):
                continue
            summary = self._format_event(event_type, data)
            if summary:
                self._buffers[npc_id].append(summary)

    def render_for(self, npc_id: str) -> str:
        """Return a newline-separated summary of recent perceived events."""
        buffer = self._buffers.get(npc_id)
        if not buffer:
            return ""
        return "\n".join(buffer)

    def clear(self, npc_id: str) -> None:
        """Clear the perception buffer for a single NPC."""
        buffer = self._buffers.get(npc_id)
        if buffer is not None:
            buffer.clear()

    def _is_subscribed(
        self,
        npc_id: str,
        config: PerceptionConfig,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        for subscription in config.subscriptions:
            if not self._subscription_matches(subscription, event_type):
                continue
            if self._requires_own_filter(subscription, event_type):
                key = (
                    "target_npc_id"
                    if event_type == "npc.chat_sent"
                    else "source_npc_id"
                )
                if data.get(key) != npc_id:
                    continue
            return True
        return False

    @staticmethod
    def _subscription_matches(subscription: str, event_type: str) -> bool:
        if subscription == event_type:
            return True
        if subscription.endswith(".*"):
            return event_type.startswith(subscription[:-1])
        if subscription.endswith(".all"):
            base = subscription[:-4]
            return event_type == base or event_type.startswith(base + ".")
        return False

    @staticmethod
    def _requires_own_filter(subscription: str, event_type: str) -> bool:
        """Plain chat subscriptions only deliver events involving the NPC."""
        return (
            event_type in ("npc.chat_sent", "npc.chat_received")
            and subscription == event_type
        )

    @staticmethod
    def _format_event(event_type: str, data: dict[str, Any]) -> str:
        if event_type == "shell.command_run":
            command = data.get("command", "")
            args = data.get("args", [])
            cwd = data.get("cwd", "/")
            cmd_line = " ".join([command, *args]) if args else command
            return f"Player ran `{cmd_line}` in {cwd}"

        if event_type == "filesystem.read":
            return f"Player read `{data.get('path', '/')}`"

        if event_type == "filesystem.write":
            operation = data.get("operation", "write")
            path = data.get("path", "/")
            verb = {
                "create": "created",
                "update": "updated",
                "delete": "deleted",
                "copy": "copied",
                "move": "moved",
            }.get(operation, f"{operation}d")
            if operation == "copy":
                source_path = data.get("source_path", "unknown")
                return f"Player copied `{source_path}` to `{path}`"
            if operation == "move":
                old_path = data.get("old_path", "unknown")
                return f"Player moved `{old_path}` to `{path}`"
            return f"Player {verb} `{path}`"

        if event_type == "npc.chat_sent":
            target = data.get("target_npc_id", "someone")
            text = data.get("text", "")
            return f"Player said to {target}: {text}"

        if event_type == "npc.chat_received":
            source = data.get("source_npc_id", "someone")
            text = data.get("text", "")
            return f"{source} said: {text}"

        # Unknown event types are ignored by the renderer.
        return ""
