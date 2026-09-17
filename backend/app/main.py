from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.auth import router as auth_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.competitions import router as competitions_router
from app.api.routes.matches import router as matches_router
from app.api.routes.players import router as players_router
from app.api.routes.teams import router as teams_router
from app.api.routes.venues import router as venues_router
from app.api.routes.videos import router as videos_router
from app.db.session import engine

app = FastAPI(
    title="Handball Information Platform API",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(competitions_router)
app.include_router(matches_router)
app.include_router(players_router)
app.include_router(teams_router)
app.include_router(venues_router)
app.include_router(videos_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from exc

    return {
        "status": "ok",
        "service": "handball-api",
        "database": "connected",
    }
