"""Pydantic models for the /ws/terminal WebSocket protocol."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class InputMessage(BaseModel):
    type: Literal["input"]
    line: str


class KeyMessage(BaseModel):
    type: Literal["key"]
    key: str


class ResizeMessage(BaseModel):
    type: Literal["resize"]
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


class CompleteMessage(BaseModel):
    type: Literal["complete"]
    line: str


ClientMessage = InputMessage | KeyMessage | ResizeMessage | CompleteMessage


class OutputMessage(BaseModel):
    type: Literal["output"]
    text: str


class PromptMessage(BaseModel):
    type: Literal["prompt"]
    text: str


class CompletionsMessage(BaseModel):
    type: Literal["completions"]
    items: list[str]
    replace: int


class ModeMessage(BaseModel):
    type: Literal["mode"]
    mode: Literal["raw", "cooked"]


class ScreenMessage(BaseModel):
    type: Literal["screen"]
    lines: list[str]
    cursor: list[int]
    cursor_visible: bool


class ExitMessage(BaseModel):
    type: Literal["exit"]


class ErrorMessage(BaseModel):
    type: Literal["error"]
    message: str


def parse_client_message(data: dict) -> ClientMessage:
    """Validate and parse an incoming client message.

    Raises:
        ValueError: If the message is malformed or has an unknown type.
    """
    try:
        msg_type = data.get("type")
        if msg_type == "input":
            return InputMessage.model_validate(data)
        if msg_type == "key":
            return KeyMessage.model_validate(data)
        if msg_type == "resize":
            return ResizeMessage.model_validate(data)
        if msg_type == "complete":
            return CompleteMessage.model_validate(data)
        raise ValueError(f"Unknown message type: {msg_type}")
    except ValidationError as e:
        raise ValueError(f"Invalid message: {e}") from e
