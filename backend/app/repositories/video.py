from datetime import datetime, timezone

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.event import Event
from app.models.analysis_task import AnalysisTask


def list_match_videos(db: Session, match_id: int) -> list[Video]:
    return list(
        db.scalars(
            select(Video)
            .where(Video.match_id == match_id, Video.deleted_at.is_(None))
            .order_by(Video.created_at.desc(), Video.id.desc())
        )
    )


def get_video(db: Session, video_id: int) -> Video | None:
    return db.get(Video, video_id)


def queue_video_for_retry(db: Session, video: Video) -> Video:
    video.processing_status = "queued"
    video.processing_progress = 0
    video.failure_reason = None
    video.checksum_sha256 = None
    video.processing_started_at = None
    video.processing_completed_at = None
    db.commit()
    db.refresh(video)
    return video


def create_video(
    db: Session,
    *,
    match_id: int,
    uploaded_by_user_id: int,
    original_filename: str,
    storage_key: str,
    content_type: str,
    size_bytes: int,
    duration_seconds: float | None = None,
    video_type: str = "original",
) -> Video:
    video = Video(
        match_id=match_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        video_type=video_type,
        status="uploaded",
        processing_status="queued",
        processing_progress=0,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def soft_delete_video(db: Session, video: Video) -> Video:
    video.status = "deleted"
    video.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(video)
    return video


def has_events(db: Session, video_id: int) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(Event.video_id == video_id, Event.deleted_at.is_(None))
            )
        )
    )


def has_active_analysis_task(db: Session, video_id: int) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    AnalysisTask.video_id == video_id,
                    AnalysisTask.status.in_(("queued", "running")),
                )
            )
        )
    )
