from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import UploadVideoUser, ViewAuthorizedVideoUser
from app.db.session import get_db
from app.repositories import event as events
from app.repositories import match as matches
from app.repositories import player as players
from app.repositories import video as videos
from app.schemas.event import EventCreate, EventRead, EventType, EventUpdate


router = APIRouter(prefix="/api/matches/{match_id}/events", tags=["events"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_match_or_404(db: Session, match_id: int):
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


def validate_event_relations(
    db: Session,
    *,
    match_id: int,
    event_data: EventCreate,
) -> int | None:
    match = get_match_or_404(db, match_id)
    video = videos.get_video(db, event_data.video_id)
    if video is None or video.deleted_at is not None or video.match_id != match_id:
        raise HTTPException(status_code=422, detail="Video does not belong to this match")
    if video.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video processing must complete before annotation",
        )
    if (
        video.duration_seconds is not None
        and event_data.timestamp_seconds > video.duration_seconds
    ):
        raise HTTPException(status_code=422, detail="Event timestamp exceeds video duration")

    participant_team_ids = {match.home_team_id, match.away_team_id}
    resolved_team_id = event_data.team_id
    if resolved_team_id is not None and resolved_team_id not in participant_team_ids:
        raise HTTPException(status_code=422, detail="Team does not participate in this match")

    if event_data.player_id is not None:
        player = players.get_player(db, event_data.player_id)
        if player is None:
            raise HTTPException(status_code=422, detail="Player not found")
        if player.team_id not in participant_team_ids:
            raise HTTPException(status_code=422, detail="Player does not participate in this match")
        if resolved_team_id is not None and resolved_team_id != player.team_id:
            raise HTTPException(status_code=422, detail="Player does not belong to the selected team")
        resolved_team_id = player.team_id
    return resolved_team_id


def get_active_event_or_404(db: Session, match_id: int, event_id: int):
    event = events.get_event(db, event_id)
    if event is None or event.deleted_at is not None or event.match_id != match_id:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("", response_model=list[EventRead])
def list_events(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
    event_type: EventType | None = None,
    team_id: int | None = None,
    player_id: int | None = None,
    status: Literal["draft", "verified"] | None = None,
) -> list[EventRead]:
    get_match_or_404(db, match_id)
    return events.list_match_events(
        db,
        match_id,
        event_type=event_type,
        team_id=team_id,
        player_id=player_id,
        status=status,
    )


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    match_id: int,
    event_data: EventCreate,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> EventRead:
    team_id = validate_event_relations(db, match_id=match_id, event_data=event_data)
    return events.create_event(
        db,
        match_id=match_id,
        event_data=event_data,
        team_id=team_id,
        user_id=current_user.id,
    )


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    match_id: int,
    event_id: int,
    event_data: EventUpdate,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> EventRead:
    event = get_active_event_or_404(db, match_id, event_id)
    if not event_data.model_fields_set:
        raise HTTPException(status_code=422, detail="At least one event field is required")
    merged = EventCreate.model_validate(
        {
            "video_id": event.video_id,
            "event_type": event.event_type,
            "timestamp_seconds": event.timestamp_seconds,
            "team_id": event.team_id,
            "player_id": event.player_id,
            "note": event.note,
            **event_data.model_dump(exclude_unset=True),
        }
    )
    team_id = validate_event_relations(db, match_id=match_id, event_data=merged)
    return events.update_event(
        db,
        event=event,
        event_data=event_data,
        team_id=team_id,
        user_id=current_user.id,
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    match_id: int,
    event_id: int,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> None:
    event = get_active_event_or_404(db, match_id, event_id)
    events.soft_delete_event(db, event, current_user.id)


@router.post("/{event_id}/verify", response_model=EventRead)
def verify_event(
    match_id: int,
    event_id: int,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> EventRead:
    event = get_active_event_or_404(db, match_id, event_id)
    return events.verify_event(db, event, current_user.id)
