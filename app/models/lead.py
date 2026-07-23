import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class LeadType(str, enum.Enum):
    CONTACT = "contact"
    CONSULTATION = "consultation"
    ELIGIBILITY = "eligibility"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    CLOSED = "closed"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_type: Mapped[LeadType] = mapped_column(
        Enum(
            LeadType,
            name="leadtype",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus,
            name="leadstatus",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=LeadStatus.NEW,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_degree: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_intake: Mapped[str | None] = mapped_column(String(50), nullable=True)
    eligibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligibility_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
