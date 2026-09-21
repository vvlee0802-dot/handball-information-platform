from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.analysis_task import AnalysisTask


ACTIVE_STATUSES = ("queued", "running")


def get_analysis_task(db: Session, task_id: str) -> AnalysisTask | None:
    return db.get(AnalysisTask, task_id)


def get_active_video_task(db: Session, video_id: int) -> AnalysisTask | None:
    return db.scalar(
        select(AnalysisTask)
        .where(
            AnalysisTask.video_id == video_id,
            AnalysisTask.status.in_(ACTIVE_STATUSES),
        )
        .order_by(AnalysisTask.created_at.desc())
    )


def list_match_analysis_tasks(db: Session, match_id: int) -> list[AnalysisTask]:
    return list(
        db.scalars(
            select(AnalysisTask)
            .where(AnalysisTask.match_id == match_id)
            .order_by(AnalysisTask.created_at.desc(), AnalysisTask.id.desc())
        )
    )


def create_or_get_active_task(
    db: Session,
    *,
    match_id: int,
    video_id: int,
    user_id: int,
) -> tuple[AnalysisTask, bool]:
    existing = get_active_video_task(db, video_id)
    if existing is not None:
        return existing, True

    task = AnalysisTask(
        id=str(uuid4()),
        match_id=match_id,
        video_id=video_id,
        created_by_user_id=user_id,
    )
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_active_video_task(db, video_id)
        if existing is None:
            raise
        return existing, True
    db.refresh(task)
    return task, False
