"""
Game Time Service

This module provides the TimeService, which manages game time independently
from system time, supporting features like:
- Time dilation (speeding up or slowing down time)
- Pausing time
- Manual time jumps
- Persistence across sessions
"""

import time
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel

from recursive_neon.services.interfaces import ITimeService

logger = logging.getLogger(__name__)


class TimeState(BaseModel):
    """State of the game time system."""
    game_time: datetime              # Current game time (UTC)
    time_dilation: float             # Time dilation factor
    is_paused: bool                  # Pause state
    last_real_time: float           # Last real time update (monotonic)
    previous_dilation: float        # Dilation before pause (for resume)


class TimeService(ITimeService):
    """
    Game time management service.

    This service maintains an independent game time that advances separately
    from OS time, with support for time dilation, pausing, and manual time
    manipulation.

    Attributes:
        DEFAULT_GAME_TIME: Default starting time for the game
        DEFAULT_DILATION: Default time dilation factor (1.0 = real-time)
    """

    DEFAULT_GAME_TIME = datetime(2048, 11, 13, 8, 0, 0, tzinfo=timezone.utc)
    DEFAULT_DILATION = 1.0

    def __init__(self, persistence_path: Optional[Path] = None):
        """
        Initialize time service.

        Args:
            persistence_path: Path to save/load time state (optional)
        """
        self.persistence_path = persistence_path
        self._state = TimeState(
            game_time=self.DEFAULT_GAME_TIME,
            time_dilation=self.DEFAULT_DILATION,
            is_paused=False,
            last_real_time=time.monotonic(),
            previous_dilation=self.DEFAULT_DILATION,
        )
        self._update_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Try to load saved state
        if persistence_path and persistence_path.exists():
            try:
                self.load_state()
            except Exception as e:
                logger.warning(f"Failed to load time state: {e}, using defaults")

    def _update_time(self) -> None:
        """Update game time based on elapsed real time."""
        current_real_time = time.monotonic()
        real_elapsed = current_real_time - self._state.last_real_time

        if not self._state.is_paused:
            game_elapsed = timedelta(seconds=real_elapsed * self._state.time_dilation)
            self._state.game_time += game_elapsed

        self._state.last_real_time = current_real_time

    def get_current_time(self) -> datetime:
        """
        Get current game time.

        Returns:
            Current game time as datetime (UTC)
        """
        self._update_time()
        return self._state.game_time

    def get_time_state(self) -> Dict[str, Any]:
        """
        Get complete time state.

        Returns:
            Dictionary containing:
                - current_time: ISO 8601 formatted time
                - time_dilation: Current dilation factor
                - is_paused: Pause state
                - real_time: Real time reference for interpolation
        """
        self._update_time()
        return {
            "current_time": self._state.game_time.isoformat(),
            "time_dilation": self._state.time_dilation,
            "is_paused": self._state.is_paused,
            "real_time": self._state.last_real_time,
        }

    def set_time_dilation(self, dilation: float) -> None:
        """
        Set time dilation factor.

        Args:
            dilation: Time dilation factor (0.0 = paused, 1.0 = real-time, 2.0 = double speed, etc.)

        Raises:
            ValueError: If dilation is negative
        """
        if dilation < 0:
            raise ValueError("Time dilation must be non-negative")

        self._update_time()
        old_dilation = self._state.time_dilation
        self._state.time_dilation = dilation
        self._state.is_paused = (dilation == 0.0)

        if not self._state.is_paused:
            self._state.previous_dilation = dilation

        self._notify_change("dilation_change", {
            "old_dilation": old_dilation,
            "new_dilation": dilation,
        })
        self.save_state()

    def get_time_dilation(self) -> float:
        """
        Get current time dilation.

        Returns:
            Current time dilation factor
        """
        return self._state.time_dilation

    def pause(self) -> None:
        """Pause time (time stops advancing)."""
        if not self._state.is_paused:
            self._update_time()
            self._state.previous_dilation = self._state.time_dilation
            self._state.time_dilation = 0.0
            self._state.is_paused = True
            self._notify_change("pause", {})
            self.save_state()

    def resume(self) -> None:
        """Resume time at previous dilation rate."""
        if self._state.is_paused:
            self._update_time()
            self._state.time_dilation = self._state.previous_dilation
            self._state.is_paused = False
            self._notify_change("resume", {})
            self.save_state()

    def is_paused(self) -> bool:
        """
        Check if paused.

        Returns:
            True if time is paused, False otherwise
        """
        return self._state.is_paused

    def jump_to(self, target_time: datetime) -> None:
        """
        Jump to specific time.

        Args:
            target_time: Target datetime to jump to
        """
        self._update_time()
        old_time = self._state.game_time
        self._state.game_time = target_time.replace(tzinfo=timezone.utc)
        self._notify_change("manual_jump", {
            "old_time": old_time.isoformat(),
            "new_time": self._state.game_time.isoformat(),
        })
        self.save_state()

    def advance(self, duration: timedelta) -> None:
        """
        Advance time by duration.

        Args:
            duration: Duration to advance time by
        """
        self._update_time()
        self._state.game_time += duration
        self._notify_change("manual_advance", {
            "duration": duration.total_seconds(),
        })
        self.save_state()

    def rewind(self, duration: timedelta) -> None:
        """
        Rewind time by duration.

        Args:
            duration: Duration to rewind time by
        """
        self._update_time()
        self._state.game_time -= duration
        self._notify_change("manual_rewind", {
            "duration": duration.total_seconds(),
        })
        self.save_state()

    def reset_to_default(self) -> None:
        """Reset to defaults."""
        self._state.game_time = self.DEFAULT_GAME_TIME
        self._state.time_dilation = self.DEFAULT_DILATION
        self._state.is_paused = False
        self._state.last_real_time = time.monotonic()
        self._state.previous_dilation = self.DEFAULT_DILATION
        self._notify_change("reset", {})
        self.save_state()

    def save_state(self) -> None:
        """Save state to disk."""
        if not self.persistence_path:
            return

        try:
            self._update_time()
            data = {
                "game_time": self._state.game_time.isoformat(),
                "time_dilation": self._state.time_dilation,
                "is_paused": self._state.is_paused,
                "previous_dilation": self._state.previous_dilation,
            }

            # Atomic write
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.persistence_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.persistence_path)

            logger.debug(f"Saved time state to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save time state: {e}")

    def load_state(self) -> None:
        """Load state from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            self._state.game_time = datetime.fromisoformat(data["game_time"])
            self._state.time_dilation = data["time_dilation"]
            self._state.is_paused = data["is_paused"]
            self._state.previous_dilation = data.get("previous_dilation", self.DEFAULT_DILATION)
            self._state.last_real_time = time.monotonic()

            logger.info(f"Loaded time state from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load time state: {e}")
            raise

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to time change events.

        Args:
            callback: Function to call when time state changes
        """
        self._update_callbacks.append(callback)

    def _notify_change(self, change_type: str, details: Dict[str, Any]) -> None:
        """
        Notify subscribers of time change.

        Args:
            change_type: Type of change (e.g., "pause", "dilation_change")
            details: Additional details about the change
        """
        event = {
            "type": change_type,
            "state": self.get_time_state(),
            "details": details,
        }
        for callback in self._update_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in time change callback: {e}")
