import logging
from time import perf_counter
from typing import Callable

from sqlalchemy.engine import Connection, Engine

from app.db.session import engine
from app.services.analysis_task import process_analysis_task
from app.services.clip_export import process_clip_export
from app.services.video_processing import process_video


logger = logging.getLogger("handball.worker")


def _run_job(
    job_type: str,
    task_id: str | int,
    function: Callable[..., None],
    database_bind: Engine | Connection | None = None,
) -> None:
    started_at = perf_counter()
    logger.info(
        "worker_job_started",
        extra={"job_type": job_type, "task_id": str(task_id), "status": "running"},
    )
    try:
        function(task_id, database_bind if database_bind is not None else engine)
    except Exception as error:
        logger.exception(
            "worker_job_failed",
            extra={
                "job_type": job_type,
                "task_id": str(task_id),
                "status": "failed",
                "error_type": type(error).__name__,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise
    logger.info(
        "worker_job_completed",
        extra={
            "job_type": job_type,
            "task_id": str(task_id),
            "status": "completed",
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )


def process_video_job(
    video_id: int,
    database_bind: Engine | Connection | None = None,
) -> None:
    _run_job("video_processing", video_id, process_video, database_bind)


def process_clip_export_job(
    clip_export_id: int,
    database_bind: Engine | Connection | None = None,
) -> None:
    _run_job("clip_export", clip_export_id, process_clip_export, database_bind)


def process_analysis_task_job(
    task_id: str,
    database_bind: Engine | Connection | None = None,
) -> None:
    _run_job("ai_analysis", task_id, process_analysis_task, database_bind)
