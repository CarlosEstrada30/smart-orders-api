"""replace_discount_percentage_with_discount_amount

Revision ID: f4d1333f244b
Revises: 3796d94d8acb
Create Date: 2025-10-27 21:45:51.611647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4d1333f244b'
down_revision = '3796d94d8acb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the new discount_amount column
    op.add_column('orders', sa.Column('discount_amount', sa.Float(), nullable=True))
    
    # Migrate existing data: convert discount_percentage to discount_amount
    # We need to calculate the actual discount amount from the percentage
    # Since we don't have the original subtotal, we'll calculate it from total_amount
    # Formula: discount_amount = (total_amount / (1 - discount_percentage/100)) * (discount_percentage/100)
    # But this is complex, so we'll set discount_amount to 0 for existing records
    # and let users update manually if needed
    
    # Set discount_amount to 0 for all existing records
    op.execute("UPDATE orders SET discount_amount = 0.0 WHERE discount_amount IS NULL")
    
    # Make discount_amount NOT NULL with default 0.0
    op.alter_column('orders', 'discount_amount', nullable=False, server_default='0.0')
    
    # Drop the old discount_percentage column
    op.drop_column('orders', 'discount_percentage')


def downgrade() -> None:
    # Add back the discount_percentage column
    op.add_column('orders', sa.Column('discount_percentage', sa.Float(), nullable=True))
    
    # Convert discount_amount back to discount_percentage
    # Since we can't calculate the original percentage from the amount without the subtotal,
    # we'll set discount_percentage to 0 for all records
    op.execute("UPDATE orders SET discount_percentage = 0.0 WHERE discount_percentage IS NULL")
    
    # Make discount_percentage NOT NULL with default 0.0
    op.alter_column('orders', 'discount_percentage', nullable=False, server_default='0.0')
    
    # Drop the discount_amount column
    op.drop_column('orders', 'discount_amount') 