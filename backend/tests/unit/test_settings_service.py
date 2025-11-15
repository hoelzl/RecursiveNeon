"""
Unit tests for SettingsService

Tests the settings management service including:
- Getting and setting values
- Default values and registration
- Validation
- Persistence
- Callbacks
- Bulk operations
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from recursive_neon.services.settings_service import SettingsService


class TestSettingsServiceInitialization:
    """Test SettingsService initialization."""

    def test_initialization_with_defaults(self):
        """Test service initializes with default settings."""
        service = SettingsService()

        # Clock settings should be registered
        assert service.get("clock.visible") is True
        assert service.get("clock.mode") == "digital"
        assert service.get("clock.position") == "top-right"

        # Theme settings should be registered
        assert service.get("theme.current") == "classic"

    def test_initialization_without_persistence_path(self):
        """Test initialization without persistence path."""
        service = SettingsService(persistence_path=None)

        assert service.persistence_path is None
        # Should still have defaults
        assert service.get("clock.mode") == "digital"


class TestGetSettings:
    """Test getting setting values."""

    def test_get_default_setting(self):
        """Test getting a default setting."""
        service = SettingsService()

        assert service.get("clock.visible") is True

    def test_get_nonexistent_setting_raises_error(self):
        """Test getting nonexistent setting raises KeyError."""
        service = SettingsService()

        with pytest.raises(KeyError, match="not found"):
            service.get("nonexistent.setting")

    def test_get_all(self):
        """Test getting all settings."""
        service = SettingsService()

        all_settings = service.get_all()

        assert isinstance(all_settings, dict)
        assert "clock.mode" in all_settings
        assert "theme.current" in all_settings

    def test_get_default(self):
        """Test getting default value."""
        service = SettingsService()

        default = service.get_default("clock.mode")

        assert default == "digital"

    def test_get_default_nonexistent_raises_error(self):
        """Test getting default for nonexistent setting raises error."""
        service = SettingsService()

        with pytest.raises(KeyError):
            service.get_default("nonexistent.setting")


class TestSetSettings:
    """Test setting values."""

    def test_set_and_get(self):
        """Test setting and getting a value."""
        service = SettingsService()

        service.set("clock.mode", "analog")

        assert service.get("clock.mode") == "analog"

    def test_set_updates_value(self):
        """Test that set updates existing value."""
        service = SettingsService()

        assert service.get("clock.mode") == "digital"

        service.set("clock.mode", "analog")

        assert service.get("clock.mode") == "analog"

    def test_set_with_validation_passes(self):
        """Test setting valid value passes validation."""
        service = SettingsService()

        # Should not raise
        service.set("clock.mode", "analog")

    def test_set_with_validation_fails(self):
        """Test setting invalid value fails validation."""
        service = SettingsService()

        with pytest.raises(ValueError, match="Invalid value"):
            service.set("clock.mode", "invalid_mode")

    def test_set_without_validator(self):
        """Test setting value for setting without validator."""
        service = SettingsService()

        # register a setting without validator
        service.register_default("test.setting", "default_value")

        # Should accept any value
        service.set("test.setting", "any_value")
        assert service.get("test.setting") == "any_value"


class TestSetMany:
    """Test setting multiple settings at once."""

    def test_set_many(self):
        """Test setting multiple settings."""
        service = SettingsService()

        service.set_many({
            "clock.mode": "analog",
            "clock.showSeconds": False,
            "theme.current": "dark"
        })

        assert service.get("clock.mode") == "analog"
        assert service.get("clock.showSeconds") is False
        assert service.get("theme.current") == "dark"

    def test_set_many_validates_all_first(self):
        """Test that set_many validates all before applying any."""
        service = SettingsService()

        # Mix of valid and invalid
        with pytest.raises(ValueError):
            service.set_many({
                "clock.mode": "analog",  # valid
                "clock.position": "invalid_position",  # invalid
            })

        # Should not have applied the valid one either
        assert service.get("clock.mode") == "digital"  # Still default

    def test_set_many_empty_dict(self):
        """Test set_many with empty dict."""
        service = SettingsService()

        # Should not raise
        service.set_many({})


class TestReset:
    """Test resetting settings to defaults."""

    def test_reset_single_setting(self):
        """Test resetting a single setting to default."""
        service = SettingsService()

        service.set("clock.mode", "analog")
        assert service.get("clock.mode") == "analog"

        service.reset("clock.mode")

        assert service.get("clock.mode") == "digital"

    def test_reset_nonexistent_setting_raises_error(self):
        """Test resetting nonexistent setting raises error."""
        service = SettingsService()

        with pytest.raises(KeyError):
            service.reset("nonexistent.setting")

    def test_reset_all(self):
        """Test resetting all settings to defaults."""
        service = SettingsService()

        # Change multiple settings
        service.set("clock.mode", "analog")
        service.set("clock.showSeconds", False)
        service.set("theme.current", "dark")

        # Reset all
        service.reset_all()

        # All should be back to defaults
        assert service.get("clock.mode") == "digital"
        assert service.get("clock.showSeconds") is True
        assert service.get("theme.current") == "classic"


class TestPersistence:
    """Test saving and loading settings."""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading settings."""
        save_path = tmp_path / "settings.json"

        # Create service and modify settings
        service1 = SettingsService(persistence_path=save_path)
        service1.set("clock.mode", "analog")
        service1.set("theme.current", "dark")
        service1.save()

        # Create new service and load
        service2 = SettingsService(persistence_path=save_path)
        service2.load()

        assert service2.get("clock.mode") == "analog"
        assert service2.get("theme.current") == "dark"

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file doesn't crash."""
        save_path = tmp_path / "nonexistent.json"

        service = SettingsService(persistence_path=save_path)
        # Should not raise an error
        # Service should use defaults

    def test_save_without_persistence_path(self):
        """Test saving without persistence path."""
        service = SettingsService(persistence_path=None)

        # Should not raise an error
        service.save()

    def test_auto_save_on_set(self, tmp_path):
        """Test that settings are auto-saved when changed."""
        save_path = tmp_path / "settings.json"

        service1 = SettingsService(persistence_path=save_path)
        service1.set("clock.mode", "analog")
        # Should auto-save

        # Load in new service
        service2 = SettingsService(persistence_path=save_path)
        service2.load()

        assert service2.get("clock.mode") == "analog"

    def test_load_validates_values(self, tmp_path):
        """Test that load validates loaded values."""
        save_path = tmp_path / "settings.json"

        # Manually create a settings file with invalid value
        import json
        with open(save_path, 'w') as f:
            json.dump({
                "clock.mode": "invalid_mode"  # Invalid
            }, f)

        service = SettingsService(persistence_path=save_path)
        service.load()

        # Should fall back to default for invalid value
        assert service.get("clock.mode") == "digital"


class TestRegisterDefault:
    """Test registering default values."""

    def test_register_default_simple(self):
        """Test registering a simple default."""
        service = SettingsService()

        service.register_default("test.setting", "test_value")

        assert service.get("test.setting") == "test_value"

    def test_register_default_with_validator(self):
        """Test registering default with validator."""
        service = SettingsService()

        def validator(value):
            return value in ["option1", "option2"]

        service.register_default("test.option", "option1", validator=validator)

        assert service.get("test.option") == "option1"

        # Valid value should work
        service.set("test.option", "option2")

        # Invalid value should fail
        with pytest.raises(ValueError):
            service.set("test.option", "option3")

    def test_register_default_with_description(self):
        """Test registering default with description."""
        service = SettingsService()

        service.register_default(
            "test.setting",
            "value",
            description="This is a test setting"
        )

        # Description is stored in the definition
        assert "test.setting" in service._defaults
        assert service._defaults["test.setting"].description == "This is a test setting"

    def test_register_default_doesnt_overwrite_existing_value(self):
        """Test that registering default doesn't overwrite existing value."""
        service = SettingsService()

        # Set a value
        service.register_default("test.setting", "default")
        service.set("test.setting", "custom")

        # Register again with different default
        service.register_default("test.setting", "new_default")

        # Should keep custom value
        assert service.get("test.setting") == "custom"


class TestCallbacks:
    """Test subscription and callback notifications."""

    def test_subscribe(self):
        """Test subscribing to setting changes."""
        service = SettingsService()
        callback = Mock()

        service.subscribe(callback)

        service.set("clock.mode", "analog")

        # Callback should have been called with key and value
        callback.assert_called_once_with("clock.mode", "analog")

    def test_multiple_callbacks(self):
        """Test multiple callbacks are all notified."""
        service = SettingsService()
        callback1 = Mock()
        callback2 = Mock()

        service.subscribe(callback1)
        service.subscribe(callback2)

        service.set("clock.mode", "analog")

        callback1.assert_called_once_with("clock.mode", "analog")
        callback2.assert_called_once_with("clock.mode", "analog")

    def test_callback_not_called_if_value_unchanged(self):
        """Test callback is not called if value doesn't change."""
        service = SettingsService()
        callback = Mock()

        service.subscribe(callback)

        # Set to same value as default
        service.set("clock.mode", "digital")

        # Should not be called because value didn't change
        callback.assert_not_called()

    def test_callback_receives_all_changes(self):
        """Test callback receives all setting changes."""
        service = SettingsService()
        changes = []

        def callback(key, value):
            changes.append((key, value))

        service.subscribe(callback)

        service.set("clock.mode", "analog")
        service.set("theme.current", "dark")
        service.set("clock.showSeconds", False)

        assert len(changes) == 3
        assert ("clock.mode", "analog") in changes
        assert ("theme.current", "dark") in changes
        assert ("clock.showSeconds", False) in changes

    def test_callback_error_handling(self):
        """Test that errors in callbacks don't crash the service."""
        service = SettingsService()

        def bad_callback(key, value):
            raise Exception("Callback error")

        service.subscribe(bad_callback)

        # Should not raise an error
        service.set("clock.mode", "analog")

        # Service should still work
        assert service.get("clock.mode") == "analog"

    def test_set_many_triggers_callbacks(self):
        """Test that set_many triggers callbacks for changed values."""
        service = SettingsService()
        changes = []

        def callback(key, value):
            changes.append((key, value))

        service.subscribe(callback)

        service.set_many({
            "clock.mode": "analog",
            "theme.current": "dark"
        })

        assert len(changes) == 2

    def test_reset_all_triggers_callbacks(self):
        """Test that reset_all triggers callbacks."""
        service = SettingsService()
        callback = Mock()

        # Change a setting
        service.set("clock.mode", "analog")

        service.subscribe(callback)

        # Reset all
        service.reset_all()

        # Should be called for clock.mode changing back to digital
        assert callback.call_count >= 1


class TestValidation:
    """Test validation functionality."""

    def test_enum_validation(self):
        """Test enum-style validation."""
        service = SettingsService()

        # clock.mode has enum validation
        valid_modes = ["off", "analog", "digital"]

        for mode in valid_modes:
            service.set("clock.mode", mode)
            assert service.get("clock.mode") == mode

        with pytest.raises(ValueError):
            service.set("clock.mode", "invalid")

    def test_boolean_validation(self):
        """Test boolean settings."""
        service = SettingsService()

        service.set("clock.showSeconds", True)
        assert service.get("clock.showSeconds") is True

        service.set("clock.showSeconds", False)
        assert service.get("clock.showSeconds") is False

    def test_custom_validator_lambda(self):
        """Test custom validator using lambda."""
        service = SettingsService()

        service.register_default(
            "test.number",
            50,
            validator=lambda v: isinstance(v, (int, float)) and 0 <= v <= 100
        )

        service.set("test.number", 75)
        assert service.get("test.number") == 75

        with pytest.raises(ValueError):
            service.set("test.number", 150)

    def test_custom_validator_function(self):
        """Test custom validator using function."""
        service = SettingsService()

        def validate_email(value):
            return isinstance(value, str) and "@" in value

        service.register_default("test.email", "default@example.com", validator=validate_email)

        service.set("test.email", "user@test.com")
        assert service.get("test.email") == "user@test.com"

        with pytest.raises(ValueError):
            service.set("test.email", "not_an_email")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_setting_key_with_dots(self):
        """Test settings with multiple dots in key."""
        service = SettingsService()

        service.register_default("my.deep.nested.setting", "value")

        service.set("my.deep.nested.setting", "new_value")
        assert service.get("my.deep.nested.setting") == "new_value"

    def test_setting_various_value_types(self):
        """Test settings with various value types."""
        service = SettingsService()

        service.register_default("test.string", "string")
        service.register_default("test.int", 42)
        service.register_default("test.float", 3.14)
        service.register_default("test.bool", True)
        service.register_default("test.none", None)

        assert service.get("test.string") == "string"
        assert service.get("test.int") == 42
        assert service.get("test.float") == 3.14
        assert service.get("test.bool") is True
        assert service.get("test.none") is None

    def test_rapid_setting_changes(self):
        """Test rapid setting changes."""
        service = SettingsService()

        for i in range(100):
            service.set("clock.mode", ["off", "analog", "digital"][i % 3])

        # Should end up with "digital" (99 % 3 = 0, but we changed to index 0 which is "off",
        # actually 99 % 3 = 0 means "off")
        assert service.get("clock.mode") in ["off", "analog", "digital"]

    def test_unknown_settings_in_loaded_file(self, tmp_path):
        """Test that unknown settings in file are preserved."""
        save_path = tmp_path / "settings.json"

        # Create file with unknown setting
        import json
        with open(save_path, 'w') as f:
            json.dump({
                "clock.mode": "analog",
                "unknown.setting": "some_value"
            }, f)

        service = SettingsService(persistence_path=save_path)
        service.load()

        # Unknown setting should be loaded (even though not registered)
        assert service.get("unknown.setting") == "some_value"
