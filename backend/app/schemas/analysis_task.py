from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnalysisTaskRead(BaseModel):
    id: str
    match_id: int
    video_id: int
    created_by_user_id: int
    task_type: Literal["goal_detection"]
    status: Literal["queued", "running", "completed", "failed"]
    progress: int
    stage: str
    failure_reason: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    reused: bool = False

    model_config = ConfigDict(from_attributes=True)
