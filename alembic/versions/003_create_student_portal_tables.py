"""create student portal tables

Revision ID: 003
Revises: 002
Create Date: 2026-07-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    application_status = postgresql.ENUM(
        "draft",
        "submitted",
        "under_review",
        "offer_received",
        "visa_stage",
        "completed",
        "rejected",
        "withdrawn",
        name="applicationstatus",
        create_type=False,
    )
    document_type = postgresql.ENUM(
        "passport",
        "transcript",
        "degree",
        "cv",
        "sop",
        "recommendation",
        "english_test",
        "moi",
        "experience_letter",
        "bank_statement",
        "other",
        name="documenttype",
        create_type=False,
    )
    document_status = postgresql.ENUM(
        "pending",
        "uploaded",
        "under_review",
        "approved",
        "rejected",
        name="documentstatus",
        create_type=False,
    )
    payment_status = postgresql.ENUM(
        "pending",
        "paid",
        "failed",
        "refunded",
        name="paymentstatus",
        create_type=False,
    )
    appointment_status = postgresql.ENUM(
        "requested",
        "confirmed",
        "completed",
        "cancelled",
        name="appointmentstatus",
        create_type=False,
    )
    message_status = postgresql.ENUM(
        "unread",
        "read",
        name="messagestatus",
        create_type=False,
    )

    for enum_type in (
        application_status,
        document_type,
        document_status,
        payment_status,
        appointment_status,
        message_status,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("university_name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("program_name", sa.String(255), nullable=False),
        sa.Column("degree_level", sa.String(50), nullable=False),
        sa.Column("intake", sa.String(50), nullable=False),
        sa.Column("status", application_status, nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_applications_student_id", "applications", ["student_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("status", document_status, nullable=False, server_default="uploaded"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_student_id", "documents", ["student_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="PKR"),
        sa.Column("status", payment_status, nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payments_student_id", "payments", ["student_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_time", sa.String(50), nullable=False),
        sa.Column("meeting_mode", sa.String(50), nullable=False, server_default="online"),
        sa.Column("status", appointment_status, nullable=False, server_default="requested"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_student_id", "appointments", ["student_id"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", message_status, nullable=False, server_default="unread"),
        sa.Column("is_from_student", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_student_id", "messages", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_student_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_student_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_student_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_documents_student_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_student_id", table_name="applications")
    op.drop_table("applications")
    op.execute("DROP TYPE IF EXISTS messagestatus")
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
