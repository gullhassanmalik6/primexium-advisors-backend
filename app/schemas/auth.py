from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import is_valid_phone, normalize_phone, sanitize_text
from app.core.referral import REFERRAL_SOURCES
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_required_name(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("This field is required")
            return cleaned
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if not is_valid_phone(cleaned):
                raise ValueError("Enter a valid international phone number")
            return cleaned
        return value


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    referral_source: str | None = Field(default=None, max_length=50)
    referral_detail: str | None = Field(default=None, max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("referral_source", mode="before")
    @classmethod
    def validate_referral_source(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
            if not cleaned or cleaned == "not_specified":
                return None
            if cleaned not in REFERRAL_SOURCES:
                raise ValueError("Invalid referral source")
            return cleaned
        return value

    @field_validator("referral_detail", mode="before")
    @classmethod
    def clean_referral_detail(cls, value: object) -> object:
        if isinstance(value, str):
            return sanitize_text(value, max_length=255)
        return value


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    is_active: bool
    avatar_url: str | None = None
    referral_source: str | None = None
    referral_detail: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=32)


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_url: str | None = None


class MessageResponse(BaseModel):
    message: str


# Re-export helper used by register endpoint
__all__ = [
    "UserBase",
    "UserCreate",
    "UserResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "DeleteAccountRequest",
    "ForgotPasswordResponse",
    "MessageResponse",
    "normalize_phone",
]
