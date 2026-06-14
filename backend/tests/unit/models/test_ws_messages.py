"""Tests for /ws/terminal message models."""

import pytest

from recursive_neon.models.ws_messages import (
    ClientMessage,
    CompleteMessage,
    InputMessage,
    KeyMessage,
    ResizeMessage,
    parse_client_message,
)


class TestParseClientMessage:
    def test_input_message(self):
        msg = parse_client_message({"type": "input", "line": "ls"})
        assert isinstance(msg, InputMessage)
        assert msg.line == "ls"

    def test_key_message(self):
        msg = parse_client_message({"type": "key", "key": "ArrowUp"})
        assert isinstance(msg, KeyMessage)
        assert msg.key == "ArrowUp"

    def test_resize_message(self):
        msg = parse_client_message({"type": "resize", "width": 80, "height": 24})
        assert isinstance(msg, ResizeMessage)
        assert msg.width == 80
        assert msg.height == 24

    def test_complete_message(self):
        msg = parse_client_message({"type": "complete", "line": "l"})
        assert isinstance(msg, CompleteMessage)
        assert msg.line == "l"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_client_message({"type": "bogus"})

    def test_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            parse_client_message({"type": "input"})

    def test_client_message_union(self):
        """Union alias is importable."""
        assert ClientMessage is not None
