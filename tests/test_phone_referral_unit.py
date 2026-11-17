"""Unit tests that do not require PostgreSQL."""

from app.core.phone import is_valid_phone, normalize_phone, sanitize_text
from app.core.referral import REFERRAL_SOURCES
from app.schemas.auth import UserCreate
import pytest
from pydantic import ValidationError


def test_normalize_phone_international():
    assert normalize_phone("+92 300 1112233") == "+923001112233"
    assert normalize_phone("+923001112233") == "+923001112233"


def test_normalize_phone_rejects_short():
    assert normalize_phone("123") is None
    assert normalize_phone("   ") is None
    assert normalize_phone(None) is None


def test_is_valid_phone():
    assert is_valid_phone("+923001112233") is True
    assert is_valid_phone("abc") is False
    assert is_valid_phone(None) is True
    assert is_valid_phone(None, required=True) is False


def test_sanitize_text():
    assert sanitize_text("  hello   world  ") == "hello world"
    assert sanitize_text("   ") is None


def test_referral_sources_cover_registration_options():
    expected = {
        "facebook",
        "instagram",
        "tiktok",
        "youtube",
        "google_search",
        "friend_or_family",
        "existing_student",
        "educational_agent",
        "walk_in",
        "other",
    }
    assert expected.issubset(REFERRAL_SOURCES)


def test_user_create_strips_names_and_normalises_email():
    user = UserCreate(
        email="  Student@Example.COM ",
        password="password123",
        first_name="  Ali  ",
        last_name=" Khan ",
        referral_source="instagram",
    )
    assert user.email == "student@example.com"
    assert user.first_name == "Ali"
    assert user.last_name == "Khan"
    assert user.referral_source == "instagram"


def test_user_create_rejects_whitespace_name():
    with pytest.raises(ValidationError):
        UserCreate(
            email="x@example.com",
            password="password123",
            first_name="   ",
            last_name="Khan",
        )


def test_user_create_rejects_invalid_referral():
    with pytest.raises(ValidationError):
        UserCreate(
            email="x@example.com",
            password="password123",
            first_name="Ali",
            last_name="Khan",
            referral_source="newspaper",
        )
