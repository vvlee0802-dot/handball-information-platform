from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EventType = Literal[
    "goal",
    "shot",
    "save",
    "turnover",
    "foul",
    "suspension",
    "timeout",
    "seven_meter",
    "other",
]


class EventCreate(BaseModel):
    video_id: int
    event_type: EventType
    timestamp_seconds: float = Field(ge=0)
    team_id: int | None = None
    player_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class EventUpdate(BaseModel):
    video_id: int | None = None
    event_type: EventType | None = None
    timestamp_seconds: float | None = Field(default=None, ge=0)
    team_id: int | None = None
    player_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class EventRead(BaseModel):
    id: int
    match_id: int
    video_id: int
    event_type: EventType
    timestamp_seconds: float
    team_id: int | None
    player_id: int | None
    note: str | None
    source: Literal["manual", "ai"]
    confidence: float | None
    model_version: str | None
    analysis_task_id: str | None
    status: Literal["draft", "verified"]
    created_by_user_id: int
    updated_by_user_id: int
    verified_by_user_id: int | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
