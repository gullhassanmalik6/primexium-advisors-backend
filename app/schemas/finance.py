from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.finance import FinanceCategory, FinanceEntryType, PaymentMethod


class FinanceEntryCreate(BaseModel):
    entry_date: date
    type: FinanceEntryType
    category: FinanceCategory
    title: str = Field(min_length=2, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="PKR", max_length=10)
    paid_by_name: str | None = Field(default=None, max_length=120)
    paid_by_user_id: UUID | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = Field(default=None, max_length=5000)
    attachment_url: str | None = Field(default=None, max_length=500)

    @field_validator("title", mode="before")
    @classmethod
    def require_title(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("Title is required")
            return cleaned
        return value

    @field_validator("paid_by_name", "notes", "currency", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class FinanceEntryUpdate(BaseModel):
    entry_date: date | None = None
    type: FinanceEntryType | None = None
    category: FinanceCategory | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=10)
    paid_by_name: str | None = Field(default=None, max_length=120)
    paid_by_user_id: UUID | None = None
    payment_method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=5000)
    attachment_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("title", "paid_by_name", "notes", "currency", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class FinanceEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entry_date: date
    type: FinanceEntryType
    category: FinanceCategory
    title: str
    amount: Decimal
    currency: str
    paid_by_name: str | None
    paid_by_user_id: UUID | None
    payment_method: PaymentMethod
    notes: str | None
    attachment_url: str | None
    is_active: bool
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    created_by_name: str | None = None


class FinanceBreakdownItem(BaseModel):
    key: str
    label: str
    amount: Decimal
    count: int


class FinanceSummaryResponse(BaseModel):
    currency: str = "PKR"
    date_from: date | None = None
    date_to: date | None = None
    total_income: Decimal
    total_expense: Decimal
    total_saving: Decimal
    total_investment: Decimal
    net_profit_loss: Decimal
    remaining_available: Decimal
    student_fees_paid_reference: Decimal
    by_category: list[FinanceBreakdownItem]
    by_member: list[FinanceBreakdownItem]
    by_month: list[FinanceBreakdownItem]
    entry_count: int
