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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoUploadPolicy(BaseModel):
    accepted_extensions: list[str]
    accepted_content_types: list[str]
    max_size_bytes: int
