"""Add company finance ledger for consultancy expenditure analytics.

Revision ID: 006
Revises: 005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_company_finance_ledger"
down_revision: str | None = "005_tracking_referral_followups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    entry_type = postgresql.ENUM(
        "income",
        "expense",
        "saving",
        "investment",
        name="financeentrytype",
        create_type=False,
    )
    category = postgresql.ENUM(
        "client_fee",
        "partner_payout",
        "other_income",
        "transport",
        "subscription",
        "domain",
        "marketing",
        "office_rent",
        "office_supplies",
        "utilities",
        "salary",
        "software",
        "reserve",
        "equipment",
        "other",
        name="financecategory",
        create_type=False,
    )
    payment_method = postgresql.ENUM(
        "cash",
        "bank",
        "jazzcash",
        "easypaisa",
        "card",
        "other",
        name="financepaymentmethod",
        create_type=False,
    )
    entry_type.create(op.get_bind(), checkfirst=True)
    category.create(op.get_bind(), checkfirst=True)
    payment_method.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "finance_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("type", entry_type, nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="PKR"),
        sa.Column("paid_by_name", sa.String(length=120), nullable=True),
        sa.Column("paid_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_finance_entries_entry_date", "finance_entries", ["entry_date"])
    op.create_index("ix_finance_entries_type", "finance_entries", ["type"])
    op.create_index("ix_finance_entries_category", "finance_entries", ["category"])


def downgrade() -> None:
    op.drop_index("ix_finance_entries_category", table_name="finance_entries")
    op.drop_index("ix_finance_entries_type", table_name="finance_entries")
    op.drop_index("ix_finance_entries_entry_date", table_name="finance_entries")
    op.drop_table("finance_entries")
    op.execute(sa.text("DROP TYPE IF EXISTS financepaymentmethod"))
    op.execute(sa.text("DROP TYPE IF EXISTS financecategory"))
    op.execute(sa.text("DROP TYPE IF EXISTS financeentrytype"))
