"""Add balance and referral fields to users

Revision ID: 005_add_user_balances
Revises: 004_add_phone_to_users
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_user_balances'
down_revision = '004_add_phone_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('balance', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))
    op.add_column('users', sa.Column('fiat_balance', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))
    op.add_column('users', sa.Column('referred_by', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('referrals_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('referral_earned', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'referral_earned')
    op.drop_column('users', 'referrals_count')
    op.drop_column('users', 'referred_by')
    op.drop_column('users', 'fiat_balance')
    op.drop_column('users', 'balance')
