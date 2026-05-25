"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-25 09:21:45.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role_enum = postgresql.ENUM(
    "super_admin", "admin", "operator", "client",
    name="user_role",
    create_type=False,
)
order_type_enum = postgresql.ENUM(
    "buy", "sell",
    name="order_type",
    create_type=False,
)
order_status_enum = postgresql.ENUM(
    "created", "cancelled", "completed",
    name="order_status",
    create_type=False,
)
rate_type_enum = postgresql.ENUM(
    "buy", "sell",
    name="rate_type",
    create_type=False,
)


def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)
    order_type_enum.create(op.get_bind(), checkfirst=True)
    order_status_enum.create(op.get_bind(), checkfirst=True)
    rate_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", user_role_enum, nullable=False, server_default="client"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_type", order_type_enum, nullable=False),
        sa.Column("amount_usdt", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_fiat", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("status", order_status_enum, nullable=False, server_default="created"),
        sa.Column("payment_link_snapshot", sa.Text(), nullable=True),
        sa.Column("link_broken", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])
    op.create_index("ix_orders_type_created", "orders", ["order_type", "created_at"])

    op.create_table(
        "rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rate_type", rate_type_enum, nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("set_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["set_by"], ["users.id"]),
    )

    op.create_table(
        "global_settings",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "notification_chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("added_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notification_chats")
    op.drop_table("global_settings")
    op.drop_table("rates")
    op.drop_index("ix_orders_type_created", table_name="orders")
    op.drop_index("ix_orders_status_created", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("users")

    rate_type_enum.drop(op.get_bind(), checkfirst=True)
    order_status_enum.drop(op.get_bind(), checkfirst=True)
    order_type_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
