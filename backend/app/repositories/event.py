from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.schemas.event import EventCreate


def list_match_events(db: Session, match_id: int) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.match_id == match_id, Event.deleted_at.is_(None))
            .order_by(Event.timestamp_seconds, Event.id)
        )
    )


def create_event(
    db: Session,
    *,
    match_id: int,
    event_data: EventCreate,
    team_id: int | None,
    user_id: int,
) -> Event:
    event = Event(
        match_id=match_id,
        **event_data.model_dump(exclude={"team_id"}),
        team_id=team_id,
        source="manual",
        status="draft",
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
