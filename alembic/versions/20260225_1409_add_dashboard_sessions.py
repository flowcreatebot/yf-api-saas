"""add dashboard sessions

Revision ID: 20260225_1409
Revises: 20260225_1308
Create Date: 2026-02-25 14:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260225_1409"
down_revision: Union[str, None] = "20260225_1308"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dashboard_sessions_expires_at"), "dashboard_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_dashboard_sessions_id"), "dashboard_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_dashboard_sessions_revoked_at"), "dashboard_sessions", ["revoked_at"], unique=False)
    op.create_index(op.f("ix_dashboard_sessions_token_hash"), "dashboard_sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_dashboard_sessions_user_id"), "dashboard_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_sessions_user_id"), table_name="dashboard_sessions")
    op.drop_index(op.f("ix_dashboard_sessions_token_hash"), table_name="dashboard_sessions")
    op.drop_index(op.f("ix_dashboard_sessions_revoked_at"), table_name="dashboard_sessions")
    op.drop_index(op.f("ix_dashboard_sessions_id"), table_name="dashboard_sessions")
    op.drop_index(op.f("ix_dashboard_sessions_expires_at"), table_name="dashboard_sessions")
    op.drop_table("dashboard_sessions")
