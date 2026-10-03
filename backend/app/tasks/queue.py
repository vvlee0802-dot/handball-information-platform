from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.engine import Connection, Engine

from app.core.config import settings
from app.tasks import jobs


JOB_FUNCTIONS: dict[str, Callable[..., None]] = {
    "video_processing": jobs.process_video_job,
    "clip_export": jobs.process_clip_export_job,
    "ai_analysis": jobs.process_analysis_task_job,
}


def dispatch_job(
    background_tasks: BackgroundTasks,
    job_type: str,
    *arguments: Any,
    database_bind: Engine | Connection | None = None,
) -> str | None:
    function = JOB_FUNCTIONS[job_type]
    if settings.task_queue_mode == "background":
        background_tasks.add_task(function, *arguments, database_bind=database_bind)
        return None

    from redis import Redis
    from rq import Queue

    queue = Queue(settings.task_queue_name, connection=Redis.from_url(settings.redis_url))
    job = queue.enqueue(
        function,
        *arguments,
        job_timeout="12h",
        result_ttl=86400,
        failure_ttl=604800,
    )
    return job.id
