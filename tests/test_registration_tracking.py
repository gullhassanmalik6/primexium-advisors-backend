"""Registration validation, duplicates, referral, and application tracking privacy."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/primexium_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from app.core.security import hash_password
from app.database.session import get_db
from app.main import app
from app.models.content import ContentItem  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.student import (  # noqa: F401
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    Appointment,
    Document,
    FollowUp,
    Message,
    Payment,
)
from app.models.user import Base, User, UserRole


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


def _login_token(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_register_rejects_blank_names(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blank@example.com",
            "password": "password123",
            "first_name": "   ",
            "last_name": "Student",
        },
    )
    assert response.status_code == 422


def test_register_rejects_invalid_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "first_name": "Test",
            "last_name": "Student",
        },
    )
    assert response.status_code == 422


def test_register_rejects_invalid_phone(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "phone@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "Student",
            "phone": "abc",
        },
    )
    assert response.status_code == 422


def test_duplicate_email_registration(client: TestClient):
    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "password123",
            "first_name": "One",
            "last_name": "Student",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUP@example.com",
            "password": "password456",
            "first_name": "Two",
            "last_name": "Student",
        },
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_duplicate_phone_registration(client: TestClient):
    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": "phone1@example.com",
            "password": "password123",
            "first_name": "One",
            "last_name": "Student",
            "phone": "+92 300 1112233",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": "phone2@example.com",
            "password": "password123",
            "first_name": "Two",
            "last_name": "Student",
            "phone": "+923001112233",
        },
    )
    assert second.status_code == 409
    assert "phone" in second.json()["detail"].lower()


def test_referral_other_requires_detail(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "referral@example.com",
            "password": "password123",
            "first_name": "Ref",
            "last_name": "Student",
            "referral_source": "other",
        },
    )
    assert response.status_code == 400


def test_referral_saved_on_register(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "instagram@example.com",
            "password": "password123",
            "first_name": "Insta",
            "last_name": "Student",
            "referral_source": "instagram",
            "referral_detail": "Promo reel",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["referral_source"] == "instagram"
    assert body["referral_detail"] == "Promo reel"


def test_student_cannot_view_other_application_tracking(client: TestClient):
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        student_a = User(
            email="a@example.com",
            hashed_password=hash_password("password123"),
            first_name="A",
            last_name="Student",
            role=UserRole.STUDENT,
        )
        student_b = User(
            email="b@example.com",
            hashed_password=hash_password("password123"),
            first_name="B",
            last_name="Student",
            role=UserRole.STUDENT,
        )
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        )
        db.add_all([student_a, student_b, admin])
        db.flush()
        application = Application(
            student_id=student_a.id,
            university_name="Test Uni",
            country="France",
            program_name="CS",
            degree_level="Masters",
            intake="Fall 2026",
            status=ApplicationStatus.INITIAL_ASSESSMENT,
            notes="INTERNAL SECRET NOTE",
            student_note="Please upload IELTS",
        )
        db.add(application)
        db.commit()
        app_id = str(application.id)
    finally:
        db.close()
        engine.dispose()

    token_b = _login_token(client, "b@example.com")
    forbidden = client.get(
        f"/api/v1/student/applications/{app_id}/tracking",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code in {403, 404}

    token_a = _login_token(client, "a@example.com")
    tracking = client.get(
        f"/api/v1/student/applications/{app_id}/tracking",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert tracking.status_code == 200
    payload = tracking.json()
    assert payload["application"]["notes"] is None
    assert payload["application"]["student_note"] == "Please upload IELTS"


def test_staff_status_update_records_history(client: TestClient):
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        student = User(
            email="track@example.com",
            hashed_password=hash_password("password123"),
            first_name="Track",
            last_name="Student",
            role=UserRole.STUDENT,
        )
        admin = User(
            email="staff@example.com",
            hashed_password=hash_password("password123"),
            first_name="Staff",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        db.add_all([student, admin])
        db.flush()
        application = Application(
            student_id=student.id,
            university_name="Sorbonne",
            country="France",
            program_name="MBA",
            degree_level="Masters",
            intake="Fall 2026",
            status=ApplicationStatus.REGISTRATION_RECEIVED,
        )
        db.add(application)
        db.commit()
        app_id = str(application.id)
    finally:
        db.close()
        engine.dispose()

    token = _login_token(client, "staff@example.com")
    update = client.patch(
        f"/api/v1/admin/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "status": "documents_pending",
            "notes": "Waiting on passport scan",
            "student_note": "Please upload your passport",
            "next_action": "Upload passport",
            "missing_documents": "Passport",
        },
    )
    assert update.status_code == 200
    assert update.json()["status"] == "documents_pending"
    assert update.json()["notes"] == "Waiting on passport scan"

    history = client.get(
        f"/api/v1/admin/applications/{app_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    assert len(history.json()) >= 1
    assert history.json()[0]["to_status"] == "documents_pending"

    student_token = _login_token(client, "track@example.com")
    tracking = client.get(
        f"/api/v1/student/applications/{app_id}/tracking",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert tracking.status_code == 200
    assert tracking.json()["application"]["notes"] is None
    assert tracking.json()["application"]["student_note"] == "Please upload your passport"


def test_follow_up_visibility(client: TestClient):
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        student = User(
            email="fu@example.com",
            hashed_password=hash_password("password123"),
            first_name="Follow",
            last_name="Up",
            role=UserRole.STUDENT,
        )
        admin = User(
            email="fu-admin@example.com",
            hashed_password=hash_password("password123"),
            first_name="Follow",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        db.add_all([student, admin])
        db.flush()
        application = Application(
            student_id=student.id,
            university_name="Test Uni",
            country="France",
            program_name="CS",
            degree_level="Bachelors",
            intake="Fall 2026",
            status=ApplicationStatus.INITIAL_ASSESSMENT,
        )
        db.add(application)
        db.commit()
        student_id = str(student.id)
        app_id = str(application.id)
    finally:
        db.close()
        engine.dispose()

    admin_token = _login_token(client, "fu-admin@example.com")
    create = client.post(
        "/api/v1/admin/follow-ups",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "student_id": student_id,
            "application_id": app_id,
            "follow_up_date": str(date.today() - timedelta(days=1)),
            "method": "whatsapp",
            "summary": "Internal call notes stay private",
            "next_action": "Send checklist",
            "visible_to_student": True,
            "student_message": "Please send your checklist documents",
        },
    )
    assert create.status_code == 201

    hidden = client.post(
        "/api/v1/admin/follow-ups",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "student_id": student_id,
            "application_id": app_id,
            "follow_up_date": str(date.today()),
            "method": "phone",
            "summary": "Private counsellor notes",
            "visible_to_student": False,
        },
    )
    assert hidden.status_code == 201

    student_token = _login_token(client, "fu@example.com")
    tracking = client.get(
        f"/api/v1/student/applications/{app_id}/tracking",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert tracking.status_code == 200
    messages = [item["student_message"] for item in tracking.json()["visible_follow_ups"]]
    assert "Please send your checklist documents" in messages
    assert all(item.get("summary") is None for item in tracking.json()["visible_follow_ups"])

    listed = client.get(
        "/api/v1/admin/follow-ups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) >= 2


def test_admin_can_delete_student_staff_cannot(client: TestClient):
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        student = User(
            email="deleteme@example.com",
            hashed_password=hash_password("password123"),
            first_name="Delete",
            last_name="Me",
            role=UserRole.STUDENT,
        )
        counsellor = User(
            email="counsellor@example.com",
            hashed_password=hash_password("password123"),
            first_name="Coun",
            last_name="Sellor",
            role=UserRole.COUNSELLOR,
        )
        admin = User(
            email="deleter@example.com",
            hashed_password=hash_password("password123"),
            first_name="Del",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        db.add_all([student, counsellor, admin])
        db.commit()
        student_id = str(student.id)
    finally:
        db.close()
        engine.dispose()

    counsellor_token = _login_token(client, "counsellor@example.com")
    forbidden = client.delete(
        f"/api/v1/admin/students/{student_id}",
        headers={"Authorization": f"Bearer {counsellor_token}"},
    )
    assert forbidden.status_code == 403

    admin_token = _login_token(client, "deleter@example.com")
    deleted = client.delete(
        f"/api/v1/admin/students/{student_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deleted.status_code == 204

    missing = client.get(
        f"/api/v1/admin/students/{student_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert missing.status_code == 404
