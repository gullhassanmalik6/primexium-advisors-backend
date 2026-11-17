from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.student import (
    ApplicationStatus,
    AppointmentStatus,
    DocumentStatus,
    DocumentType,
    MessageStatus,
    PaymentStatus,
)


class ApplicationCreate(BaseModel):
    university_name: str = Field(min_length=2, max_length=255)
    country: str = Field(min_length=2, max_length=100)
    program_name: str = Field(min_length=2, max_length=255)
    degree_level: str = Field(min_length=2, max_length=50)
    intake: str = Field(min_length=2, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationUpdate(BaseModel):
    university_name: str | None = Field(default=None, min_length=2, max_length=255)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    program_name: str | None = Field(default=None, min_length=2, max_length=255)
    degree_level: str | None = Field(default=None, min_length=2, max_length=50)
    intake: str | None = Field(default=None, min_length=2, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)
    status: ApplicationStatus | None = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    university_name: str
    country: str
    program_name: str
    degree_level: str
    intake: str
    status: ApplicationStatus
    notes: str | None = None
    student_note: str | None = None
    next_action: str | None = None
    next_action_due: date | None = None
    missing_documents: str | None = None
    stage_completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    from_status: str | None
    to_status: str
    changed_by_id: UUID | None
    student_safe_note: str | None
    next_action: str | None
    next_action_due: date | None
    created_at: datetime
    changed_by_name: str | None = None


class StudentApplicationTrackingResponse(BaseModel):
    application: ApplicationResponse
    history: list[ApplicationHistoryResponse]
    visible_follow_ups: list["StudentFollowUpResponse"]


class StudentFollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    follow_up_date: date
    method: str
    student_message: str | None
    next_action: str | None
    next_follow_up_date: date | None
    related_status: str | None
    created_at: datetime


class FollowUpCreate(BaseModel):
    student_id: UUID
    application_id: UUID | None = None
    follow_up_date: date
    method: str = Field(default="phone", max_length=30)
    summary: str = Field(min_length=2, max_length=5000)
    next_action: str | None = Field(default=None, max_length=500)
    next_follow_up_date: date | None = None
    visible_to_student: bool = False
    student_message: str | None = Field(default=None, max_length=5000)
    related_status: str | None = Field(default=None, max_length=50)


class FollowUpUpdate(BaseModel):
    status: str | None = None
    summary: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=500)
    next_follow_up_date: date | None = None
    visible_to_student: bool | None = None
    student_message: str | None = Field(default=None, max_length=5000)


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    application_id: UUID | None
    staff_id: UUID | None
    follow_up_date: date
    method: str
    summary: str
    next_action: str | None
    next_follow_up_date: date | None
    status: str
    visible_to_student: bool
    student_message: str | None
    related_status: str | None
    created_at: datetime
    updated_at: datetime
    student_name: str | None = None
    student_email: str | None = None


class DocumentCreate(BaseModel):
    document_type: DocumentType
    title: str = Field(min_length=2, max_length=255)
    file_url: str | None = Field(default=None, max_length=500)
    application_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    application_id: UUID | None
    document_type: DocumentType
    title: str
    file_url: str | None
    status: DocumentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    application_id: UUID | None
    title: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    due_date: date | None
    paid_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AppointmentCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=255)
    preferred_date: date
    preferred_time: str = Field(min_length=1, max_length=50)
    meeting_mode: str = Field(default="online", max_length=50)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    topic: str
    preferred_date: date
    preferred_time: str
    meeting_mode: str
    status: AppointmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2, max_length=5000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    sender_id: UUID
    subject: str
    body: str
    status: MessageStatus
    is_from_student: bool
    created_at: datetime


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class DashboardStats(BaseModel):
    applications_total: int
    applications_active: int
    documents_total: int
    documents_pending: int
    payments_pending: int
    appointments_upcoming: int
    messages_unread: int


class ListResponse(BaseModel):
    items: list
    total: int
