from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import ManageCompetitionDataUser
from app.db.session import get_db
from app.repositories import player as player_repository
from app.repositories import team as team_repository
from app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate


router = APIRouter(prefix="/api/players", tags=["players"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def ensure_team_exists(db: Session, team_id: int) -> None:
    if team_repository.get_team(db, team_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Referenced team not found",
        )


@router.get("", response_model=list[PlayerRead])
def list_players(
    db: DatabaseSession,
    team_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[PlayerRead]:
    return player_repository.list_players(db, team_id)


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(
    player_data: PlayerCreate,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> PlayerRead:
    ensure_team_exists(db, player_data.team_id)
    return player_repository.create_player(db, player_data)


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, db: DatabaseSession) -> PlayerRead:
    player = player_repository.get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.patch("/{player_id}", response_model=PlayerRead)
def update_player(
    player_id: int,
    player_data: PlayerUpdate,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> PlayerRead:
    player = player_repository.get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    if player_data.team_id is not None:
        ensure_team_exists(db, player_data.team_id)
    return player_repository.update_player(db, player, player_data)


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(
    player_id: int,
    db: DatabaseSession,
    _current_user: ManageCompetitionDataUser,
) -> None:
    player = player_repository.get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    if player_repository.has_events(db, player_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该球员仍有关联比赛事件，请先处理相关事件。",
        )
    player_repository.delete_player(db, player)
