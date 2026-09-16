from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competition import Competition
from app.schemas.competition import CompetitionCreate, CompetitionUpdate


def list_competitions(db: Session) -> list[Competition]:
    statement = select(Competition).order_by(Competition.id)
    return list(db.scalars(statement).all())


def get_competition(db: Session, competition_id: int) -> Competition | None:
    return db.get(Competition, competition_id)


def create_competition(
    db: Session,
    competition_data: CompetitionCreate,
) -> Competition:
    competition = Competition(**competition_data.model_dump())
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return competition


def update_competition(
    db: Session,
    competition: Competition,
    competition_data: CompetitionUpdate,
) -> Competition:
    for field, value in competition_data.model_dump(exclude_unset=True).items():
        setattr(competition, field, value)

    db.commit()
    db.refresh(competition)
    return competition
