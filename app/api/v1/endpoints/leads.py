from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.database.session import get_db
from app.models.lead import Lead, LeadStatus, LeadType
from app.models.user import User, UserRole
from app.schemas.lead import (
    ConsultationLeadCreate,
    ContactLeadCreate,
    EligibilityLeadCreate,
    LeadCreateResponse,
    LeadListResponse,
    LeadResponse,
    LeadStatusUpdate,
)

router = APIRouter(prefix="/leads", tags=["leads"])

STAFF_ROLES = (
    UserRole.ADMIN,
    UserRole.COUNSELLOR,
    UserRole.DOCUMENTATION_OFFICER,
    UserRole.FINANCE,
    UserRole.MARKETING,
)


@router.post("/contact", response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
def create_contact_lead(payload: ContactLeadCreate, db: Session = Depends(get_db)) -> LeadCreateResponse:
    lead = Lead(
        lead_type=LeadType.CONTACT,
        status=LeadStatus.NEW,
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip() if payload.phone else None,
        subject=payload.subject.strip(),
        message=payload.message.strip(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadCreateResponse(id=lead.id, message="Thank you! We will get back to you shortly.")


@router.post(
    "/consultation",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation_lead(
    payload: ConsultationLeadCreate,
    db: Session = Depends(get_db),
) -> LeadCreateResponse:
    lead = Lead(
        lead_type=LeadType.CONSULTATION,
        status=LeadStatus.NEW,
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip(),
        preferred_country=payload.preferred_country,
        preferred_degree=payload.preferred_degree,
        preferred_intake=payload.preferred_intake,
        message=payload.message.strip() if payload.message else None,
        subject="Book Consultation",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadCreateResponse(
        id=lead.id,
        message="Consultation request received. Our counsellor will contact you soon.",
    )


@router.post(
    "/eligibility",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_eligibility_lead(
    payload: EligibilityLeadCreate,
    db: Session = Depends(get_db),
) -> LeadCreateResponse:
    lead = Lead(
        lead_type=LeadType.ELIGIBILITY,
        status=LeadStatus.NEW,
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip(),
        preferred_country=payload.preferred_country,
        preferred_degree=payload.preferred_degree,
        preferred_intake=payload.preferred_intake,
        eligibility_score=payload.eligibility_score,
        eligibility_tier=payload.eligibility_tier,
        payload=payload.payload,
        subject="Eligibility Assessment",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadCreateResponse(
        id=lead.id,
        message="Eligibility assessment saved. An advisor may follow up with you.",
    )


@router.get("", response_model=LeadListResponse)
def list_leads(
    lead_type: LeadType | None = None,
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*STAFF_ROLES)),
) -> LeadListResponse:
    query = select(Lead)
    count_query = select(func.count()).select_from(Lead)

    if lead_type is not None:
        query = query.where(Lead.lead_type == lead_type)
        count_query = count_query.where(Lead.lead_type == lead_type)
    if lead_status is not None:
        query = query.where(Lead.status == lead_status)
        count_query = count_query.where(Lead.status == lead_status)

    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)).all()
    return LeadListResponse(items=list(items), total=total)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*STAFF_ROLES)),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead_status(
    lead_id: UUID,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*STAFF_ROLES)),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    lead.status = payload.status
    if payload.notes is not None:
        lead.notes = payload.notes
    db.commit()
    db.refresh(lead)
    return lead
