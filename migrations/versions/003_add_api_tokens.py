"""add api_tokens table

Revision ID: 003
Revises: 002
Create Date: 2026-05-25 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("jti", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])
    op.create_index("ix_api_tokens_jti", "api_tokens", ["jti"])


def downgrade() -> None:
    op.drop_index("ix_api_tokens_jti", table_name="api_tokens")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
