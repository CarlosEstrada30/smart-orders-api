"""add_currency_code_to_settings

Revision ID: 65e4b890a07e
Revises: eb91b5d3cd61
Create Date: 2026-08-19 09:25:23.285129

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '65e4b890a07e'
down_revision = 'eb91b5d3cd61'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'settings',
        sa.Column(
            'currency_code',
            sa.String(length=3),
            server_default='GTQ',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('settings', 'currency_code')
