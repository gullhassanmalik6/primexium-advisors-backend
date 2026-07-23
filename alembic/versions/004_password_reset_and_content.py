"""password reset tokens and content items

Revision ID: 004
Revises: 003
Create Date: 2026-07-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    content_type = postgresql.ENUM(
        "country",
        "university",
        "package",
        "blog",
        "testimonial",
        name="contenttype",
        create_type=False,
    )
    content_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_items_content_type", "content_items", ["content_type"])
    op.create_index("ix_content_items_slug", "content_items", ["slug"])
    op.create_index("ix_content_items_is_published", "content_items", ["is_published"])
    op.create_index(
        "ix_content_items_type_slug",
        "content_items",
        ["content_type", "slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_content_items_type_slug", table_name="content_items")
    op.drop_index("ix_content_items_is_published", table_name="content_items")
    op.drop_index("ix_content_items_slug", table_name="content_items")
    op.drop_index("ix_content_items_content_type", table_name="content_items")
    op.drop_table("content_items")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.execute("DROP TYPE IF EXISTS contenttype")
