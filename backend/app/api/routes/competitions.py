from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import competition as competition_repository
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionRead,
    CompetitionUpdate,
)


router = APIRouter(prefix="/api/competitions", tags=["competitions"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[CompetitionRead])
def list_competitions(db: DatabaseSession) -> list[CompetitionRead]:
    return competition_repository.list_competitions(db)


@router.post("", response_model=CompetitionRead, status_code=status.HTTP_201_CREATED)
def create_competition(
    competition_data: CompetitionCreate,
    db: DatabaseSession,
) -> CompetitionRead:
    return competition_repository.create_competition(db, competition_data)


@router.get("/{competition_id}", response_model=CompetitionRead)
def get_competition(competition_id: int, db: DatabaseSession) -> CompetitionRead:
    competition = competition_repository.get_competition(db, competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )
    return competition


@router.patch("/{competition_id}", response_model=CompetitionRead)
def update_competition(
    competition_id: int,
    competition_data: CompetitionUpdate,
    db: DatabaseSession,
) -> CompetitionRead:
    competition = competition_repository.get_competition(db, competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )
    return competition_repository.update_competition(
        db,
        competition,
        competition_data,
    )
