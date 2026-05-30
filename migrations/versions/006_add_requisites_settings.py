"""Add requisites settings to global_settings

Revision ID: 006
Revises: 005
Create Date: 2026-05-30 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO global_settings (key, value) VALUES ('requisites_card', '0000 0000 0000 0000') "
        "ON CONFLICT (key) DO NOTHING"
    )
    op.execute(
        "INSERT INTO global_settings (key, value) VALUES ('requisites_wallet', 'TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM global_settings WHERE key = 'requisites_card'")
    op.execute("DELETE FROM global_settings WHERE key = 'requisites_wallet'")
