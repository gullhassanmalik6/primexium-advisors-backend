from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.core.file_storage import (
    content_type_for_key,
    delete_upload,
    is_remote_url,
    resolve_path,
    upload_document,
)
from app.database.session import get_db
from app.models.finance import FinanceCategory, FinanceEntry, FinanceEntryType, PaymentMethod
from app.models.student import Payment, PaymentStatus
from app.models.user import User, UserRole
from app.schemas.finance import (
    FinanceBreakdownItem,
    FinanceEntryCreate,
    FinanceEntryResponse,
    FinanceEntryUpdate,
    FinanceSummaryResponse,
)

router = APIRouter(prefix="/admin/finance", tags=["finance"])

STAFF_ROLES = (
    UserRole.ADMIN,
    UserRole.COUNSELLOR,
    UserRole.DOCUMENTATION_OFFICER,
    UserRole.FINANCE,
    UserRole.MARKETING,
)

staff_required = require_roles(*STAFF_ROLES)
finance_write_required = require_roles(UserRole.ADMIN, UserRole.FINANCE)

ZERO = Decimal("0.00")


def _staff_name(user: User | None) -> str | None:
    if user is None:
        return None
    return f"{user.first_name} {user.last_name}".strip()


def _to_response(entry: FinanceEntry, db: Session) -> FinanceEntryResponse:
    created_by = db.get(User, entry.created_by_id) if entry.created_by_id else None
    data = FinanceEntryResponse.model_validate(entry)
    data.created_by_name = _staff_name(created_by)
    return data


def _filtered_query(
    *,
    date_from: date | None,
    date_to: date | None,
    entry_type: FinanceEntryType | None,
    category: str | None,
    paid_by: str | None,
    active_only: bool = True,
):
    query = select(FinanceEntry)
    if active_only:
        query = query.where(FinanceEntry.is_active.is_(True))
    if date_from is not None:
        query = query.where(FinanceEntry.entry_date >= date_from)
    if date_to is not None:
        query = query.where(FinanceEntry.entry_date <= date_to)
    if entry_type is not None:
        query = query.where(FinanceEntry.type == entry_type)
    if category:
        try:
            query = query.where(FinanceEntry.category == FinanceCategory(category))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid finance category",
            ) from exc
    if paid_by:
        query = query.where(FinanceEntry.paid_by_name.ilike(f"%{paid_by.strip()}%"))
    return query


@router.get("/summary", response_model=FinanceSummaryResponse)
def finance_summary(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> FinanceSummaryResponse:
    rows = list(
        db.scalars(
            _filtered_query(
                date_from=date_from,
                date_to=date_to,
                entry_type=None,
                category=None,
                paid_by=None,
            ).order_by(FinanceEntry.entry_date.desc())
        ).all()
    )

    totals = {
        FinanceEntryType.INCOME: ZERO,
        FinanceEntryType.EXPENSE: ZERO,
        FinanceEntryType.SAVING: ZERO,
        FinanceEntryType.INVESTMENT: ZERO,
    }
    by_category: dict[str, list] = defaultdict(lambda: [ZERO, 0])
    by_member: dict[str, list] = defaultdict(lambda: [ZERO, 0])
    by_month: dict[str, list] = defaultdict(lambda: [ZERO, 0])

    for row in rows:
        amount = Decimal(row.amount)
        totals[row.type] += amount
        cat_key = row.category.value if hasattr(row.category, "value") else str(row.category)
        by_category[cat_key][0] += amount
        by_category[cat_key][1] += 1
        member = (row.paid_by_name or "Unassigned").strip() or "Unassigned"
        by_member[member][0] += amount
        by_member[member][1] += 1
        month_key = row.entry_date.strftime("%Y-%m")
        # Month net contribution: income positive, others negative for overview
        signed = amount if row.type == FinanceEntryType.INCOME else -amount
        by_month[month_key][0] += signed
        by_month[month_key][1] += 1

    income = totals[FinanceEntryType.INCOME]
    expense = totals[FinanceEntryType.EXPENSE]
    saving = totals[FinanceEntryType.SAVING]
    investment = totals[FinanceEntryType.INVESTMENT]
    net_profit_loss = income - expense - investment
    remaining = income - expense - saving - investment

    student_fees_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == PaymentStatus.PAID
    )
    if date_from is not None:
        student_fees_query = student_fees_query.where(func.date(Payment.paid_at) >= date_from)
    if date_to is not None:
        student_fees_query = student_fees_query.where(func.date(Payment.paid_at) <= date_to)
    student_fees = Decimal(str(db.scalar(student_fees_query) or 0))

    return FinanceSummaryResponse(
        date_from=date_from,
        date_to=date_to,
        total_income=income,
        total_expense=expense,
        total_saving=saving,
        total_investment=investment,
        net_profit_loss=net_profit_loss,
        remaining_available=remaining,
        student_fees_paid_reference=student_fees,
        by_category=[
            FinanceBreakdownItem(
                key=key,
                label=key.replace("_", " ").title(),
                amount=values[0],
                count=values[1],
            )
            for key, values in sorted(by_category.items(), key=lambda item: item[1][0], reverse=True)
        ],
        by_member=[
            FinanceBreakdownItem(
                key=key,
                label=key,
                amount=values[0],
                count=values[1],
            )
            for key, values in sorted(by_member.items(), key=lambda item: item[1][0], reverse=True)
        ],
        by_month=[
            FinanceBreakdownItem(
                key=key,
                label=key,
                amount=values[0],
                count=values[1],
            )
            for key, values in sorted(by_month.items(), reverse=True)
        ],
        entry_count=len(rows),
    )


@router.get("/entries", response_model=list[FinanceEntryResponse])
def list_finance_entries(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    entry_type: FinanceEntryType | None = Query(default=None, alias="type"),
    category: str | None = None,
    paid_by: str | None = None,
) -> list[FinanceEntryResponse]:
    rows = list(
        db.scalars(
            _filtered_query(
                date_from=date_from,
                date_to=date_to,
                entry_type=entry_type,
                category=category,
                paid_by=paid_by,
            ).order_by(FinanceEntry.entry_date.desc(), FinanceEntry.created_at.desc())
        ).all()
    )
    return [_to_response(row, db) for row in rows]


@router.post("/entries", response_model=FinanceEntryResponse, status_code=status.HTTP_201_CREATED)
def create_finance_entry(
    payload: FinanceEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(finance_write_required),
) -> FinanceEntryResponse:
    entry = FinanceEntry(
        entry_date=payload.entry_date,
        type=payload.type,
        category=payload.category,
        title=payload.title,
        amount=payload.amount,
        currency=(payload.currency or "PKR").upper(),
        paid_by_name=payload.paid_by_name,
        paid_by_user_id=payload.paid_by_user_id,
        payment_method=payload.payment_method,
        notes=payload.notes,
        attachment_url=payload.attachment_url,
        created_by_id=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, db)


@router.post("/entries/upload", response_model=FinanceEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_finance_entry_with_receipt(
    entry_date: date = Form(...),
    type: FinanceEntryType = Form(...),
    category: FinanceCategory = Form(...),
    title: str = Form(..., min_length=2, max_length=255),
    amount: Decimal = Form(..., gt=0),
    currency: str = Form(default="PKR"),
    paid_by_name: str | None = Form(default=None),
    payment_method: PaymentMethod = Form(default=PaymentMethod.CASH),
    notes: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(finance_write_required),
) -> FinanceEntryResponse:
    cleaned_title = title.strip()
    if not cleaned_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")

    attachment_url: str | None = None
    if file is not None and file.filename:
        attachment_url = upload_document(
            file.file,
            filename=file.filename,
            content_type=file.content_type,
            folder=f"finance/{current_user.id}",
        )

    entry = FinanceEntry(
        entry_date=entry_date,
        type=type,
        category=category,
        title=cleaned_title,
        amount=amount,
        currency=(currency or "PKR").strip().upper() or "PKR",
        paid_by_name=paid_by_name.strip() if paid_by_name and paid_by_name.strip() else None,
        payment_method=payment_method,
        notes=notes.strip() if notes and notes.strip() else None,
        attachment_url=attachment_url,
        created_by_id=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, db)


@router.post("/entries/{entry_id}/attachment", response_model=FinanceEntryResponse)
async def upload_finance_attachment(
    entry_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(finance_write_required),
) -> FinanceEntryResponse:
    entry = db.get(FinanceEntry, entry_id)
    if entry is None or not entry.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance entry not found")
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A receipt file is required")

    previous = entry.attachment_url
    entry.attachment_url = upload_document(
        file.file,
        filename=file.filename,
        content_type=file.content_type,
        folder=f"finance/{current_user.id}",
    )
    delete_upload(previous)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, db)


@router.get("/entries/{entry_id}/file")
def download_finance_attachment(
    entry_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> FileResponse:
    entry = db.get(FinanceEntry, entry_id)
    if entry is None or not entry.is_active or not entry.attachment_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    if is_remote_url(entry.attachment_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This receipt is an external URL; open attachment_url directly",
        )
    path = resolve_path(entry.attachment_url)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt file missing on server")
    return FileResponse(
        path,
        media_type=content_type_for_key(entry.attachment_url),
        filename=path.name,
    )


@router.delete("/entries/{entry_id}/attachment", response_model=FinanceEntryResponse)
def remove_finance_attachment(
    entry_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(finance_write_required),
) -> FinanceEntryResponse:
    entry = db.get(FinanceEntry, entry_id)
    if entry is None or not entry.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance entry not found")
    delete_upload(entry.attachment_url)
    entry.attachment_url = None
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, db)


@router.patch("/entries/{entry_id}", response_model=FinanceEntryResponse)
def update_finance_entry(
    entry_id: UUID,
    payload: FinanceEntryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(finance_write_required),
) -> FinanceEntryResponse:
    entry = db.get(FinanceEntry, entry_id)
    if entry is None or not entry.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance entry not found")

    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = str(data["currency"]).upper()
    for key, value in data.items():
        setattr(entry, key, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, db)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_finance_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(finance_write_required),
) -> Response:
    entry = db.get(FinanceEntry, entry_id)
    if entry is None or not entry.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance entry not found")
    entry.is_active = False
    db.add(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
