"""
Settings Service

This module provides the SettingsService, which manages application settings
with features like:
- Persistent storage
- Validation
- Default values
- Change notifications
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from recursive_neon.services.interfaces import ISettingsService

logger = logging.getLogger(__name__)


class SettingDefinition:
    """Definition of a setting with validation and metadata."""

    def __init__(
        self,
        key: str,
        default_value: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize setting definition.

        Args:
            key: Setting key
            default_value: Default value
            validator: Optional validation function
            description: Optional description
        """
        self.key = key
        self.default_value = default_value
        self.validator = validator
        self.description = description

    def validate(self, value: Any) -> bool:
        """
        Validate a value.

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        if self.validator:
            return self.validator(value)
        return True


class SettingsService(ISettingsService):
    """
    Settings management service.

    This service manages application settings with validation, persistence,
    and change notifications.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        """
        Initialize settings service.

        Args:
            persistence_path: Path to save/load settings (optional)
        """
        self.persistence_path = persistence_path
        self._settings: Dict[str, Any] = {}
        self._defaults: Dict[str, SettingDefinition] = {}
        self._callbacks: List[Callable[[str, Any], None]] = []

        # Register default settings
        self._register_default_settings()

        # Load saved settings
        if persistence_path and persistence_path.exists():
            try:
                self.load()
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}, using defaults")

    def _register_default_settings(self) -> None:
        """Register all default settings."""

        # Clock settings
        self.register_default("clock.visible", True)
        self.register_default(
            "clock.mode",
            "digital",
            validator=lambda v: v in ["off", "analog", "digital"],
            description="Clock display mode"
        )
        self.register_default(
            "clock.position",
            "top-right",
            validator=lambda v: v in ["top-left", "top-right", "bottom-left", "bottom-right"],
            description="Clock position on screen"
        )
        self.register_default(
            "clock.format",
            "24h",
            validator=lambda v: v in ["12h", "24h"],
            description="Time format for digital clock"
        )
        self.register_default("clock.showSeconds", True, description="Show seconds in digital clock")
        self.register_default("clock.showDate", True, description="Show date with time")

        # Theme settings
        self.register_default(
            "theme.current",
            "classic",
            validator=lambda v: v in ["classic", "dark", "light", "neon", "terminal", "cyberpunk"],
            description="Current theme"
        )

    def register_default(
        self,
        key: str,
        default_value: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Register a default setting.

        Args:
            key: Setting key
            default_value: Default value
            validator: Optional validation function
            description: Optional description
        """
        definition = SettingDefinition(key, default_value, validator, description)
        self._defaults[key] = definition

        # If no value exists, use default
        if key not in self._settings:
            self._settings[key] = default_value

    def get(self, key: str) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key

        Returns:
            Setting value

        Raises:
            KeyError: If setting not found
        """
        if key in self._settings:
            return self._settings[key]

        # Return default if exists
        if key in self._defaults:
            return self._defaults[key].default_value

        raise KeyError(f"Setting '{key}' not found")

    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.

        Returns:
            Dictionary of all settings
        """
        return dict(self._settings)

    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: New value

        Raises:
            ValueError: If value is invalid
        """
        # Validate if validator exists
        if key in self._defaults:
            if not self._defaults[key].validate(value):
                raise ValueError(f"Invalid value for setting '{key}': {value}")

        old_value = self._settings.get(key)
        self._settings[key] = value

        # Notify subscribers if value changed
        if old_value != value:
            self._notify_change(key, value)
            self.save()

    def set_many(self, settings: Dict[str, Any]) -> None:
        """
        Set multiple settings.

        Args:
            settings: Dictionary of settings to update

        Raises:
            ValueError: If any value is invalid
        """
        # Validate all first
        for key, value in settings.items():
            if key in self._defaults:
                if not self._defaults[key].validate(value):
                    raise ValueError(f"Invalid value for setting '{key}': {value}")

        # Apply all
        changed_keys = []
        for key, value in settings.items():
            old_value = self._settings.get(key)
            self._settings[key] = value
            if old_value != value:
                changed_keys.append(key)

        # Notify for each changed key
        for key in changed_keys:
            self._notify_change(key, self._settings[key])

        if changed_keys:
            self.save()

    def reset(self, key: str) -> None:
        """
        Reset setting to default.

        Args:
            key: Setting key to reset

        Raises:
            KeyError: If setting has no default
        """
        if key not in self._defaults:
            raise KeyError(f"Setting '{key}' has no default")

        default_value = self._defaults[key].default_value
        self.set(key, default_value)

    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        for key, definition in self._defaults.items():
            self._settings[key] = definition.default_value

        # Notify all changes
        for key in self._defaults.keys():
            self._notify_change(key, self._settings[key])

        self.save()

    def get_default(self, key: str) -> Any:
        """
        Get default value.

        Args:
            key: Setting key

        Returns:
            Default value

        Raises:
            KeyError: If setting has no default
        """
        if key not in self._defaults:
            raise KeyError(f"Setting '{key}' has no default")
        return self._defaults[key].default_value

    def save(self) -> None:
        """Save settings to disk."""
        if not self.persistence_path:
            return

        try:
            # Atomic write
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.persistence_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self._settings, f, indent=2)
            temp_path.replace(self.persistence_path)

            logger.debug(f"Saved settings to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def load(self) -> None:
        """Load settings from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, 'r') as f:
                loaded_settings = json.load(f)

            # Validate and apply
            for key, value in loaded_settings.items():
                if key in self._defaults:
                    if self._defaults[key].validate(value):
                        self._settings[key] = value
                    else:
                        logger.warning(f"Invalid value for '{key}': {value}, using default")
                else:
                    # Unknown setting, but keep it
                    self._settings[key] = value

            logger.info(f"Loaded settings from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to changes.

        Args:
            callback: Function to call when settings change (receives key, value)
        """
        self._callbacks.append(callback)

    def _notify_change(self, key: str, value: Any) -> None:
        """
        Notify subscribers of change.

        Args:
            key: Setting key that changed
            value: New value
        """
        for callback in self._callbacks:
            try:
                callback(key, value)
            except Exception as e:
                logger.error(f"Error in settings callback: {e}")
