from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User


test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


def override_get_db() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def registered_user() -> User:
    with TestingSessionLocal() as session:
        user = User(
            email="coach@example.com",
            display_name="测试教练",
            password_hash=hash_password("correct-password"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@pytest.fixture
def anonymous_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(registered_user: User) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": registered_user.email,
                "password": "correct-password",
            },
        )
        assert response.status_code == 200
        yield test_client
