from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis_tasks import router as analysis_tasks_router
from app.api.routes.ai_match_reports import router as ai_match_reports_router
from app.api.routes.agent import router as agent_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.knowledge_qa import router as knowledge_qa_router
from app.api.routes.knowledge_evaluations import router as knowledge_evaluations_router
from app.api.routes.clip_exports import router as clip_exports_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.competitions import router as competitions_router
from app.api.routes.events import router as events_router
from app.api.routes.matches import router as matches_router
from app.api.routes.match_reports import router as match_reports_router
from app.api.routes.players import router as players_router
from app.api.routes.player_stats import router as player_stats_router
from app.api.routes.teams import router as teams_router
from app.api.routes.venues import router as venues_router
from app.api.routes.videos import router as videos_router
from app.db.session import engine
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.observability import request_context_middleware


configure_logging()

app = FastAPI(
    title="Handball Information Platform API",
    version=settings.app_version,
)

app.middleware("http")(request_context_middleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-Request-ID", "X-Original-Filename", "X-Video-Type", "X-Video-Duration-Seconds"],
)
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(auth_router)
app.include_router(analysis_tasks_router)
app.include_router(ai_match_reports_router)
app.include_router(agent_router)
app.include_router(knowledge_router)
app.include_router(knowledge_qa_router)
app.include_router(knowledge_evaluations_router)
app.include_router(clip_exports_router)
app.include_router(admin_users_router)
app.include_router(competitions_router)
app.include_router(events_router)
app.include_router(matches_router)
app.include_router(match_reports_router)
app.include_router(players_router)
app.include_router(player_stats_router)
app.include_router(teams_router)
app.include_router(venues_router)
app.include_router(videos_router)


def database_health() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from exc


def redis_health() -> str:
    if settings.task_queue_mode != "rq":
        return "disabled"
    try:
        from redis import Redis

        Redis.from_url(settings.redis_url).ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Task queue is unavailable") from exc
    return "connected"


@app.get("/api/health/live")
def liveness_check() -> dict[str, str]:
    return {"status": "ok", "service": "handball-api", "version": settings.app_version}


@app.get("/api/health/ready")
def readiness_check() -> dict[str, str]:
    database_health()
    queue_status = redis_health()
    return {
        "status": "ok",
        "service": "handball-api",
        "version": settings.app_version,
        "database": "connected",
        "task_queue": queue_status,
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    database_health()
    queue_status = redis_health()

    return {
        "status": "ok",
        "service": "handball-api",
        "version": settings.app_version,
        "database": "connected",
        "task_queue": queue_status,
    }
