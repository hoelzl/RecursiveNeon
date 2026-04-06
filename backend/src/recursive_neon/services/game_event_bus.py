"""
Game Event Bus — simple pub/sub for in-game events.

Commands and services publish events (e.g., ``editor.buffer_saved``);
game scripts or other components subscribe to react.  This is the
plumbing layer — no game scripts ship in Phase 7e, just the bus.
"""

from __future__ import annotations

import contextlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[str, dict[str, Any]], None]


@dataclass
class GameEventBus:
    """Publish/subscribe event bus for game-world events.

    Thread-safety note: like the rest of the single-player backend,
    this is designed for single-threaded (asyncio) use.  If multi-player
    support is added, callers must serialize access externally.
    """

    _subscribers: dict[str, list[EventHandler]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* to be called when *event_type* is published."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove *handler* from *event_type*.  No-op if not subscribed."""
        handlers = self._subscribers.get(event_type)
        if handlers is not None:
            with contextlib.suppress(ValueError):
                handlers.remove(handler)

    def publish(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Publish *event_type* with *data* to all subscribers.

        Errors in individual handlers are logged but do not prevent
        other handlers from running.
        """
        payload = data or {}
        for handler in list(self._subscribers.get(event_type, [])):
            try:
                handler(event_type, payload)
            except Exception:
                logger.exception("Error in event handler for %s", event_type)
