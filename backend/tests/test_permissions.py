from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.authorization import Permission, UserRole
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.models.user_permission import UserPermission
from tests.conftest import TestingSessionLocal


def create_user(
    *,
    email: str,
    role: UserRole,
    extra_permissions: tuple[Permission, ...] = (),
) -> User:
    with TestingSessionLocal() as session:
        user = User(
            email=email,
            display_name=email.split("@", maxsplit=1)[0],
            password_hash=hash_password("correct-password"),
            role=role.value,
        )
        user.permission_grants = [
            UserPermission(permission=permission.value)
            for permission in extra_permissions
        ]
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@pytest.fixture
def athlete_client() -> Generator[TestClient, None, None]:
    user = create_user(email="athlete@example.com", role=UserRole.ATHLETE)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "correct-password"},
        )
        assert response.status_code == 200
        yield test_client


@pytest.fixture
def system_admin_client() -> Generator[TestClient, None, None]:
    user = create_user(email="admin@example.com", role=UserRole.SYSTEM_ADMIN)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "correct-password"},
        )
        assert response.status_code == 200
        yield test_client


def test_athlete_cannot_bypass_hidden_write_controls(
    athlete_client: TestClient,
) -> None:
    response = athlete_client.post(
        "/api/competitions",
        json={"name": "无权创建的赛事", "season": "2026", "status": "active"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_configurable_grant_allows_coach_to_manage_competition_data() -> None:
    user = create_user(
        email="authorized-coach@example.com",
        role=UserRole.COACH_ANALYST,
        extra_permissions=(Permission.MANAGE_COMPETITION_DATA,),
    )
    with TestClient(app) as test_client:
        test_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "correct-password"},
        )
        response = test_client.post(
            "/api/competitions",
            json={"name": "授权创建的赛事", "season": "2026", "status": "active"},
        )

    assert response.status_code == 201


def test_only_system_admin_can_access_user_management(
    athlete_client: TestClient,
    system_admin_client: TestClient,
) -> None:
    denied_response = athlete_client.get("/api/admin/users")
    allowed_response = system_admin_client.get("/api/admin/users")

    assert denied_response.status_code == 403
    assert allowed_response.status_code == 200


def test_system_admin_can_create_and_configure_user(
    system_admin_client: TestClient,
) -> None:
    create_response = system_admin_client.post(
        "/api/admin/users",
        json={
            "email": "new-coach@example.com",
            "display_name": "新教练",
            "password": "initial-password",
            "role": "coach_analyst",
            "extra_permissions": ["manage_competition_data"],
        },
    )

    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["role"] == "coach_analyst"
    assert created_user["extra_permissions"] == ["manage_competition_data"]
    assert set(created_user["permissions"]) == {
        "generate_reports",
        "manage_competition_data",
        "upload_and_annotate_video",
        "view_authorized_video",
    }

    update_response = system_admin_client.patch(
        f"/api/admin/users/{created_user['id']}",
        json={"role": "athlete", "extra_permissions": []},
    )

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "athlete"
    assert update_response.json()["permissions"] == ["view_authorized_video"]
