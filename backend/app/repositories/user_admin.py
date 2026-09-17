from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.authorization import Permission, UserRole
from app.core.security import hash_password, normalize_email
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.user_permission import UserPermission
from app.schemas.user_admin import AdminUserCreate, AdminUserUpdate


def list_users(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .options(selectinload(User.permission_grants))
            .order_by(User.created_at, User.id)
        )
    )


def get_user(db: Session, user_id: int) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.permission_grants))
        .where(User.id == user_id)
    )


def create_user(db: Session, data: AdminUserCreate) -> User:
    user = User(
        email=normalize_email(data.email),
        display_name=data.display_name.strip(),
        password_hash=hash_password(data.password),
        role=data.role.value,
    )
    user.permission_grants = [
        UserPermission(permission=permission.value)
        for permission in sorted(set(data.extra_permissions), key=str)
    ]
    db.add(user)
    db.commit()
    return get_user(db, user.id) or user


def update_user(db: Session, user: User, data: AdminUserUpdate) -> User:
    changes = data.model_dump(exclude_unset=True, exclude={"extra_permissions"})
    for field, value in changes.items():
        if field == "role" and value is not None:
            value = value.value
        if field == "display_name" and value is not None:
            value = value.strip()
        setattr(user, field, value)

    if data.extra_permissions is not None:
        user.permission_grants = [
            UserPermission(permission=permission.value)
            for permission in sorted(set(data.extra_permissions), key=str)
        ]

    if data.is_active is False:
        revoke_user_sessions(db, user.id)

    db.commit()
    return get_user(db, user.id) or user


def count_active_system_admins(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.SYSTEM_ADMIN.value,
                User.is_active.is_(True),
            )
        )
        or 0
    )


def revoke_user_sessions(db: Session, user_id: int) -> None:
    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    revoked_at = datetime.now(UTC)
    for auth_session in sessions:
        auth_session.revoked_at = revoked_at


def get_extra_permissions(user: User) -> list[Permission]:
    permissions: list[Permission] = []
    for grant in user.permission_grants:
        try:
            permissions.append(Permission(grant.permission))
        except ValueError:
            continue
    return sorted(set(permissions), key=str)
