from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.video import Video


def list_match_videos(db: Session, match_id: int) -> list[Video]:
    return list(
        db.scalars(
            select(Video)
            .where(Video.match_id == match_id)
            .order_by(Video.created_at.desc(), Video.id.desc())
        )
    )


def create_video(
    db: Session,
    *,
    match_id: int,
    uploaded_by_user_id: int,
    original_filename: str,
    storage_key: str,
    content_type: str,
    size_bytes: int,
) -> Video:
    video = Video(
        match_id=match_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        status="uploaded",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
