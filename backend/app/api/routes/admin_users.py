from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import ManageUsersUser
from app.core.authorization import UserRole, get_effective_permissions
from app.core.security import normalize_email
from app.db.session import get_db
from app.repositories import auth as auth_repository
from app.repositories import user_admin as user_repository
from app.schemas.user_admin import AdminUserCreate, AdminUserRead, AdminUserUpdate


router = APIRouter(prefix="/api/admin/users", tags=["user administration"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def to_admin_user_read(user) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=UserRole(user.role),
        is_active=user.is_active,
        permissions=sorted(get_effective_permissions(user), key=str),
        extra_permissions=user_repository.get_extra_permissions(user),
    )


@router.get("", response_model=list[AdminUserRead])
def list_users(
    db: DatabaseSession,
    _current_user: ManageUsersUser,
) -> list[AdminUserRead]:
    return [to_admin_user_read(user) for user in user_repository.list_users(db)]


@router.post("", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: AdminUserCreate,
    db: DatabaseSession,
    _current_user: ManageUsersUser,
) -> AdminUserRead:
    if auth_repository.get_user_by_email(db, normalize_email(data.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    return to_admin_user_read(user_repository.create_user(db, data))


@router.patch("/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: DatabaseSession,
    current_user: ManageUsersUser,
) -> AdminUserRead:
    user = user_repository.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        if data.role is not None and data.role.value != user.role:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="You cannot change your own system role",
            )
        if data.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="You cannot deactivate your own account",
            )

    removes_active_system_admin = (
        user.role == UserRole.SYSTEM_ADMIN.value
        and user.is_active
        and (
            (data.role is not None and data.role != UserRole.SYSTEM_ADMIN)
            or data.is_active is False
        )
    )
    if removes_active_system_admin and user_repository.count_active_system_admins(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one active system administrator is required",
        )

    return to_admin_user_read(user_repository.update_user(db, user, data))
