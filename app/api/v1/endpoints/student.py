from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.core.cloudinary_service import upload_document
from app.database.session import get_db
from app.models.student import (
    Application,
    ApplicationStatus,
    Appointment,
    AppointmentStatus,
    Document,
    DocumentStatus,
    DocumentType,
    Message,
    MessageStatus,
    Payment,
    PaymentStatus,
)
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.student import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    AppointmentCreate,
    AppointmentResponse,
    DashboardStats,
    DocumentCreate,
    DocumentResponse,
    MessageCreate,
    MessageResponse,
    PaymentResponse,
    ProfileUpdate,
)

router = APIRouter(prefix="/student", tags=["student"])

student_only = require_roles(UserRole.STUDENT)


def _get_owned_application(db: Session, application_id: UUID, student_id: UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None or application.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> DashboardStats:
    student_id = current_user.id
    applications_total = (
        db.scalar(select(func.count()).select_from(Application).where(Application.student_id == student_id))
        or 0
    )
    applications_active = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.student_id == student_id,
                Application.status.notin_(
                    [ApplicationStatus.COMPLETED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]
                ),
            )
        )
        or 0
    )
    documents_total = (
        db.scalar(select(func.count()).select_from(Document).where(Document.student_id == student_id)) or 0
    )
    documents_pending = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.student_id == student_id,
                Document.status.in_([DocumentStatus.PENDING, DocumentStatus.UNDER_REVIEW]),
            )
        )
        or 0
    )
    payments_pending = (
        db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.student_id == student_id, Payment.status == PaymentStatus.PENDING)
        )
        or 0
    )
    appointments_upcoming = (
        db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.student_id == student_id,
                Appointment.status.in_([AppointmentStatus.REQUESTED, AppointmentStatus.CONFIRMED]),
                Appointment.preferred_date >= date.today(),
            )
        )
        or 0
    )
    messages_unread = (
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.student_id == student_id,
                Message.is_from_student.is_(False),
                Message.status == MessageStatus.UNREAD,
            )
        )
        or 0
    )
    return DashboardStats(
        applications_total=applications_total,
        applications_active=applications_active,
        documents_total=documents_total,
        documents_pending=documents_pending,
        payments_pending=payments_pending,
        appointments_upcoming=appointments_upcoming,
        messages_unread=messages_unread,
    )


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(student_only)) -> User:
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.student_id == current_user.id)
            .order_by(Application.created_at.desc())
        ).all()
    )


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Application:
    application = Application(
        student_id=current_user.id,
        university_name=payload.university_name.strip(),
        country=payload.country.strip(),
        program_name=payload.program_name.strip(),
        degree_level=payload.degree_level.strip(),
        intake=payload.intake.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Application:
    return _get_owned_application(db, application_id, current_user.id)


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Application:
    application = _get_owned_application(db, application_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    # Students may only set draft/submitted/withdrawn locally; other statuses are staff-managed.
    if "status" in data and data["status"] not in {
        ApplicationStatus.DRAFT,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.WITHDRAWN,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Students can only set draft, submitted, or withdrawn status",
        )
    for key, value in data.items():
        setattr(application, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(application)
    return application


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> list[Document]:
    return list(
        db.scalars(
            select(Document).where(Document.student_id == current_user.id).order_by(Document.created_at.desc())
        ).all()
    )


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Document:
    if payload.application_id is not None:
        _get_owned_application(db, payload.application_id, current_user.id)

    document = Document(
        student_id=current_user.id,
        application_id=payload.application_id,
        document_type=payload.document_type,
        title=payload.title.strip(),
        file_url=payload.file_url.strip() if payload.file_url else None,
        notes=payload.notes.strip() if payload.notes else None,
        status=DocumentStatus.UPLOADED if payload.file_url else DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_student_document(
    document_type: DocumentType = Form(...),
    title: str = Form(..., min_length=2, max_length=255),
    notes: str | None = Form(default=None),
    application_id: UUID | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Document:
    if application_id is not None:
        _get_owned_application(db, application_id, current_user.id)

    file_url = upload_document(
        file.file,
        filename=file.filename or "document",
        content_type=file.content_type,
        folder=f"primexium/documents/{current_user.id}",
    )

    document = Document(
        student_id=current_user.id,
        application_id=application_id,
        document_type=document_type,
        title=title.strip(),
        file_url=file_url,
        notes=notes.strip() if notes else None,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> None:
    document = db.get(Document, document_id)
    if document is None or document.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(document)
    db.commit()


@router.get("/payments", response_model=list[PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment).where(Payment.student_id == current_user.id).order_by(Payment.created_at.desc())
        ).all()
    )


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment)
            .where(Appointment.student_id == current_user.id)
            .order_by(Appointment.preferred_date.desc())
        ).all()
    )


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Appointment:
    if payload.preferred_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferred date cannot be in the past",
        )
    appointment = Appointment(
        student_id=current_user.id,
        topic=payload.topic.strip(),
        preferred_date=payload.preferred_date,
        preferred_time=payload.preferred_time.strip(),
        meeting_mode=payload.meeting_mode.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        status=AppointmentStatus.REQUESTED,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
)
def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if appointment.status in {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment cannot be cancelled",
        )
    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/messages", response_model=list[MessageResponse])
def list_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> list[Message]:
    return list(
        db.scalars(
            select(Message).where(Message.student_id == current_user.id).order_by(Message.created_at.desc())
        ).all()
    )


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Message:
    message = Message(
        student_id=current_user.id,
        sender_id=current_user.id,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
        status=MessageStatus.UNREAD,
        is_from_student=True,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/messages/{message_id}/read", response_model=MessageResponse)
def mark_message_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> Message:
    message = db.get(Message, message_id)
    if message is None or message.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if not message.is_from_student:
        message.status = MessageStatus.READ
        db.commit()
        db.refresh(message)
    return message
