from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.schemas.event import EventCreate, EventType, EventUpdate


def list_match_events(
    db: Session,
    match_id: int,
    *,
    event_type: EventType | None = None,
    team_id: int | None = None,
    player_id: int | None = None,
    status: str | None = None,
) -> list[Event]:
    statement = select(Event).where(
        Event.match_id == match_id,
        Event.deleted_at.is_(None),
    )
    if event_type is not None:
        statement = statement.where(Event.event_type == event_type)
    if team_id is not None:
        statement = statement.where(Event.team_id == team_id)
    if player_id is not None:
        statement = statement.where(Event.player_id == player_id)
    if status is not None:
        statement = statement.where(Event.status == status)
    return list(
        db.scalars(
            statement.order_by(Event.timestamp_seconds, Event.id)
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


def get_event(db: Session, event_id: int) -> Event | None:
    return db.get(Event, event_id)


def update_event(
    db: Session,
    *,
    event: Event,
    event_data: EventUpdate,
    team_id: int | None,
    user_id: int,
) -> Event:
    values = event_data.model_dump(exclude_unset=True, exclude={"team_id"})
    for field, value in values.items():
        setattr(event, field, value)
    if "team_id" in event_data.model_fields_set or "player_id" in event_data.model_fields_set:
        event.team_id = team_id
    event.updated_by_user_id = user_id
    event.status = "draft"
    event.verified_at = None
    event.verified_by_user_id = None
    db.commit()
    db.refresh(event)
    return event


def soft_delete_event(db: Session, event: Event, user_id: int) -> None:
    event.deleted_at = datetime.now(timezone.utc)
    event.updated_by_user_id = user_id
    db.commit()


def verify_event(db: Session, event: Event, user_id: int) -> Event:
    event.status = "verified"
    event.verified_at = datetime.now(timezone.utc)
    event.verified_by_user_id = user_id
    event.updated_by_user_id = user_id
    db.commit()
    db.refresh(event)
    return event
