from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.event import Event
from app.schemas.player import PlayerCreate, PlayerUpdate


def list_players(db: Session, team_id: int | None = None) -> list[Player]:
    statement = select(Player).order_by(Player.id)
    if team_id is not None:
        statement = statement.where(Player.team_id == team_id)
    return list(db.scalars(statement).all())


def get_player(db: Session, player_id: int) -> Player | None:
    return db.get(Player, player_id)


def create_player(db: Session, player_data: PlayerCreate) -> Player:
    player = Player(**player_data.model_dump())
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def update_player(db: Session, player: Player, player_data: PlayerUpdate) -> Player:
    for field, value in player_data.model_dump(exclude_unset=True).items():
        setattr(player, field, value)

    db.commit()
    db.refresh(player)
    return player


def delete_player(db: Session, player: Player) -> None:
    db.delete(player)
    db.commit()


def has_events(db: Session, player_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Event.player_id == player_id))))
