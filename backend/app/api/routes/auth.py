from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_session_token,
    verify_password,
)
from app.db.session import get_db
from app.repositories import auth as auth_repository
from app.schemas.auth import LoginRequest, UserRead


router = APIRouter(prefix="/api/auth", tags=["authentication"])
DatabaseSession = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[
    str | None,
    Cookie(alias=settings.session_cookie_name),
]


@router.post("/login", response_model=UserRead)
def login(
    credentials: LoginRequest,
    response: Response,
    db: DatabaseSession,
) -> UserRead:
    user = auth_repository.get_user_by_email(db, credentials.email)
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(credentials.password, password_hash)

    if user is None or not password_is_valid or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    raw_token = create_session_token()
    auth_repository.create_session(
        db,
        user,
        raw_token,
        settings.session_max_age_seconds,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return user


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> UserRead:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DatabaseSession,
    session_token: SessionCookie = None,
) -> Response:
    if session_token:
        auth_repository.revoke_session(db, session_token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
