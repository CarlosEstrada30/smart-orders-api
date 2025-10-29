"""change_quantity_decimal_places_to_2

Revision ID: 83779a0ffe7c
Revises: a351b18f515d
Create Date: 2025-10-29 13:22:10.752011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '83779a0ffe7c'
down_revision = 'a351b18f515d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cambiar la columna quantity en order_items de Numeric(10,3) a Numeric(10,2)
    op.alter_column('order_items', 'quantity',
                   existing_type=sa.Numeric(10, 3),
                   type_=sa.Numeric(10, 2),
                   nullable=False)
    
    # Cambiar la columna quantity en inventory_entry_items de Numeric(10,3) a Numeric(10,2)
    op.alter_column('inventory_entry_items', 'quantity',
                   existing_type=sa.Numeric(10, 3),
                   type_=sa.Numeric(10, 2),
                   nullable=False)


def downgrade() -> None:
    # Revertir la columna quantity en order_items de Numeric(10,2) a Numeric(10,3)
    op.alter_column('order_items', 'quantity',
                   existing_type=sa.Numeric(10, 2),
                   type_=sa.Numeric(10, 3),
                   nullable=False)
    
    # Revertir la columna quantity en inventory_entry_items de Numeric(10,2) a Numeric(10,3)
    op.alter_column('inventory_entry_items', 'quantity',
                   existing_type=sa.Numeric(10, 2),
                   type_=sa.Numeric(10, 3),
                   nullable=False) 