from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import UploadVideoUser, ViewAuthorizedVideoUser
from app.db.session import get_db
from app.repositories import analysis_task as analysis_tasks
from app.repositories import match as matches
from app.repositories import video as videos
from app.schemas.analysis_task import AnalysisTaskRead
from app.services.analysis_task import process_analysis_task


router = APIRouter(tags=["analysis-tasks"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def serialize_analysis_task(task, *, reused: bool = False) -> AnalysisTaskRead:
    return AnalysisTaskRead.model_validate(task).model_copy(update={"reused": reused})


@router.get(
    "/api/matches/{match_id}/analysis-tasks",
    response_model=list[AnalysisTaskRead],
)
def list_match_analysis_tasks(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> list[AnalysisTaskRead]:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return [
        serialize_analysis_task(task)
        for task in analysis_tasks.list_match_analysis_tasks(db, match_id)
    ]


@router.get("/api/analysis-tasks/{task_id}", response_model=AnalysisTaskRead)
def get_analysis_task(
    task_id: str,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> AnalysisTaskRead:
    task = analysis_tasks.get_analysis_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Analysis task not found")
    return serialize_analysis_task(task)


@router.post(
    "/api/videos/{video_id}/analysis-tasks",
    response_model=AnalysisTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_analysis_task(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: UploadVideoUser,
) -> AnalysisTaskRead:
    video = videos.get_video(db, video_id)
    if video is None or video.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video processing must complete before AI analysis",
        )

    task, reused = analysis_tasks.create_or_get_active_task(
        db,
        match_id=video.match_id,
        video_id=video.id,
        user_id=current_user.id,
    )
    if not reused:
        background_tasks.add_task(process_analysis_task, task.id, db.get_bind())
    return serialize_analysis_task(task, reused=reused)
