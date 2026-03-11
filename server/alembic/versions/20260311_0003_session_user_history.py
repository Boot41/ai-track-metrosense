"""add user ownership and titles to sessions

Revision ID: 20260311_0005
Revises: 20260311_0004
Create Date: 2026-03-11 12:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260311_0005"
down_revision = "20260311_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("title", sa.String(length=200), nullable=True))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_foreign_key("fk_sessions_user_id_users", "sessions", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_sessions_user_id_users", "sessions", type_="foreignkey")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_column("sessions", "title")
    op.drop_column("sessions", "user_id")
