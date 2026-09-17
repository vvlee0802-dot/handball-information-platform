from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ClipExportCreate(BaseModel):
    event_ids: list[int] = Field(min_length=1, max_length=100)


class ClipExportRead(BaseModel):
    id: int
    match_id: int
    created_by_user_id: int
    event_ids: list[int]
    status: Literal["queued", "processing", "completed", "failed"]
    filename: str
    size_bytes: int | None
    duration_seconds: float | None
    failure_reason: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
