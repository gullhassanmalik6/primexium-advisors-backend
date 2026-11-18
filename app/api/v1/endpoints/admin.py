from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.core.file_storage import content_type_for_key, is_remote_url, resolve_path
from app.core.security import hash_password
from app.database.session import get_db
from app.models.lead import Lead, LeadStatus, LeadType
from app.models.student import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    Appointment,
    AppointmentStatus,
    Document,
    DocumentStatus,
    FollowUp,
    FollowUpMethod,
    FollowUpStatus,
    Message,
    MessageStatus,
    Payment,
    PaymentStatus,
)
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminDashboardStats,
    AdminMessageCreate,
    ApplicationStatusUpdate,
    ApplicationWithStudent,
    AppointmentStatusUpdate,
    AppointmentWithStudent,
    DocumentStatusUpdate,
    DocumentWithStudent,
    EmployeeCreate,
    EmployeeUpdate,
    MessageWithStudent,
    PaymentCreate,
    PaymentStatusUpdate,
    PaymentWithStudent,
    ReportSummary,
    StudentDetailResponse,
    StudentListItem,
    StudentStatusUpdate,
)
from app.schemas.lead import LeadResponse
from app.schemas.auth import UserResponse
from app.schemas.student import (
    ApplicationHistoryResponse,
    ApplicationResponse,
    AppointmentResponse,
    DocumentResponse,
    FollowUpCreate,
    FollowUpResponse,
    FollowUpUpdate,
    MessageResponse,
    PaymentResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])

STAFF_ROLES = (
    UserRole.ADMIN,
    UserRole.COUNSELLOR,
    UserRole.DOCUMENTATION_OFFICER,
    UserRole.FINANCE,
    UserRole.MARKETING,
)

staff_required = require_roles(*STAFF_ROLES)
admin_required = require_roles(UserRole.ADMIN)


def _student_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def _get_student(db: Session, student_id: UUID) -> User:
    student = db.get(User, student_id)
    if student is None or student.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.get("/dashboard", response_model=AdminDashboardStats)
def dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> AdminDashboardStats:
    return AdminDashboardStats(
        leads_new=db.scalar(select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.NEW)) or 0,
        leads_total=db.scalar(select(func.count()).select_from(Lead)) or 0,
        students_total=db.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.STUDENT)
        )
        or 0,
        applications_total=db.scalar(select(func.count()).select_from(Application)) or 0,
        applications_active=db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.status.notin_(
                    [ApplicationStatus.COMPLETED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]
                )
            )
        )
        or 0,
        documents_pending=db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.status.in_([DocumentStatus.PENDING, DocumentStatus.UNDER_REVIEW, DocumentStatus.UPLOADED]))
        )
        or 0,
        payments_pending=db.scalar(
            select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PENDING)
        )
        or 0,
        appointments_requested=db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.status == AppointmentStatus.REQUESTED)
        )
        or 0,
        messages_unread_from_students=db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.is_from_student.is_(True), Message.status == MessageStatus.UNREAD)
        )
        or 0,
    )


@router.get("/reports/summary", response_model=ReportSummary)
def report_summary(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> ReportSummary:
    leads_by_type = {
        row[0].value: row[1]
        for row in db.execute(select(Lead.lead_type, func.count()).group_by(Lead.lead_type)).all()
    }
    leads_by_status = {
        row[0].value: row[1]
        for row in db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all()
    }
    applications_by_status = {
        row[0].value: row[1]
        for row in db.execute(select(Application.status, func.count()).group_by(Application.status)).all()
    }
    payments_by_status = {
        row[0].value: row[1]
        for row in db.execute(select(Payment.status, func.count()).group_by(Payment.status)).all()
    }
    return ReportSummary(
        generated_at=datetime.now(UTC),
        leads_by_type=leads_by_type,
        leads_by_status=leads_by_status,
        applications_by_status=applications_by_status,
        payments_by_status=payments_by_status,
        students_active=db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.STUDENT, User.is_active.is_(True))
        )
        or 0,
        students_inactive=db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.STUDENT, User.is_active.is_(False))
        )
        or 0,
    )


@router.get("/students", response_model=list[StudentListItem])
def list_students(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[StudentListItem]:
    students = list(
        db.scalars(select(User).where(User.role == UserRole.STUDENT).order_by(User.created_at.desc())).all()
    )
    items: list[StudentListItem] = []
    for student in students:
        count = (
            db.scalar(
                select(func.count()).select_from(Application).where(Application.student_id == student.id)
            )
            or 0
        )
        item = StudentListItem.model_validate(student)
        item.applications_count = count
        items.append(item)
    return items


@router.get("/students/{student_id}", response_model=StudentDetailResponse)
def get_student_detail(
    student_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> StudentDetailResponse:
    student = _get_student(db, student_id)
    applications_count = (
        db.scalar(select(func.count()).select_from(Application).where(Application.student_id == student.id))
        or 0
    )
    item = StudentListItem.model_validate(student)
    item.applications_count = applications_count

    applications = list(
        db.scalars(
            select(Application)
            .where(Application.student_id == student.id)
            .order_by(Application.created_at.desc())
        ).all()
    )
    documents = list(
        db.scalars(
            select(Document).where(Document.student_id == student.id).order_by(Document.created_at.desc())
        ).all()
    )
    payments = list(
        db.scalars(
            select(Payment).where(Payment.student_id == student.id).order_by(Payment.created_at.desc())
        ).all()
    )
    appointments = list(
        db.scalars(
            select(Appointment)
            .where(Appointment.student_id == student.id)
            .order_by(Appointment.preferred_date.desc())
        ).all()
    )
    messages = list(
        db.scalars(
            select(Message).where(Message.student_id == student.id).order_by(Message.created_at.desc()).limit(50)
        ).all()
    )

    return StudentDetailResponse(
        student=item,
        applications=applications,
        documents=documents,
        payments=payments,
        appointments=appointments,
        messages=messages,
    )


@router.get("/crm/overview")
def crm_overview(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> dict:
    stats = AdminDashboardStats(
        leads_new=db.scalar(select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.NEW)) or 0,
        leads_total=db.scalar(select(func.count()).select_from(Lead)) or 0,
        students_total=db.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.STUDENT)
        )
        or 0,
        applications_total=db.scalar(select(func.count()).select_from(Application)) or 0,
        applications_active=db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.status.notin_(
                    [ApplicationStatus.COMPLETED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]
                )
            )
        )
        or 0,
        documents_pending=db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.status.in_([DocumentStatus.PENDING, DocumentStatus.UNDER_REVIEW, DocumentStatus.UPLOADED]))
        )
        or 0,
        payments_pending=db.scalar(
            select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PENDING)
        )
        or 0,
        appointments_requested=db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.status == AppointmentStatus.REQUESTED)
        )
        or 0,
        messages_unread_from_students=db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.is_from_student.is_(True), Message.status == MessageStatus.UNREAD)
        )
        or 0,
    )
    recent_leads = list(db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(8)).all())
    leads_by_status = {
        row[0].value: row[1]
        for row in db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all()
    }
    return {
        "stats": stats,
        "recent_leads": [LeadResponse.model_validate(lead) for lead in recent_leads],
        "leads_by_status": leads_by_status,
    }


@router.patch("/students/{student_id}", response_model=UserResponse)
def update_student_status(
    student_id: UUID,
    payload: StudentStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> User:
    student = _get_student(db, student_id)
    student.is_active = payload.is_active
    db.commit()
    db.refresh(student)
    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
) -> None:
    """Permanently delete a student account and cascaded portal records."""
    student = _get_student(db, student_id)
    db.delete(student)
    db.commit()


@router.get("/applications", response_model=list[ApplicationWithStudent])
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[ApplicationWithStudent]:
    rows = db.execute(
        select(Application, User)
        .join(User, User.id == Application.student_id)
        .order_by(Application.created_at.desc())
    ).all()
    results: list[ApplicationWithStudent] = []
    for application, student in rows:
        data = ApplicationResponse.model_validate(application).model_dump()
        results.append(
            ApplicationWithStudent(
                **data,
                student_email=student.email,
                student_name=_student_name(student),
            )
        )
    return results


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_required),
) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    previous_status = application.status.value if application.status else None
    status_changed = application.status != payload.status
    application.status = payload.status
    if payload.notes is not None:
        application.notes = payload.notes
    if payload.student_note is not None:
        application.student_note = payload.student_note
    if payload.next_action is not None:
        application.next_action = payload.next_action
    if payload.next_action_due is not None:
        application.next_action_due = payload.next_action_due
    if payload.missing_documents is not None:
        application.missing_documents = payload.missing_documents
    if status_changed:
        application.stage_completed_at = datetime.now(UTC)
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                from_status=previous_status,
                to_status=payload.status.value,
                changed_by_id=current_user.id,
                student_safe_note=payload.student_note,
                internal_note=payload.notes,
                next_action=payload.next_action,
                next_action_due=payload.next_action_due,
            )
        )

    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications/{application_id}/history", response_model=list[ApplicationHistoryResponse])
def application_history(
    application_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[ApplicationHistoryResponse]:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    rows = list(
        db.scalars(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == application_id)
            .order_by(ApplicationStatusHistory.created_at.desc())
        ).all()
    )
    results: list[ApplicationHistoryResponse] = []
    for row in rows:
        staff_name = None
        if row.changed_by_id:
            staff = db.get(User, row.changed_by_id)
            if staff:
                staff_name = f"{staff.first_name} {staff.last_name}".strip()
        item = ApplicationHistoryResponse.model_validate(row)
        item.changed_by_name = staff_name
        results.append(item)
    return results


@router.get("/follow-ups", response_model=list[FollowUpResponse])
def list_follow_ups(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
    overdue_only: bool = Query(default=False),
) -> list[FollowUpResponse]:
    query = select(FollowUp).order_by(FollowUp.follow_up_date.asc())
    rows = list(db.scalars(query).all())
    today = datetime.now(UTC).date()
    results: list[FollowUpResponse] = []
    for row in rows:
        if overdue_only and not (
            row.status == FollowUpStatus.PENDING and row.follow_up_date < today
        ):
            continue
        student = db.get(User, row.student_id)
        item = FollowUpResponse(
            id=row.id,
            student_id=row.student_id,
            application_id=row.application_id,
            staff_id=row.staff_id,
            follow_up_date=row.follow_up_date,
            method=row.method.value if hasattr(row.method, "value") else str(row.method),
            summary=row.summary,
            next_action=row.next_action,
            next_follow_up_date=row.next_follow_up_date,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            visible_to_student=row.visible_to_student,
            student_message=row.student_message,
            related_status=row.related_status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            student_name=_student_name(student) if student else None,
            student_email=student.email if student else None,
        )
        results.append(item)
    return results


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_required),
) -> FollowUpResponse:
    student = _get_student(db, payload.student_id)
    try:
        method = FollowUpMethod(payload.method)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid follow-up method") from exc

    follow_up = FollowUp(
        student_id=student.id,
        application_id=payload.application_id,
        staff_id=current_user.id,
        follow_up_date=payload.follow_up_date,
        method=method,
        summary=payload.summary.strip(),
        next_action=payload.next_action,
        next_follow_up_date=payload.next_follow_up_date,
        visible_to_student=payload.visible_to_student,
        student_message=payload.student_message if payload.visible_to_student else None,
        related_status=payload.related_status,
        status=FollowUpStatus.PENDING,
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return FollowUpResponse(
        id=follow_up.id,
        student_id=follow_up.student_id,
        application_id=follow_up.application_id,
        staff_id=follow_up.staff_id,
        follow_up_date=follow_up.follow_up_date,
        method=follow_up.method.value,
        summary=follow_up.summary,
        next_action=follow_up.next_action,
        next_follow_up_date=follow_up.next_follow_up_date,
        status=follow_up.status.value,
        visible_to_student=follow_up.visible_to_student,
        student_message=follow_up.student_message,
        related_status=follow_up.related_status,
        created_at=follow_up.created_at,
        updated_at=follow_up.updated_at,
        student_name=_student_name(student),
        student_email=student.email,
    )


@router.patch("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    follow_up_id: UUID,
    payload: FollowUpUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> FollowUpResponse:
    follow_up = db.get(FollowUp, follow_up_id)
    if follow_up is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    if payload.status is not None:
        try:
            follow_up.status = FollowUpStatus(payload.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid follow-up status") from exc
    if payload.summary is not None:
        follow_up.summary = payload.summary
    if payload.next_action is not None:
        follow_up.next_action = payload.next_action
    if payload.next_follow_up_date is not None:
        follow_up.next_follow_up_date = payload.next_follow_up_date
    if payload.visible_to_student is not None:
        follow_up.visible_to_student = payload.visible_to_student
    if payload.student_message is not None:
        follow_up.student_message = payload.student_message
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    student = db.get(User, follow_up.student_id)
    return FollowUpResponse(
        id=follow_up.id,
        student_id=follow_up.student_id,
        application_id=follow_up.application_id,
        staff_id=follow_up.staff_id,
        follow_up_date=follow_up.follow_up_date,
        method=follow_up.method.value,
        summary=follow_up.summary,
        next_action=follow_up.next_action,
        next_follow_up_date=follow_up.next_follow_up_date,
        status=follow_up.status.value,
        visible_to_student=follow_up.visible_to_student,
        student_message=follow_up.student_message,
        related_status=follow_up.related_status,
        created_at=follow_up.created_at,
        updated_at=follow_up.updated_at,
        student_name=_student_name(student) if student else None,
        student_email=student.email if student else None,
    )


@router.get("/documents", response_model=list[DocumentWithStudent])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[DocumentWithStudent]:
    rows = db.execute(
        select(Document, User).join(User, User.id == Document.student_id).order_by(Document.created_at.desc())
    ).all()
    results: list[DocumentWithStudent] = []
    for document, student in rows:
        data = DocumentResponse.model_validate(document).model_dump()
        results.append(
            DocumentWithStudent(
                **data,
                student_email=student.email,
                student_name=_student_name(student),
            )
        )
    return results


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: UUID,
    payload: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.status = payload.status
    if payload.notes is not None:
        document.notes = payload.notes
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents/{document_id}/file")
def download_admin_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None or not document.file_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")
    if is_remote_url(document.file_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document is an external URL; open file_url directly",
        )
    path = resolve_path(document.file_url)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file missing on server")
    return FileResponse(
        path,
        media_type=content_type_for_key(document.file_url),
        filename=path.name,
    )


@router.get("/payments", response_model=list[PaymentWithStudent])
def list_payments(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[PaymentWithStudent]:
    rows = db.execute(
        select(Payment, User).join(User, User.id == Payment.student_id).order_by(Payment.created_at.desc())
    ).all()
    results: list[PaymentWithStudent] = []
    for payment, student in rows:
        data = PaymentResponse.model_validate(payment).model_dump()
        results.append(
            PaymentWithStudent(
                **data,
                student_email=student.email,
                student_name=_student_name(student),
            )
        )
    return results


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> Payment:
    _get_student(db, payload.student_id)
    if payload.application_id is not None:
        application = db.get(Application, payload.application_id)
        if application is None or application.student_id != payload.student_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application")
    payment = Payment(
        student_id=payload.student_id,
        application_id=payload.application_id,
        title=payload.title.strip(),
        amount=payload.amount,
        currency=payload.currency.strip().upper(),
        due_date=payload.due_date,
        notes=payload.notes.strip() if payload.notes else None,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/payments/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: UUID,
    payload: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    payment.status = payload.status
    if payload.status == PaymentStatus.PAID and payment.paid_at is None:
        payment.paid_at = datetime.now(UTC)
    if payload.notes is not None:
        payment.notes = payload.notes
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/appointments", response_model=list[AppointmentWithStudent])
def list_appointments(
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[AppointmentWithStudent]:
    rows = db.execute(
        select(Appointment, User)
        .join(User, User.id == Appointment.student_id)
        .order_by(Appointment.preferred_date.desc())
    ).all()
    results: list[AppointmentWithStudent] = []
    for appointment, student in rows:
        data = AppointmentResponse.model_validate(appointment).model_dump()
        results.append(
            AppointmentWithStudent(
                **data,
                student_email=student.email,
                student_name=_student_name(student),
            )
        )
    return results


@router.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    appointment.status = payload.status
    if payload.notes is not None:
        appointment.notes = payload.notes
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/messages", response_model=list[MessageWithStudent])
def list_messages(
    student_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[MessageWithStudent]:
    query = select(Message, User).join(User, User.id == Message.student_id)
    if student_id is not None:
        query = query.where(Message.student_id == student_id)
    rows = db.execute(query.order_by(Message.created_at.desc())).all()
    results: list[MessageWithStudent] = []
    for message, student in rows:
        data = MessageResponse.model_validate(message).model_dump()
        results.append(
            MessageWithStudent(
                **data,
                student_email=student.email,
                student_name=_student_name(student),
            )
        )
    return results


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: AdminMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_required),
) -> Message:
    _get_student(db, payload.student_id)
    message = Message(
        student_id=payload.student_id,
        sender_id=current_user.id,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
        status=MessageStatus.UNREAD,
        is_from_student=False,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/messages/{message_id}/read", response_model=MessageResponse)
def mark_student_message_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> Message:
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if message.is_from_student:
        message.status = MessageStatus.READ
        db.commit()
        db.refresh(message)
    return message


@router.get("/employees", response_model=list[UserResponse])
def list_employees(
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.role != UserRole.STUDENT).order_by(User.created_at.desc())
        ).all()
    )


@router.post("/employees", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_required),
) -> User:
    if payload.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use student registration for student accounts",
        )
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/employees/{employee_id}", response_model=UserResponse)
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
) -> User:
    employee = db.get(User, employee_id)
    if employee is None or employee.role == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if employee.id == current_user.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    data = payload.model_dump(exclude_unset=True)
    if data.get("role") == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid employee role")
    for key, value in data.items():
        setattr(employee, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(employee)
    return employee
