from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VideoUploadSession(Base):
    __tablename__ = "video_upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_type: Mapped[str] = mapped_column(
        String(30), default="original", server_default="original", nullable=False
    )
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="uploading", server_default="uploading", nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_id: Mapped[int | None] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VideoUploadPart(Base):
    __tablename__ = "video_upload_parts"
    __table_args__ = (
        UniqueConstraint("upload_id", "part_number", name="uq_video_upload_part_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("video_upload_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
