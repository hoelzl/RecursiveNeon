"""Calendar event models for RecursiveNeon."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class CalendarEvent(BaseModel):
    """Represents a calendar event in the game."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('end_time')
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end_time is after start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateEventRequest(BaseModel):
    """Request model for creating a calendar event."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: bool = False

    @field_validator('end_time')
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end_time is after start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class UpdateEventRequest(BaseModel):
    """Request model for updating a calendar event."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    notes: Optional[str] = Field(None, max_length=5000)
    all_day: Optional[bool] = None
