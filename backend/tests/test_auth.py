from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.auth_session import AuthSession
from app.models.user import User
from tests.conftest import TestingSessionLocal


def test_valid_credentials_create_session_and_return_user(
    anonymous_client: TestClient,
    registered_user: User,
) -> None:
    login_response = anonymous_client.post(
        "/api/auth/login",
        json={"email": "  COACH@example.com ", "password": "correct-password"},
    )

    assert login_response.status_code == 200
    assert login_response.json() == {
        "id": registered_user.id,
        "email": "coach@example.com",
        "display_name": "测试教练",
        "role": "competition_admin",
        "is_active": True,
        "permissions": ["manage_competition_data", "view_authorized_video"],
    }
    assert "HttpOnly" in login_response.headers["set-cookie"]

    me_response = anonymous_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "coach@example.com"


def test_wrong_email_and_password_return_same_error(
    anonymous_client: TestClient,
    registered_user: User,
) -> None:
    wrong_email_response = anonymous_client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    wrong_password_response = anonymous_client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "wrong-password"},
    )

    expected_error = {"detail": "Invalid email or password"}
    assert wrong_email_response.status_code == 401
    assert wrong_password_response.status_code == 401
    assert wrong_email_response.json() == expected_error
    assert wrong_password_response.json() == expected_error


def test_expired_session_is_rejected(
    anonymous_client: TestClient,
    registered_user: User,
) -> None:
    anonymous_client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "correct-password"},
    )
    with TestingSessionLocal() as db:
        auth_session = db.scalar(select(AuthSession))
        assert auth_session is not None
        auth_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    response = anonymous_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Session expired or invalid"}


def test_logout_revokes_session(
    anonymous_client: TestClient,
    registered_user: User,
) -> None:
    anonymous_client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "correct-password"},
    )

    assert anonymous_client.post("/api/auth/logout").status_code == 204
    assert anonymous_client.get("/api/auth/me").status_code == 401


def test_write_endpoint_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/api/competitions",
        json={"name": "测试赛事", "season": "2026", "status": "active"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
