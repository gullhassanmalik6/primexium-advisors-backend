"""Add referral fields, application tracking enrichments, history, and follow-ups.

Revision ID: 005
Revises: 004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_tracking_referral_followups"
down_revision: str | None = "004_password_reset_and_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_APP_STATUSES = (
    "registration_received",
    "initial_assessment",
    "documents_pending",
    "documents_under_review",
    "university_selection",
    "application_preparation",
    "further_action_required",
    "campus_france",
    "pre_departure",
    "on_hold",
)


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_normalized", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("referral_source", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("referral_detail", sa.String(length=255), nullable=True))
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.create_index("ix_users_phone_normalized", "users", ["phone_normalized"])

    op.add_column("applications", sa.Column("student_note", sa.Text(), nullable=True))
    op.add_column("applications", sa.Column("next_action", sa.String(length=500), nullable=True))
    op.add_column("applications", sa.Column("next_action_due", sa.Date(), nullable=True))
    op.add_column("applications", sa.Column("missing_documents", sa.Text(), nullable=True))
    op.add_column(
        "applications",
        sa.Column("stage_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Expand PostgreSQL enum outside a transactional block where required.
    with op.get_context().autocommit_block():
        for value in NEW_APP_STATUSES:
            op.execute(sa.text(f"ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS '{value}'"))

    op.create_table(
        "application_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("changed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_safe_note", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(length=500), nullable=True),
        sa.Column("next_action_due", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_application_status_history_application_id",
        "application_status_history",
        ["application_id"],
    )

    followup_method = postgresql.ENUM(
        "phone",
        "email",
        "whatsapp",
        "in_person",
        "other",
        name="followupmethod",
        create_type=False,
    )
    followup_status = postgresql.ENUM(
        "pending",
        "completed",
        "cancelled",
        name="followupstatus",
        create_type=False,
    )
    followup_method.create(op.get_bind(), checkfirst=True)
    followup_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=False),
        sa.Column("method", followup_method, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("next_action", sa.String(length=500), nullable=True),
        sa.Column("next_follow_up_date", sa.Date(), nullable=True),
        sa.Column("status", followup_status, nullable=False),
        sa.Column("visible_to_student", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("student_message", sa.Text(), nullable=True),
        sa.Column("related_status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_follow_ups_student_id", "follow_ups", ["student_id"])
    op.create_index("ix_follow_ups_follow_up_date", "follow_ups", ["follow_up_date"])
    op.create_index("ix_follow_ups_status", "follow_ups", ["status"])


def downgrade() -> None:
    op.drop_index("ix_follow_ups_status", table_name="follow_ups")
    op.drop_index("ix_follow_ups_follow_up_date", table_name="follow_ups")
    op.drop_index("ix_follow_ups_student_id", table_name="follow_ups")
    op.drop_table("follow_ups")
    op.execute(sa.text("DROP TYPE IF EXISTS followupstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS followupmethod"))

    op.drop_index("ix_application_status_history_application_id", table_name="application_status_history")
    op.drop_table("application_status_history")

    op.drop_column("applications", "stage_completed_at")
    op.drop_column("applications", "missing_documents")
    op.drop_column("applications", "next_action_due")
    op.drop_column("applications", "next_action")
    op.drop_column("applications", "student_note")

    op.drop_index("ix_users_phone_normalized", table_name="users")
    op.drop_column("users", "referral_detail")
    op.drop_column("users", "referral_source")
    op.drop_column("users", "phone_normalized")
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
