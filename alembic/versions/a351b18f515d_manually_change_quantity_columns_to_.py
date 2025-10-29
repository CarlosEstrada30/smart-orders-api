"""manually_change_quantity_columns_to_numeric

Revision ID: a351b18f515d
Revises: 3928f3e26d4f
Create Date: 2025-10-29 13:10:44.049962

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a351b18f515d'
down_revision = '3928f3e26d4f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cambiar la columna quantity en order_items de Integer a Numeric(10,3)
    op.alter_column('order_items', 'quantity',
                   existing_type=sa.Integer(),
                   type_=sa.Numeric(10, 3),
                   nullable=False)
    
    # Cambiar la columna quantity en inventory_entry_items de Integer a Numeric(10,3)
    op.alter_column('inventory_entry_items', 'quantity',
                   existing_type=sa.Integer(),
                   type_=sa.Numeric(10, 3),
                   nullable=False)


def downgrade() -> None:
    # Revertir la columna quantity en order_items de Numeric(10,3) a Integer
    op.alter_column('order_items', 'quantity',
                   existing_type=sa.Numeric(10, 3),
                   type_=sa.Integer(),
                   nullable=False)
    
    # Revertir la columna quantity en inventory_entry_items de Numeric(10,3) a Integer
    op.alter_column('inventory_entry_items', 'quantity',
                   existing_type=sa.Numeric(10, 3),
                   type_=sa.Integer(),
                   nullable=False) 