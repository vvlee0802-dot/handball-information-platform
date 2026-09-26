from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventPlayerAssignmentAudit(Base):
    __tablename__ = "event_player_assignment_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    old_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_player_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    new_player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    changed_by_user_name: Mapped[str] = mapped_column(String(120), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
