"""add_payment_system_to_orders

Revision ID: eb91b5d3cd61
Revises: 83779a0ffe7c
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'eb91b5d3cd61'
down_revision = '83779a0ffe7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The paymentmethod enum already exists from Invoice model with values:
    # CASH, CREDIT_CARD, BANK_TRANSFER, CHECK, OTHER
    # We need to add 'DEBIT_CARD' value if it doesn't exist
    # Note: PostgreSQL requires this to be done outside a transaction block
    # So we'll try to add it, and if it fails (already exists), we'll continue
    try:
        op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'DEBIT_CARD'")
    except Exception:
        # Value might already exist or enum might not exist yet, continue anyway
        pass
    
    # Create orderpaymentstatus enum (new enum for Order.payment_status)
    # Check if it exists first to avoid errors
    # In multitenant systems, each schema needs its own enum
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE t.typname = 'orderpaymentstatus'
            AND n.nspname = current_schema()
        )
    """))
    enum_exists = result.scalar()
    
    if not enum_exists:
        op.execute("CREATE TYPE orderpaymentstatus AS ENUM ('unpaid', 'partial', 'paid')")
    
    # Create payments table
    # Reuse existing paymentmethod enum (it already exists from Invoice)
    # Note: The enum in DB has uppercase values (CASH, CREDIT_CARD, etc.) but SQLAlchemy handles conversion
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_number', sa.String(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        # Use existing paymentmethod enum (values are uppercase: CASH, CREDIT_CARD, etc.)
        # SQLAlchemy will handle conversion between Python lowercase and DB uppercase
        # Use postgresql.ENUM with create_type=False and existing_type=True to reuse existing type
        sa.Column('payment_method', postgresql.ENUM('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'CHECK', 'OTHER', name='paymentmethod', create_type=False, existing_type=True), nullable=False),
        sa.Column('status', sa.Enum('confirmed', 'cancelled', name='paymentstatus'), nullable=True, server_default='confirmed'),
        sa.Column('payment_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_payment_number'), 'payments', ['payment_number'], unique=True)
    op.create_index(op.f('ix_payments_order_id'), 'payments', ['order_id'], unique=False)

    # Add payment tracking fields to orders table
    op.add_column('orders', sa.Column('paid_amount', sa.Numeric(10, 2), nullable=True, server_default='0.0'))
    op.add_column('orders', sa.Column('balance_due', sa.Numeric(10, 2), nullable=True, server_default='0.0'))
    # Use postgresql.ENUM with create_type=False - the enum was created above
    # We need to use postgresql.ENUM to explicitly reference the existing type
    op.add_column('orders', sa.Column('payment_status', postgresql.ENUM('unpaid', 'partial', 'paid', name='orderpaymentstatus', create_type=False), nullable=True, server_default='unpaid'))
    
    # Update ALL existing orders: set balance_due = total_amount and payment_status = 'unpaid'
    # This ensures all existing orders have the correct initial values
    op.execute("""
        UPDATE orders 
        SET balance_due = total_amount,
            payment_status = 'unpaid'
    """)
    
    # Make balance_due NOT NULL after setting values
    op.alter_column('orders', 'balance_due', nullable=False, server_default=None)
    op.alter_column('orders', 'payment_status', nullable=False, server_default='unpaid')


def downgrade() -> None:
    # Remove payment_status column
    op.alter_column('orders', 'payment_status', nullable=True)
    op.drop_column('orders', 'payment_status')
    
    # Remove payment tracking fields from orders
    op.drop_column('orders', 'balance_due')
    op.drop_column('orders', 'paid_amount')
    
    # Drop payments table
    op.drop_index(op.f('ix_payments_order_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_payment_number'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    
    # Drop enum types (Alembic will handle this automatically, but we can do it explicitly)
    # Note: paymentmethod enum is also used by Invoice, so we should NOT drop it
    op.execute("DROP TYPE IF EXISTS orderpaymentstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    # Do NOT drop paymentmethod as it's used by Invoice table

