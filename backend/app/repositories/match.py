from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.video import Video
from app.models.video_upload import VideoUploadSession
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


def has_active_video_data(db: Session, match_id: int) -> bool:
    has_videos = db.scalar(
        select(
            exists().where(
                Video.match_id == match_id,
                Video.deleted_at.is_(None),
            )
        )
    )
    has_uploads = db.scalar(
        select(
            exists().where(
                VideoUploadSession.match_id == match_id,
                VideoUploadSession.status.in_(["uploading", "assembling", "failed"]),
            )
        )
    )
    return bool(has_videos or has_uploads)


def delete_match(db: Session, match: Match) -> None:
    db.delete(match)
    db.commit()
