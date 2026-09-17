from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models.team import Team
from app.models.match import Match
from app.models.player import Player
from app.schemas.team import TeamCreate, TeamUpdate


def list_teams(db: Session) -> list[Team]:
    return list(db.scalars(select(Team).order_by(Team.id)).all())


def get_team(db: Session, team_id: int) -> Team | None:
    return db.get(Team, team_id)


def create_team(db: Session, team_data: TeamCreate) -> Team:
    team = Team(**team_data.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def update_team(db: Session, team: Team, team_data: TeamUpdate) -> Team:
    for field, value in team_data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)
    return team


def has_players_or_matches(db: Session, team_id: int) -> bool:
    has_players = db.scalar(select(exists().where(Player.team_id == team_id)))
    has_matches = db.scalar(
        select(
            exists().where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
            )
        )
    )
    return bool(has_players or has_matches)


def delete_team(db: Session, team: Team) -> None:
    db.delete(team)
    db.commit()
