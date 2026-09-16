from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_session_token, normalize_email
from app.models.auth_session import AuthSession
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def create_session(
    db: Session,
    user: User,
    raw_token: str,
    max_age_seconds: int,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(seconds=max_age_seconds),
    )
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    return auth_session


def get_user_for_session(db: Session, raw_token: str) -> User | None:
    return db.scalar(
        select(User)
        .join(AuthSession)
        .where(
            AuthSession.token_hash == hash_session_token(raw_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )


def revoke_session(db: Session, raw_token: str) -> None:
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_session_token(raw_token),
            AuthSession.revoked_at.is_(None),
        )
    )
    if auth_session is None:
        return
    auth_session.revoked_at = datetime.now(UTC)
    db.commit()
