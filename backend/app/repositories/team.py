from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team
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
