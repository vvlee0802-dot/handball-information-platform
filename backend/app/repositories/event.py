from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.schemas.event import EventCreate, EventType, EventUpdate
from app.services.goal_detection import GoalCandidatePrediction


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
    verified_at = datetime.now(timezone.utc)
    event = Event(
        match_id=match_id,
        **event_data.model_dump(exclude={"team_id"}),
        team_id=team_id,
        source="manual",
        status="verified",
        verified_at=verified_at,
        verified_by_user_id=user_id,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def create_ai_candidates(
    db: Session,
    *,
    match_id: int,
    video_id: int,
    analysis_task_id: str,
    model_version: str,
    predictions: list[GoalCandidatePrediction],
    user_id: int,
) -> list[Event]:
    candidates = [
        Event(
            match_id=match_id,
            video_id=video_id,
            event_type="goal",
            timestamp_seconds=prediction.timestamp_seconds,
            team_id=None,
            player_id=None,
            note="AI 候选进球，等待人工确认",
            source="ai",
            confidence=prediction.confidence,
            model_version=model_version,
            analysis_task_id=analysis_task_id,
            status="draft",
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        for prediction in predictions
    ]
    db.add_all(candidates)
    db.flush()
    return candidates


def list_verified_manual_goals(
    db: Session,
    *,
    match_id: int,
    video_id: int,
) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(
                Event.match_id == match_id,
                Event.video_id == video_id,
                Event.event_type == "goal",
                Event.source == "manual",
                Event.status == "verified",
                Event.deleted_at.is_(None),
            )
            .order_by(Event.timestamp_seconds, Event.id)
        )
    )


def soft_delete_ai_drafts_for_video(
    db: Session,
    *,
    video_id: int,
    user_id: int,
) -> None:
    now = datetime.now(timezone.utc)
    drafts = list(
        db.scalars(
            select(Event).where(
                Event.video_id == video_id,
                Event.source == "ai",
                Event.status == "draft",
                Event.deleted_at.is_(None),
            )
        )
    )
    for draft in drafts:
        draft.deleted_at = now
        draft.updated_by_user_id = user_id


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
    if event.source == "manual":
        event.status = "verified"
        event.verified_at = datetime.now(timezone.utc)
        event.verified_by_user_id = user_id
    else:
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
