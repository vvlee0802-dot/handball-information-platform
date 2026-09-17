from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class VideoRead(BaseModel):
    id: int
    match_id: int
    uploaded_by_user_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    status: Literal["uploaded"]
    processing_status: Literal["queued", "processing", "completed", "failed"]
    processing_progress: int
    processing_attempts: int
    failure_reason: str | None
    checksum_sha256: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoUploadPolicy(BaseModel):
    accepted_extensions: list[str]
    accepted_content_types: list[str]
    max_size_bytes: int
