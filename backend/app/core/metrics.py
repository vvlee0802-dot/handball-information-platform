from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram
from redis import Redis
from rq import Queue, Worker
from rq.registry import FailedJobRegistry
from sqlalchemy import text
from sqlalchemy.engine import Engine
from starlette.responses import Response

from app.core.config import settings
from app.db.session import engine

REQUESTS_TOTAL = Counter(
    "handball_http_requests_total",
    "HTTP requests handled by the API.",
    ("method", "path", "status"),
)
REQUEST_DURATION_SECONDS = Histogram(
    "handball_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ("method", "path"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 180),
)
REQUESTS_IN_PROGRESS = Gauge(
    "handball_http_requests_in_progress",
    "HTTP requests currently being processed.",
    ("method",),
)
DEPENDENCY_UP = Gauge(
    "handball_dependency_up",
    "Whether a required runtime dependency is reachable.",
    ("dependency",),
)
TASK_RECORDS = Gauge(
    "handball_task_records",
    "Persisted background and AI task records grouped by type and status.",
    ("task_type", "status"),
)
RQ_QUEUE_DEPTH = Gauge(
    "handball_rq_queue_depth",
    "Jobs currently waiting in the configured RQ queue.",
    ("queue",),
)
RQ_FAILED_JOBS = Gauge(
    "handball_rq_failed_jobs",
    "Failed jobs retained by the configured RQ queue.",
    ("queue",),
)
RQ_WORKERS = Gauge(
    "handball_rq_workers",
    "RQ workers in a healthy idle or busy state.",
    ("queue",),
)


TASK_TABLES = {
    "video_analysis": "analysis_tasks",
    "clip_export": "clip_exports",
    "ai_match_report": "ai_match_reports",
    "knowledge_document": "knowledge_documents",
    "match_agent": "agent_runs",
}


def route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else request.url.path


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path == "/internal/metrics":
        return await call_next(request)

    method = request.method
    status_code = 500
    started_at = perf_counter()
    REQUESTS_IN_PROGRESS.labels(method=method).inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        path = route_label(request)
        REQUESTS_IN_PROGRESS.labels(method=method).dec()
        REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
        REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(
            perf_counter() - started_at
        )


def refresh_database_metrics(database_engine: Engine = engine) -> None:
    TASK_RECORDS.clear()
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            DEPENDENCY_UP.labels(dependency="database").set(1)
            for task_type, table_name in TASK_TABLES.items():
                rows = connection.execute(
                    text(f"SELECT status, COUNT(*) AS count FROM {table_name} GROUP BY status")
                )
                for row in rows:
                    TASK_RECORDS.labels(task_type=task_type, status=row.status).set(row.count)
    except Exception:
        DEPENDENCY_UP.labels(dependency="database").set(0)


def refresh_queue_metrics() -> None:
    queue_name = settings.task_queue_name
    if settings.task_queue_mode != "rq":
        DEPENDENCY_UP.labels(dependency="redis").set(1)
        RQ_QUEUE_DEPTH.labels(queue=queue_name).set(0)
        RQ_FAILED_JOBS.labels(queue=queue_name).set(0)
        RQ_WORKERS.labels(queue=queue_name).set(0)
        return

    try:
        connection = Redis.from_url(settings.redis_url)
        connection.ping()
        queue = Queue(queue_name, connection=connection)
        failed_registry = FailedJobRegistry(queue=queue)
        healthy_workers = sum(
            worker.get_state() in {"busy", "idle"}
            for worker in Worker.all(connection=connection, queue=queue)
        )
        DEPENDENCY_UP.labels(dependency="redis").set(1)
        RQ_QUEUE_DEPTH.labels(queue=queue_name).set(queue.count)
        RQ_FAILED_JOBS.labels(queue=queue_name).set(failed_registry.count)
        RQ_WORKERS.labels(queue=queue_name).set(healthy_workers)
    except Exception:
        DEPENDENCY_UP.labels(dependency="redis").set(0)
        RQ_QUEUE_DEPTH.labels(queue=queue_name).set(0)
        RQ_WORKERS.labels(queue=queue_name).set(0)


def refresh_operational_metrics() -> None:
    refresh_database_metrics()
    refresh_queue_metrics()
