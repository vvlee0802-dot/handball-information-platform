from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import ManageCompetitionDataUser
from app.db.session import get_db
from app.repositories import competition as competitions
from app.repositories import match as matches
from app.repositories import team as teams
from app.repositories import venue as venues
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate


router = APIRouter(prefix="/api/matches", tags=["matches"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def validate_references(db: Session, data: MatchCreate) -> None:
    checks = [
        (competitions.get_competition(db, data.competition_id), "Referenced competition not found"),
        (teams.get_team(db, data.home_team_id), "Referenced home team not found"),
        (teams.get_team(db, data.away_team_id), "Referenced away team not found"),
        (venues.get_venue(db, data.venue_id), "Referenced venue not found"),
    ]
    for record, message in checks:
        if record is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


@router.get("", response_model=list[MatchRead])
def list_matches(db: DatabaseSession) -> list[MatchRead]:
    return matches.list_matches(db)


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(
    data: MatchCreate,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> MatchRead:
    validate_references(db, data)
    return matches.create_match(db, data)


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: DatabaseSession) -> MatchRead:
    match = matches.get_match(db, match_id)
    if match is None: raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}", response_model=MatchRead)
def update_match(
    match_id: int,
    data: MatchUpdate,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> MatchRead:
    match = matches.get_match(db, match_id)
    if match is None: raise HTTPException(status_code=404, detail="Match not found")
    merged = MatchCreate.model_validate({
        "competition_id": match.competition_id, "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id, "venue_id": match.venue_id,
        "match_date": match.match_date, "start_time": match.start_time,
        "stage": match.stage, "status": match.status,
        "home_score": match.home_score, "away_score": match.away_score,
        **data.model_dump(exclude_unset=True),
    })
    validate_references(db, merged)
    return matches.update_match(db, match, data)
