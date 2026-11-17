"""Company consultancy ledger — income, expenses, savings, investments."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class FinanceEntryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    SAVING = "saving"
    INVESTMENT = "investment"


class FinanceCategory(str, enum.Enum):
    # Income
    CLIENT_FEE = "client_fee"
    PARTNER_PAYOUT = "partner_payout"
    OTHER_INCOME = "other_income"
    # Expenses / operations
    TRANSPORT = "transport"
    SUBSCRIPTION = "subscription"
    DOMAIN = "domain"
    MARKETING = "marketing"
    OFFICE_RENT = "office_rent"
    OFFICE_SUPPLIES = "office_supplies"
    UTILITIES = "utilities"
    SALARY = "salary"
    SOFTWARE = "software"
    # Savings / investment
    RESERVE = "reserve"
    EQUIPMENT = "equipment"
    OTHER = "other"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK = "bank"
    JAZZCASH = "jazzcash"
    EASYPAISA = "easypaisa"
    CARD = "card"
    OTHER = "other"


class FinanceEntry(Base):
    __tablename__ = "finance_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    type: Mapped[FinanceEntryType] = mapped_column(
        Enum(
            FinanceEntryType,
            name="financeentrytype",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    category: Mapped[FinanceCategory] = mapped_column(
        Enum(
            FinanceCategory,
            name="financecategory",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="PKR")
    paid_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paid_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            name="financepaymentmethod",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=PaymentMethod.CASH,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
