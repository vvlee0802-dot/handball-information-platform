from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisPrediction(Base):
    __tablename__ = "analysis_predictions"
    __table_args__ = (
        Index("ix_analysis_predictions_task_outcome", "analysis_task_id", "outcome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_task_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_timestamp_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ground_truth_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True, nullable=True
    )
    ground_truth_timestamp_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_error_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_decision: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
