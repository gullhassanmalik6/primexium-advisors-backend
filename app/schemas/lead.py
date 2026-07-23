from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.lead import LeadStatus, LeadType


class ContactLeadCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    subject: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=5, max_length=5000)


class ConsultationLeadCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    preferred_country: str | None = Field(default=None, max_length=100)
    preferred_degree: str | None = Field(default=None, max_length=100)
    preferred_intake: str | None = Field(default=None, max_length=50)
    message: str | None = Field(default=None, max_length=5000)


class EligibilityLeadCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    preferred_country: str | None = Field(default=None, max_length=100)
    preferred_degree: str | None = Field(default=None, max_length=100)
    preferred_intake: str | None = Field(default=None, max_length=50)
    eligibility_score: int = Field(ge=0, le=100)
    eligibility_tier: str = Field(min_length=2, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)


class LeadResponse(BaseModel):
    id: UUID
    lead_type: LeadType
    status: LeadStatus
    full_name: str
    email: EmailStr
    phone: str | None
    subject: str | None
    message: str | None
    preferred_country: str | None
    preferred_degree: str | None
    preferred_intake: str | None
    eligibility_score: int | None
    eligibility_tier: str | None
    payload: dict[str, Any] | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int


class LeadStatusUpdate(BaseModel):
    status: LeadStatus
    notes: str | None = None


class LeadCreateResponse(BaseModel):
    id: UUID
    message: str
