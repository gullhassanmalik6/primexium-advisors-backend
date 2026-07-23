import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Prefer an explicit test DB. Never default to the app .env database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/primexium_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from app.database.session import get_db
from app.main import app
from app.models.content import ContentItem  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.student import Application, Appointment, Document, Message, Payment  # noqa: F401
from app.models.user import Base, User  # noqa: F401


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        engine.dispose()
        pytest.skip(f"PostgreSQL test database unavailable: {exc}")

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Isolate only the dedicated test database.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_login_me(client: TestClient):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "Student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com"


def test_refresh_token(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "password123",
            "first_name": "Refresh",
            "last_name": "User",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()


def test_forgot_and_reset_password(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reset@example.com",
            "password": "password123",
            "first_name": "Reset",
            "last_name": "User",
        },
    )
    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    reset_url = forgot.json().get("reset_url")
    assert reset_url
    token = reset_url.split("token=")[1]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "newpassword123"},
    )
    assert reset.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200


def test_content_crud_requires_staff(client: TestClient):
    assert client.get("/api/v1/content").status_code == 200
    assert client.get("/api/v1/content").json() == []

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "cms@example.com",
            "password": "password123",
            "first_name": "Cms",
            "last_name": "User",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cms@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    forbidden = client.post(
        "/api/v1/admin/content",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content_type": "blog",
            "slug": "hello",
            "title": "Hello",
            "summary": "World",
            "data": {},
            "is_published": True,
            "sort_order": 1,
        },
    )
    assert forbidden.status_code == 403
