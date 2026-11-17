"""Unit tests for finance schemas (no database required)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.finance import FinanceCategory, FinanceEntryType, PaymentMethod
from app.schemas.finance import FinanceEntryCreate


def test_finance_entry_create_valid():
    entry = FinanceEntryCreate(
        entry_date=date.today(),
        type=FinanceEntryType.EXPENSE,
        category=FinanceCategory.TRANSPORT,
        title="Sania pick and drop",
        amount=Decimal("2500"),
        payment_method=PaymentMethod.CASH,
        paid_by_name="Sania",
    )
    assert entry.title == "Sania pick and drop"
    assert entry.amount == Decimal("2500")


def test_finance_entry_rejects_blank_title():
    with pytest.raises(ValidationError):
        FinanceEntryCreate(
            entry_date=date.today(),
            type=FinanceEntryType.EXPENSE,
            category=FinanceCategory.DOMAIN,
            title="   ",
            amount=Decimal("1000"),
        )


def test_finance_entry_rejects_zero_amount():
    with pytest.raises(ValidationError):
        FinanceEntryCreate(
            entry_date=date.today(),
            type=FinanceEntryType.INCOME,
            category=FinanceCategory.CLIENT_FEE,
            title="Client fee",
            amount=Decimal("0"),
        )
