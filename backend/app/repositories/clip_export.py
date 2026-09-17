from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clip_export import ClipExport, ClipExportEvent


def create_clip_export(
    db: Session,
    *,
    match_id: int,
    user_id: int,
    event_ids: list[int],
    filename: str,
) -> ClipExport:
    clip_export = ClipExport(
        match_id=match_id,
        created_by_user_id=user_id,
        filename=filename,
    )
    db.add(clip_export)
    db.flush()
    db.add_all(
        ClipExportEvent(clip_export_id=clip_export.id, event_id=event_id, sequence=sequence)
        for sequence, event_id in enumerate(event_ids)
    )
    db.commit()
    db.refresh(clip_export)
    return clip_export


def list_match_clip_exports(db: Session, match_id: int) -> list[ClipExport]:
    return list(
        db.scalars(
            select(ClipExport)
            .where(ClipExport.match_id == match_id)
            .order_by(ClipExport.created_at.desc(), ClipExport.id.desc())
        )
    )


def get_clip_export(db: Session, clip_export_id: int) -> ClipExport | None:
    return db.get(ClipExport, clip_export_id)


def list_event_ids(db: Session, clip_export_id: int) -> list[int]:
    return list(
        db.scalars(
            select(ClipExportEvent.event_id)
            .where(ClipExportEvent.clip_export_id == clip_export_id)
            .order_by(ClipExportEvent.sequence)
        )
    )
