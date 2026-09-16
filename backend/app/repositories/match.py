from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.schemas.match import MatchCreate, MatchUpdate


def list_matches(db: Session) -> list[Match]:
    return list(db.scalars(select(Match).order_by(Match.match_date, Match.start_time, Match.id)).all())


def get_match(db: Session, match_id: int) -> Match | None:
    return db.get(Match, match_id)


def create_match(db: Session, data: MatchCreate) -> Match:
    match = Match(**data.model_dump())
    db.add(match); db.commit(); db.refresh(match)
    return match


def update_match(db: Session, match: Match, data: MatchUpdate) -> Match:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    db.commit(); db.refresh(match)
    return match
