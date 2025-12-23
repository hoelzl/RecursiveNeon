"""
Media Viewer Service

Manages the hypnotic spiral media viewer with text overlays.
"""
from typing import Dict, Any, List

from recursive_neon.models.app_models import (
    MediaViewerConfig,
    MediaViewerState,
    TextMessage,
)


class MediaViewerService:
    """
    Service for managing the media viewer.

    Provides configuration and message management for the hypnotic
    spiral display with text overlays.
    """

    def __init__(self, media_viewer_state: MediaViewerState):
        """
        Initialize the media viewer service.

        Args:
            media_viewer_state: The media viewer state to manage
        """
        self._state = media_viewer_state

    def get_config(self) -> MediaViewerConfig:
        """Get the media viewer configuration."""
        return self._state.config

    def update_config(self, data: Dict[str, Any]) -> MediaViewerConfig:
        """
        Update the media viewer configuration.

        Args:
            data: Configuration data (spiral_style, rotation_speed, messages, loop)

        Returns:
            Updated MediaViewerConfig
        """
        current = self._state.config

        # Parse messages if provided
        messages = current.messages
        if "messages" in data:
            messages = [
                TextMessage(**msg) if isinstance(msg, dict) else msg
                for msg in data["messages"]
            ]

        # Create updated config
        updated_config = MediaViewerConfig(
            spiral_style=data.get("spiral_style", current.spiral_style),
            rotation_speed=data.get("rotation_speed", current.rotation_speed),
            messages=messages,
            loop=data.get("loop", current.loop),
        )

        self._state.config = updated_config
        return updated_config

    def add_message(self, message_data: Dict[str, Any]) -> TextMessage:
        """
        Add a text message to the media viewer sequence.

        Args:
            message_data: Message data (text, duration, size, color, position, etc.)

        Returns:
            The created TextMessage
        """
        message = TextMessage(**message_data)
        current_messages = list(self._state.config.messages)
        current_messages.append(message)

        self._state.config = MediaViewerConfig(
            spiral_style=self._state.config.spiral_style,
            rotation_speed=self._state.config.rotation_speed,
            messages=current_messages,
            loop=self._state.config.loop,
        )

        return message

    def remove_message(self, index: int) -> None:
        """
        Remove a message by index.

        Args:
            index: Index of the message to remove

        Raises:
            IndexError: If index is out of range
        """
        current_messages = list(self._state.config.messages)
        if 0 <= index < len(current_messages):
            current_messages.pop(index)
            self._state.config = MediaViewerConfig(
                spiral_style=self._state.config.spiral_style,
                rotation_speed=self._state.config.rotation_speed,
                messages=current_messages,
                loop=self._state.config.loop,
            )
        else:
            raise IndexError(f"Message index out of range: {index}")

    def clear_messages(self) -> None:
        """Clear all messages from the sequence."""
        self._state.config = MediaViewerConfig(
            spiral_style=self._state.config.spiral_style,
            rotation_speed=self._state.config.rotation_speed,
            messages=[],
            loop=self._state.config.loop,
        )

    def set_style(self, style: str) -> MediaViewerConfig:
        """
        Set the spiral style for the media viewer.

        Args:
            style: Spiral style ("blackwhite" or "colorful")

        Returns:
            Updated MediaViewerConfig
        """
        self._state.config = MediaViewerConfig(
            spiral_style=style,
            rotation_speed=self._state.config.rotation_speed,
            messages=self._state.config.messages,
            loop=self._state.config.loop,
        )

        return self._state.config

    def set_rotation_speed(self, speed: float) -> MediaViewerConfig:
        """
        Set the rotation speed for the spiral.

        Args:
            speed: Rotation speed multiplier

        Returns:
            Updated MediaViewerConfig
        """
        self._state.config = MediaViewerConfig(
            spiral_style=self._state.config.spiral_style,
            rotation_speed=speed,
            messages=self._state.config.messages,
            loop=self._state.config.loop,
        )

        return self._state.config

    def set_loop(self, loop: bool) -> MediaViewerConfig:
        """
        Set whether the message sequence should loop.

        Args:
            loop: True to loop, False to play once

        Returns:
            Updated MediaViewerConfig
        """
        self._state.config = MediaViewerConfig(
            spiral_style=self._state.config.spiral_style,
            rotation_speed=self._state.config.rotation_speed,
            messages=self._state.config.messages,
            loop=loop,
        )

        return self._state.config

    def get_messages(self) -> List[TextMessage]:
        """Get all messages in the sequence."""
        return self._state.config.messages

    def initialize_default_messages(self) -> None:
        """
        Initialize the media viewer with default corporate "wellness" messages.

        This creates a dystopian sequence of messages that appears to be for
        health and relaxation but subtly reinforces corporate/government messaging.
        """
        default_messages = [
            # Opening relaxation
            TextMessage(
                text="Welcome to MindSync Wellness",
                duration=3.0,
                size=48,
                color="#00FFFF",
                x=50,
                y=30,
                font_weight="bold"
            ),
            TextMessage(
                text="Take a deep breath...",
                duration=4.0,
                size=36,
                color="#FFFFFF",
                x=50,
                y=50,
                font_weight="normal"
            ),
            # Pause for breathing
            TextMessage(
                text=None,  # Pause
                duration=2.0,
                size=32,
                color="#FFFFFF",
                x=50,
                y=50
            ),
            # Subtle corporate messaging
            TextMessage(
                text="You are valued.",
                duration=3.0,
                size=40,
                color="#00FF00",
                x=50,
                y=45,
                font_weight="normal"
            ),
            TextMessage(
                text="Your productivity matters.",
                duration=3.0,
                size=32,
                color="#FFFF00",
                x=50,
                y=55,
                font_weight="normal"
            ),
            TextMessage(
                text=None,  # Pause
                duration=2.0,
                size=32,
                color="#FFFFFF",
                x=50,
                y=50
            ),
            # More relaxation mixed with messaging
            TextMessage(
                text="Trust the system.",
                duration=3.5,
                size=36,
                color="#FF00FF",
                x=50,
                y=50,
                font_weight="normal"
            ),
            TextMessage(
                text="Consume responsibly.",
                duration=3.0,
                size=28,
                color="#00FFFF",
                x=50,
                y=60,
                font_weight="normal"
            ),
            TextMessage(
                text=None,  # Pause
                duration=2.0,
                size=32,
                color="#FFFFFF",
                x=50,
                y=50
            ),
            # Closing
            TextMessage(
                text="You are refreshed.",
                duration=3.0,
                size=42,
                color="#00FF00",
                x=50,
                y=45,
                font_weight="bold"
            ),
            TextMessage(
                text="Return to work with renewed focus.",
                duration=4.0,
                size=30,
                color="#FFFFFF",
                x=50,
                y=55,
                font_weight="normal"
            ),
            TextMessage(
                text=None,  # Final pause before loop
                duration=3.0,
                size=32,
                color="#FFFFFF",
                x=50,
                y=50
            ),
        ]

        self._state.config = MediaViewerConfig(
            spiral_style="blackwhite",
            rotation_speed=1.0,
            messages=default_messages,
            loop=True,
        )
