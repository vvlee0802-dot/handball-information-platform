from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"
    __table_args__ = (
        Index(
            "uq_analysis_tasks_active_video",
            "video_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(
        String(30), default="goal_detection", server_default="goal_detection", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued", nullable=False
    )
    progress: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    stage: Mapped[str] = mapped_column(
        String(50), default="queued", server_default="queued", nullable=False
    )
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    candidate_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    evaluation_mode: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    ground_truth_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    true_positive_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    false_positive_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    false_negative_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_absolute_error_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
