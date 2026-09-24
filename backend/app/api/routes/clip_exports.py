from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import UploadVideoUser, ViewAuthorizedVideoUser
from app.core.config import settings
from app.db.session import get_db
from app.models.event import Event
from app.models.video import Video
from app.repositories import clip_export as clip_exports
from app.repositories import match as matches
from app.schemas.clip_export import ClipExportCreate, ClipExportRead
from app.services.clip_export import (
    ClipExportError,
    delete_clip_export_output,
    process_clip_export,
)


router = APIRouter(tags=["clip-exports"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def serialize_clip_export(db: Session, clip_export) -> ClipExportRead:
    return ClipExportRead(
        id=clip_export.id,
        match_id=clip_export.match_id,
        created_by_user_id=clip_export.created_by_user_id,
        event_ids=clip_exports.list_event_ids(db, clip_export.id),
        status=clip_export.status,
        filename=clip_export.filename,
        size_bytes=clip_export.size_bytes,
        duration_seconds=clip_export.duration_seconds,
        failure_reason=clip_export.failure_reason,
        processing_started_at=clip_export.processing_started_at,
        processing_completed_at=clip_export.processing_completed_at,
        created_at=clip_export.created_at,
    )


@router.get(
    "/api/matches/{match_id}/clip-exports",
    response_model=list[ClipExportRead],
)
def list_match_clip_exports(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> list[ClipExportRead]:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return [
        serialize_clip_export(db, clip_export)
        for clip_export in clip_exports.list_match_clip_exports(db, match_id)
    ]


@router.post(
    "/api/matches/{match_id}/clip-exports",
    response_model=ClipExportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_clip_export(
    match_id: int,
    payload: ClipExportCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> ClipExportRead:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if len(set(payload.event_ids)) != len(payload.event_ids):
        raise HTTPException(status_code=422, detail="Event IDs cannot be duplicated")

    selected_events = list(
        db.scalars(
            select(Event).where(
                Event.id.in_(payload.event_ids),
                Event.match_id == match_id,
                Event.deleted_at.is_(None),
            )
        )
    )
    if len(selected_events) != len(payload.event_ids):
        raise HTTPException(status_code=422, detail="All events must belong to this match")
    if any(event.status != "verified" for event in selected_events):
        raise HTTPException(status_code=409, detail="Only verified events can be exported")

    video_ids = {event.video_id for event in selected_events}
    selected_videos = list(db.scalars(select(Video).where(Video.id.in_(video_ids))))
    if len(selected_videos) != len(video_ids) or any(
        video.deleted_at is not None or video.processing_status != "completed"
        for video in selected_videos
    ):
        raise HTTPException(status_code=409, detail="All event videos must be available")

    ordered_event_ids = [
        event.id for event in sorted(selected_events, key=lambda item: (item.timestamp_seconds, item.id))
    ]
    filename = f"match-{match_id}-events-{len(ordered_event_ids)}.mp4"
    clip_export = clip_exports.create_clip_export(
        db,
        match_id=match_id,
        user_id=current_user.id,
        event_ids=ordered_event_ids,
        filename=filename,
    )
    response = serialize_clip_export(db, clip_export)
    background_tasks.add_task(process_clip_export, clip_export.id, db.get_bind())
    return response


@router.get("/api/clip-exports/{clip_export_id}/content", response_class=FileResponse)
def read_clip_export_content(
    clip_export_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
    download: bool = False,
) -> FileResponse:
    clip_export = clip_exports.get_clip_export(db, clip_export_id)
    if clip_export is None:
        raise HTTPException(status_code=404, detail="Clip export not found")
    if clip_export.status != "completed" or clip_export.storage_key is None:
        raise HTTPException(status_code=409, detail="Clip export is not ready")
    stored_path = settings.video_storage_path / clip_export.storage_key
    if not stored_path.is_file():
        raise HTTPException(status_code=404, detail="Stored clip file not found")
    if download:
        return FileResponse(
            Path(stored_path),
            media_type="video/mp4",
            filename=clip_export.filename,
            content_disposition_type="attachment",
        )
    return FileResponse(
        Path(stored_path),
        media_type="video/mp4",
        headers={"Content-Disposition": f'inline; filename="{clip_export.filename}"'},
    )


@router.delete(
    "/api/clip-exports/{clip_export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_clip_export(
    clip_export_id: int,
    db: DatabaseSession,
    _current_user: UploadVideoUser,
) -> None:
    clip_export = clip_exports.get_clip_export(db, clip_export_id)
    if clip_export is None:
        raise HTTPException(status_code=404, detail="Clip export not found")
    if clip_export.status in {"queued", "processing"}:
        raise HTTPException(
            status_code=409,
            detail="A queued or processing clip export cannot be deleted",
        )
    try:
        delete_clip_export_output(clip_export)
    except ClipExportError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    clip_exports.delete_clip_export(db, clip_export)
