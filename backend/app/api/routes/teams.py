from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import team as team_repository
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate


router = APIRouter(prefix="/api/teams", tags=["teams"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[TeamRead])
def list_teams(db: DatabaseSession) -> list[TeamRead]:
    return team_repository.list_teams(db)


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(team_data: TeamCreate, db: DatabaseSession) -> TeamRead:
    return team_repository.create_team(db, team_data)


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: DatabaseSession) -> TeamRead:
    team = team_repository.get_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.patch("/{team_id}", response_model=TeamRead)
def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: DatabaseSession,
) -> TeamRead:
    team = team_repository.get_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team_repository.update_team(db, team, team_data)
