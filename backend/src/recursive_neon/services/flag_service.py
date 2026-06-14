"""Persistent world-flag / quest-state service."""

from __future__ import annotations

import copy
import logging
from typing import Any

from recursive_neon.models.game_state import GameState
from recursive_neon.services.game_event_bus import GameEventBus

logger = logging.getLogger(__name__)


class FlagService:
    """Key/value store for world flags and quest state.

    Mutations are published on the ``GameEventBus``:
        - ``flag.set``   → {"key": str, "value": Any, "old_value": Any | None}
        - ``flag.cleared`` → {"key": str, "old_value": Any | None}

    Values should be JSON-serialisable scalars.  The service does not
    enforce this at runtime, but persistence will fail loudly if a value
    cannot be serialised.
    """

    def __init__(
        self,
        game_state: GameState,
        event_bus: GameEventBus,
    ) -> None:
        self._game_state = game_state
        self._event_bus = event_bus

    def set_flag(self, key: str, value: Any = True) -> None:
        """Set *key* to *value* and publish a ``flag.set`` event."""
        old_value = self._game_state.flags.get(key)
        self._game_state.flags[key] = value
        self._event_bus.publish(
            "flag.set",
            {"key": key, "value": value, "old_value": old_value},
        )
        logger.debug("Flag set: %s = %r (was %r)", key, value, old_value)

    def clear_flag(self, key: str) -> None:
        """Remove *key* and publish a ``flag.cleared`` event if it existed."""
        if key not in self._game_state.flags:
            return
        old_value = self._game_state.flags.pop(key)
        self._event_bus.publish(
            "flag.cleared",
            {"key": key, "old_value": old_value},
        )
        logger.debug("Flag cleared: %s (was %r)", key, old_value)

    def get_flag(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if unset."""
        return self._game_state.flags.get(key, default)

    def has_flag(self, key: str) -> bool:
        """Return True if *key* is set."""
        return key in self._game_state.flags

    def list_flags(self) -> dict[str, Any]:
        """Return a shallow copy of all flags."""
        return copy.copy(self._game_state.flags)
