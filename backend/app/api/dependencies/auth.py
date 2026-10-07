from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import Permission, has_permission
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


def require_permission(permission: Permission):
    def check_permission(current_user: CurrentUser) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return check_permission


def require_any_permission(*permissions: Permission):
    def check_permissions(current_user: CurrentUser) -> User:
        if not any(has_permission(current_user, permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return check_permissions


ManageCompetitionDataUser = Annotated[
    User,
    Depends(require_permission(Permission.MANAGE_COMPETITION_DATA)),
]
ManageUsersUser = Annotated[
    User,
    Depends(require_permission(Permission.MANAGE_USERS)),
]
ViewAuthorizedVideoUser = Annotated[
    User,
    Depends(require_permission(Permission.VIEW_AUTHORIZED_VIDEO)),
]
UploadVideoUser = Annotated[
    User,
    Depends(require_permission(Permission.UPLOAD_AND_ANNOTATE_VIDEO)),
]
ManageMatchReportUser = Annotated[
    User,
    Depends(
        require_any_permission(
            Permission.MANAGE_COMPETITION_DATA,
            Permission.GENERATE_REPORTS,
        )
    ),
]
ManageKnowledgeBaseUser = Annotated[
    User,
    Depends(require_permission(Permission.MANAGE_KNOWLEDGE_BASE)),
]
QueryKnowledgeBaseUser = Annotated[
    User,
    Depends(require_permission(Permission.QUERY_KNOWLEDGE_BASE)),
]
UseMatchAgentUser = Annotated[
    User,
    Depends(require_permission(Permission.USE_MATCH_AGENT)),
]
