from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    ManageCompetitionDataUser,
    UploadVideoUser,
    ViewAuthorizedVideoUser,
)
from app.db.session import get_db
from app.repositories import match as matches
from app.repositories import player as players
from app.repositories import player_stats
from app.models.event import Event
from app.schemas.event import EventRead
from app.schemas.player_stats import (
    MatchPlayerStatsRead,
    PlayerAssignmentAuditRead,
    PlayerAssignmentBatchRead,
    PlayerAssignmentBatchUpdate,
    PlayerStatsMetric,
)
from sqlalchemy import select


router = APIRouter(prefix="/api/matches/{match_id}/player-stats", tags=["player-stats"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=MatchPlayerStatsRead)
def read_match_player_stats(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> MatchPlayerStatsRead:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return player_stats.get_match_player_stats(db, match)


def get_participating_player_or_404(db: Session, match, player_id: int):
    player = players.get_player(db, player_id)
    if player is None or player.team_id not in {match.home_team_id, match.away_team_id}:
        raise HTTPException(status_code=404, detail="Player does not participate in this match")
    return player


@router.get("/{player_id}/events", response_model=list[EventRead])
def read_player_metric_events(
    match_id: int,
    player_id: int,
    metric: PlayerStatsMetric,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> list[EventRead]:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    get_participating_player_or_404(db, match, player_id)
    return player_stats.list_player_metric_events(
        db,
        match_id=match_id,
        player_id=player_id,
        metric=metric,
    )


@router.post("/player-assignment", response_model=PlayerAssignmentBatchRead)
def update_event_player_assignments(
    match_id: int,
    payload: PlayerAssignmentBatchUpdate,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> PlayerAssignmentBatchRead:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if len(set(payload.event_ids)) != len(payload.event_ids):
        raise HTTPException(status_code=422, detail="Event IDs cannot be duplicated")
    new_player = get_participating_player_or_404(db, match, payload.player_id)
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
        raise HTTPException(status_code=422, detail="All events must be active and belong to this match")
    ordered_events = sorted(selected_events, key=lambda event: payload.event_ids.index(event.id))
    affected_count, updated_events = player_stats.reassign_events_to_player(
        db,
        events=ordered_events,
        new_player=new_player,
        changed_by_user_id=current_user.id,
        changed_by_user_name=current_user.display_name,
    )
    return PlayerAssignmentBatchRead(
        requested_count=len(payload.event_ids),
        affected_count=affected_count,
        events=[EventRead.model_validate(event) for event in updated_events],
    )


@router.get("/player-assignment/audits", response_model=list[PlayerAssignmentAuditRead])
def read_player_assignment_audits(
    match_id: int,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> list[PlayerAssignmentAuditRead]:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return player_stats.list_player_assignment_audits(db, match_id=match_id)
