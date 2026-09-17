from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VideoUploadCreate(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    total_size: int = Field(gt=0)
    fingerprint: str = Field(min_length=1, max_length=500)


class VideoUploadPartRead(BaseModel):
    part_number: int
    size_bytes: int
    checksum_sha256: str


class VideoUploadSessionRead(BaseModel):
    id: str
    match_id: int
    original_filename: str
    total_size: int
    chunk_size: int
    total_parts: int
    status: Literal["uploading", "assembling", "completed", "cancelled", "failed"]
    uploaded_parts: list[VideoUploadPartRead]
    video_id: int | None
    created_at: datetime
    updated_at: datetime
