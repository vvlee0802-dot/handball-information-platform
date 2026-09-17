from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.video_upload import VideoUploadPart, VideoUploadSession


def find_resumable_session(
    db: Session,
    *,
    match_id: int,
    user_id: int,
    fingerprint: str,
    original_filename: str,
    content_type: str,
    total_size: int,
) -> VideoUploadSession | None:
    return db.scalar(
        select(VideoUploadSession)
        .where(
            VideoUploadSession.match_id == match_id,
            VideoUploadSession.user_id == user_id,
            VideoUploadSession.fingerprint == fingerprint,
            VideoUploadSession.original_filename == original_filename,
            VideoUploadSession.content_type == content_type,
            VideoUploadSession.total_size == total_size,
            VideoUploadSession.status.in_(["uploading", "failed"]),
        )
        .order_by(VideoUploadSession.created_at.desc())
    )


def list_parts(db: Session, upload_id: str) -> list[VideoUploadPart]:
    return list(
        db.scalars(
            select(VideoUploadPart)
            .where(VideoUploadPart.upload_id == upload_id)
            .order_by(VideoUploadPart.part_number)
        )
    )


def get_part(db: Session, upload_id: str, part_number: int) -> VideoUploadPart | None:
    return db.scalar(
        select(VideoUploadPart).where(
            VideoUploadPart.upload_id == upload_id,
            VideoUploadPart.part_number == part_number,
        )
    )


def delete_parts(db: Session, upload_id: str) -> None:
    db.execute(delete(VideoUploadPart).where(VideoUploadPart.upload_id == upload_id))
