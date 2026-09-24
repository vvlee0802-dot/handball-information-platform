from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


PredictionOutcome = Literal["true_positive", "false_positive", "false_negative"]
TrainingDecision = Literal["pending", "include", "exclude"]


class AnalysisPredictionRead(BaseModel):
    id: int
    analysis_task_id: str
    outcome: PredictionOutcome
    predicted_timestamp_seconds: float | None
    confidence: float | None
    ground_truth_event_id: int | None
    ground_truth_timestamp_seconds: float | None
    time_error_seconds: float | None
    training_decision: TrainingDecision
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisPredictionReview(BaseModel):
    decision: Literal["include", "exclude"]
