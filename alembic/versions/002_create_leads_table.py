"""create leads table

Revision ID: 002
Revises: 001
Create Date: 2026-07-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    lead_type = postgresql.ENUM(
        "contact",
        "consultation",
        "eligibility",
        name="leadtype",
        create_type=False,
    )
    lead_status = postgresql.ENUM(
        "new",
        "contacted",
        "qualified",
        "converted",
        "closed",
        name="leadstatus",
        create_type=False,
    )
    lead_type.create(op.get_bind(), checkfirst=True)
    lead_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_type", lead_type, nullable=False),
        sa.Column("status", lead_status, nullable=False, server_default="new"),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("preferred_country", sa.String(100), nullable=True),
        sa.Column("preferred_degree", sa.String(100), nullable=True),
        sa.Column("preferred_intake", sa.String(50), nullable=True),
        sa.Column("eligibility_score", sa.Integer(), nullable=True),
        sa.Column("eligibility_tier", sa.String(50), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_leads_lead_type", "leads", ["lead_type"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_email", "leads", ["email"])


def downgrade() -> None:
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_lead_type", table_name="leads")
    op.drop_table("leads")
    op.execute("DROP TYPE IF EXISTS leadstatus")
    op.execute("DROP TYPE IF EXISTS leadtype")
