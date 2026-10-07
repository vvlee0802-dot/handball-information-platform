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
from app.repositories import player as players
from app.schemas.clip_export import (
    ClipExportCreate,
    ClipExportRead,
    ClipExportSegmentRead,
    PlayerHighlightCreate,
)
from app.services.clip_export import (
    ClipExportError,
    calculate_clip_bounds,
    delete_clip_export_output,
)
from app.tasks.queue import dispatch_job

router = APIRouter(tags=["clip-exports"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def serialize_clip_export(db: Session, clip_export) -> ClipExportRead:
    event_ids = clip_exports.list_event_ids(db, clip_export.id)
    events_by_id = {
        event.id: event for event in db.scalars(select(Event).where(Event.id.in_(event_ids)))
    }
    video_ids = {event.video_id for event in events_by_id.values()}
    videos_by_id = {
        video.id: video for video in db.scalars(select(Video).where(Video.id.in_(video_ids)))
    }
    segments: list[ClipExportSegmentRead] = []
    highlight_offset = 0.0
    for event_id in event_ids:
        event = events_by_id.get(event_id)
        video = videos_by_id.get(event.video_id) if event is not None else None
        if event is None or video is None:
            continue
        start, end = calculate_clip_bounds(event.timestamp_seconds, video.duration_seconds)
        duration = end - start
        segments.append(
            ClipExportSegmentRead(
                event_id=event.id,
                source_timestamp_seconds=event.timestamp_seconds,
                highlight_start_seconds=highlight_offset,
                duration_seconds=duration,
            )
        )
        highlight_offset += duration

    return ClipExportRead(
        id=clip_export.id,
        match_id=clip_export.match_id,
        created_by_user_id=clip_export.created_by_user_id,
        event_ids=event_ids,
        status=clip_export.status,
        filename=clip_export.filename,
        export_type=clip_export.export_type,
        player_id=clip_export.player_id,
        event_types=clip_export.event_types.split(",") if clip_export.event_types else [],
        segments=segments,
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
        event.id
        for event in sorted(selected_events, key=lambda item: (item.timestamp_seconds, item.id))
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
    dispatch_job(
        background_tasks,
        "clip_export",
        clip_export.id,
        database_bind=db.get_bind(),
    )
    return response


@router.post(
    "/api/matches/{match_id}/player-highlights",
    response_model=ClipExportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_player_highlight(
    match_id: int,
    payload: PlayerHighlightCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: ViewAuthorizedVideoUser,
) -> ClipExportRead:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    player = players.get_player(db, payload.player_id)
    if player is None or player.team_id not in {match.home_team_id, match.away_team_id}:
        raise HTTPException(status_code=422, detail="Player does not participate in this match")
    event_types = list(dict.fromkeys(payload.event_types))
    selected_events = list(
        db.scalars(
            select(Event)
            .where(
                Event.match_id == match_id,
                Event.player_id == player.id,
                Event.event_type.in_(event_types),
                Event.status == "verified",
                Event.deleted_at.is_(None),
            )
            .order_by(Event.timestamp_seconds, Event.id)
        )
    )
    if not selected_events:
        raise HTTPException(
            status_code=422,
            detail="No verified events match the selected player and event types",
        )
    video_ids = {event.video_id for event in selected_events}
    selected_videos = list(db.scalars(select(Video).where(Video.id.in_(video_ids))))
    if len(selected_videos) != len(video_ids) or any(
        video.deleted_at is not None or video.processing_status != "completed"
        for video in selected_videos
    ):
        raise HTTPException(status_code=409, detail="All event videos must be available")

    filename = f"match-{match_id}-player-{player.id}-highlight.mp4"
    clip_export = clip_exports.create_clip_export(
        db,
        match_id=match_id,
        user_id=current_user.id,
        event_ids=[event.id for event in selected_events],
        filename=filename,
        export_type="player_highlight",
        player_id=player.id,
        event_types=event_types,
    )
    response = serialize_clip_export(db, clip_export)
    dispatch_job(
        background_tasks,
        "clip_export",
        clip_export.id,
        database_bind=db.get_bind(),
    )
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
