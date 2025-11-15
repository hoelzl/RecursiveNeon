"""
Unit tests for TimeService

Tests the game time management service including:
- Time initialization and defaults
- Time dilation
- Pause and resume
- Manual time manipulation (jump, advance, rewind)
- Persistence
- Callbacks
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from recursive_neon.services.time_service import TimeService


class TestTimeServiceInitialization:
    """Test TimeService initialization and defaults."""

    def test_initialization_with_defaults(self):
        """Test service initializes with default values."""
        service = TimeService()

        assert service.get_time_dilation() == 1.0
        assert not service.is_paused()

        # Time should be close to default (2048-11-13 08:00:00 UTC)
        current_time = service.get_current_time()
        assert current_time.year == 2048
        assert current_time.month == 11
        assert current_time.day == 13
        assert current_time.hour == 8

    def test_initialization_without_persistence_path(self):
        """Test initialization without persistence path."""
        service = TimeService(persistence_path=None)

        assert service.persistence_path is None
        assert service.get_time_dilation() == 1.0


class TestTimeDilation:
    """Test time dilation functionality."""

    def test_set_time_dilation(self):
        """Test setting time dilation."""
        service = TimeService()

        service.set_time_dilation(2.0)
        assert service.get_time_dilation() == 2.0

    def test_set_time_dilation_to_zero(self):
        """Test setting time dilation to zero (pause)."""
        service = TimeService()

        service.set_time_dilation(0.0)
        assert service.get_time_dilation() == 0.0
        assert service.is_paused()

    def test_negative_time_dilation_raises_error(self):
        """Test that negative time dilation raises ValueError."""
        service = TimeService()

        with pytest.raises(ValueError, match="non-negative"):
            service.set_time_dilation(-1.0)

    def test_time_advances_with_dilation(self):
        """Test that time advances at correct rate with dilation."""
        service = TimeService()

        start_time = service.get_current_time()
        service.set_time_dilation(10.0)  # 10x speed

        time.sleep(0.1)  # Sleep 0.1 real seconds

        end_time = service.get_current_time()
        elapsed = (end_time - start_time).total_seconds()

        # Should have advanced ~1 second (0.1 * 10)
        # Allow some tolerance for test execution time
        assert 0.8 < elapsed < 1.5


class TestPauseAndResume:
    """Test pause and resume functionality."""

    def test_pause(self):
        """Test pausing time."""
        service = TimeService()

        assert not service.is_paused()

        service.pause()

        assert service.is_paused()
        assert service.get_time_dilation() == 0.0

    def test_time_stops_when_paused(self):
        """Test that time doesn't advance when paused."""
        service = TimeService()

        service.pause()
        time_before = service.get_current_time()

        time.sleep(0.2)

        time_after = service.get_current_time()

        # Time should not have advanced
        assert time_before == time_after

    def test_resume(self):
        """Test resuming time."""
        service = TimeService()
        service.set_time_dilation(2.0)

        service.pause()
        assert service.is_paused()

        service.resume()

        assert not service.is_paused()
        assert service.get_time_dilation() == 2.0  # Should restore previous dilation

    def test_pause_when_already_paused(self):
        """Test pausing when already paused (should be idempotent)."""
        service = TimeService()

        service.pause()
        assert service.is_paused()

        service.pause()  # Pause again
        assert service.is_paused()

    def test_resume_when_not_paused(self):
        """Test resuming when not paused (should be idempotent)."""
        service = TimeService()

        assert not service.is_paused()

        service.resume()  # Resume when not paused
        assert not service.is_paused()


class TestManualTimeManipulation:
    """Test manual time manipulation methods."""

    def test_jump_to(self):
        """Test jumping to specific time."""
        service = TimeService()

        target = datetime(2049, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        service.jump_to(target)

        current = service.get_current_time()
        assert current.year == 2049
        assert current.month == 1
        assert current.day == 1

    def test_advance(self):
        """Test advancing time by duration."""
        service = TimeService()

        start = service.get_current_time()
        service.advance(timedelta(days=5))

        end = service.get_current_time()
        elapsed = end - start

        assert elapsed.days == 5

    def test_rewind(self):
        """Test rewinding time by duration."""
        service = TimeService()

        start = service.get_current_time()
        service.rewind(timedelta(hours=2))

        end = service.get_current_time()
        elapsed = start - end

        assert elapsed.total_seconds() == 2 * 3600  # 2 hours in seconds

    def test_advance_multiple_times(self):
        """Test advancing time multiple times accumulates."""
        service = TimeService()

        start = service.get_current_time()

        service.advance(timedelta(days=1))
        service.advance(timedelta(days=2))
        service.advance(timedelta(days=3))

        end = service.get_current_time()
        elapsed = end - start

        assert elapsed.days == 6


class TestTimeState:
    """Test getting complete time state."""

    def test_get_time_state(self):
        """Test getting complete time state."""
        service = TimeService()
        service.set_time_dilation(2.5)

        state = service.get_time_state()

        assert "current_time" in state
        assert "time_dilation" in state
        assert "is_paused" in state
        assert "real_time" in state

        assert state["time_dilation"] == 2.5
        assert state["is_paused"] is False

    def test_get_time_state_when_paused(self):
        """Test getting state when paused."""
        service = TimeService()
        service.pause()

        state = service.get_time_state()

        assert state["is_paused"] is True
        assert state["time_dilation"] == 0.0


class TestPersistence:
    """Test saving and loading state."""

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        save_path = tmp_path / "time_state.json"

        # Create service and modify state
        service1 = TimeService(persistence_path=save_path)
        service1.set_time_dilation(5.0)
        target_time = datetime(2050, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        service1.jump_to(target_time)
        service1.save_state()

        # Create new service and load
        service2 = TimeService(persistence_path=save_path)
        service2.load_state()

        assert service2.get_time_dilation() == 5.0
        loaded_time = service2.get_current_time()
        assert loaded_time.year == 2050
        assert loaded_time.month == 6
        assert loaded_time.day == 15

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file doesn't crash."""
        save_path = tmp_path / "nonexistent.json"

        service = TimeService(persistence_path=save_path)
        # Should not raise an error
        # Service should use defaults

    def test_save_without_persistence_path(self):
        """Test saving without persistence path (should do nothing)."""
        service = TimeService(persistence_path=None)

        # Should not raise an error
        service.save_state()

    def test_persistence_with_paused_state(self, tmp_path):
        """Test that paused state is persisted."""
        save_path = tmp_path / "time_state.json"

        service1 = TimeService(persistence_path=save_path)
        service1.set_time_dilation(3.0)
        service1.pause()
        service1.save_state()

        service2 = TimeService(persistence_path=save_path)
        service2.load_state()

        assert service2.is_paused()
        # Previous dilation should be saved for resume
        service2.resume()
        assert service2.get_time_dilation() == 3.0


class TestResetToDefault:
    """Test resetting to default state."""

    def test_reset_to_default(self):
        """Test resetting to default state."""
        service = TimeService()

        # Modify state
        service.set_time_dilation(10.0)
        service.jump_to(datetime(2100, 1, 1, tzinfo=timezone.utc))

        # Reset
        service.reset_to_default()

        assert service.get_time_dilation() == 1.0
        assert not service.is_paused()

        current = service.get_current_time()
        assert current.year == 2048
        assert current.month == 11
        assert current.day == 13


class TestCallbacks:
    """Test subscription and callback notifications."""

    def test_subscribe(self):
        """Test subscribing to time changes."""
        service = TimeService()
        callback = Mock()

        service.subscribe(callback)

        service.set_time_dilation(2.0)

        # Callback should have been called
        assert callback.call_count == 1

        # Check callback arguments
        event = callback.call_args[0][0]
        assert event["type"] == "dilation_change"

    def test_multiple_callbacks(self):
        """Test multiple callbacks are all notified."""
        service = TimeService()
        callback1 = Mock()
        callback2 = Mock()

        service.subscribe(callback1)
        service.subscribe(callback2)

        service.pause()

        assert callback1.call_count == 1
        assert callback2.call_count == 1

    def test_callback_receives_event_details(self):
        """Test callback receives correct event details."""
        service = TimeService()
        events = []

        def callback(event):
            events.append(event)

        service.subscribe(callback)

        service.set_time_dilation(3.0)
        service.pause()
        service.resume()

        assert len(events) == 3
        assert events[0]["type"] == "dilation_change"
        assert events[1]["type"] == "pause"
        assert events[2]["type"] == "resume"

    def test_callback_error_handling(self):
        """Test that errors in callbacks don't crash the service."""
        service = TimeService()

        def bad_callback(event):
            raise Exception("Callback error")

        service.subscribe(bad_callback)

        # Should not raise an error
        service.set_time_dilation(2.0)

        # Service should still work
        assert service.get_time_dilation() == 2.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_high_time_dilation(self):
        """Test very high time dilation values."""
        service = TimeService()

        service.set_time_dilation(1000.0)
        assert service.get_time_dilation() == 1000.0

    def test_very_low_time_dilation(self):
        """Test very low (but positive) time dilation."""
        service = TimeService()

        service.set_time_dilation(0.001)
        assert service.get_time_dilation() == 0.001

    def test_fractional_time_dilation(self):
        """Test fractional time dilation values."""
        service = TimeService()

        service.set_time_dilation(0.5)

        start = service.get_current_time()
        time.sleep(0.2)
        end = service.get_current_time()

        elapsed = (end - start).total_seconds()
        # Should be about 0.1 seconds (0.2 * 0.5)
        assert 0.05 < elapsed < 0.15

    def test_jump_to_far_future(self):
        """Test jumping to far future date."""
        service = TimeService()

        target = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        service.jump_to(target)

        current = service.get_current_time()
        assert current.year == 9999

    def test_jump_to_past(self):
        """Test jumping to past date."""
        service = TimeService()

        target = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        service.jump_to(target)

        current = service.get_current_time()
        assert current.year == 2000

    def test_advance_by_zero(self):
        """Test advancing by zero duration."""
        service = TimeService()

        before = service.get_current_time()
        service.advance(timedelta(0))
        after = service.get_current_time()

        # Should be approximately the same (allowing for tiny execution time)
        diff = abs((after - before).total_seconds())
        assert diff < 0.01

    def test_rapid_state_changes(self):
        """Test rapid state changes."""
        service = TimeService()

        # Rapidly change state
        for i in range(100):
            service.set_time_dilation(float(i % 10))

        # Should end up with dilation of 9 (99 % 10)
        assert service.get_time_dilation() == 9.0
