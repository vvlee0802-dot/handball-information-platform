from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories import auth as auth_repository


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=settings.session_cookie_name),
    ] = None,
) -> User:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = auth_repository.get_user_for_session(db, session_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
