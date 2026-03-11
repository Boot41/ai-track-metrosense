"""ensure users table exists

Revision ID: 20260311_0004
Revises: 20260311_0003
Create Date: 2026-03-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260311_0004"
down_revision = "20260311_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT to_regclass('public.users')")).scalar()
    if exists is not None:
        return
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
