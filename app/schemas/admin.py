from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.student import (
    ApplicationStatus,
    AppointmentStatus,
    DocumentStatus,
    PaymentStatus,
)
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.schemas.student import (
    ApplicationResponse,
    AppointmentResponse,
    DocumentResponse,
    MessageResponse,
    PaymentResponse,
)


class AdminDashboardStats(BaseModel):
    leads_new: int
    leads_total: int
    students_total: int
    applications_total: int
    applications_active: int
    documents_pending: int
    payments_pending: int
    appointments_requested: int
    messages_unread_from_students: int


class StudentListItem(UserResponse):
    applications_count: int = 0


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: str | None = Field(default=None, max_length=5000)


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus
    notes: str | None = Field(default=None, max_length=2000)


class PaymentCreate(BaseModel):
    student_id: UUID
    application_id: UUID | None = None
    title: str = Field(min_length=2, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="PKR", max_length=10)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    notes: str | None = Field(default=None, max_length=2000)


class AdminMessageCreate(BaseModel):
    student_id: UUID
    subject: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2, max_length=5000)


class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    role: UserRole


class EmployeeUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class StudentStatusUpdate(BaseModel):
    is_active: bool


class ApplicationWithStudent(ApplicationResponse):
    student_email: str
    student_name: str


class DocumentWithStudent(DocumentResponse):
    student_email: str
    student_name: str


class PaymentWithStudent(PaymentResponse):
    student_email: str
    student_name: str


class AppointmentWithStudent(AppointmentResponse):
    student_email: str
    student_name: str


class MessageWithStudent(MessageResponse):
    student_email: str
    student_name: str


class ReportSummary(BaseModel):
    generated_at: datetime
    leads_by_type: dict[str, int]
    leads_by_status: dict[str, int]
    applications_by_status: dict[str, int]
    payments_by_status: dict[str, int]
    students_active: int
    students_inactive: int
