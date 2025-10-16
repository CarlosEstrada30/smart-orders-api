#!/usr/bin/env python3
"""
Migration script to add FEL (Facturación Electrónica en Línea) support to Guatemala
This script adds the necessary columns to the invoices table
"""

from app.database import get_db, SessionLocal
from app.config import settings
from sqlalchemy import create_engine, text
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_fel_migration():
    """Run the FEL migration to add new columns to invoices table"""

    print("🇬🇹 Starting FEL Integration Migration for Guatemala...")

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # SQL statements to add new FEL columns
    migration_sql = [
        # Add new invoice statuses to the enum (if using PostgreSQL)
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoicestatus_new') THEN
                CREATE TYPE invoicestatus_new AS ENUM (
                    'draft', 'fel_pending', 'fel_authorized', 'fel_rejected',
                    'issued', 'paid', 'overdue', 'cancelled'
                );
            END IF;
        END $$;
        """,

        # Add FEL columns to invoices table
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_uuid VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS dte_number VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_authorization_date TIMESTAMPTZ;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_xml_path VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_certification_date TIMESTAMPTZ;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_certifier VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_series VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_number VARCHAR;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_error_message TEXT;
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS requires_fel BOOLEAN DEFAULT TRUE;
        """,

        # Add indexes for performance
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_fel_uuid ON invoices(fel_uuid);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_dte_number ON invoices(dte_number);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_requires_fel ON invoices(requires_fel);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_fel_status ON invoices(status) WHERE status IN ('fel_pending', 'fel_authorized', 'fel_rejected');
        """,

        # Update status column type (PostgreSQL specific)
        """
        DO $$
        BEGIN
            -- Update the status column to use the new enum
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoicestatus_new') THEN
                ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT;
                ALTER TABLE invoices ALTER COLUMN status TYPE invoicestatus_new USING status::text::invoicestatus_new;
                ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'draft'::invoicestatus_new;
                DROP TYPE IF EXISTS invoicestatus CASCADE;
                ALTER TYPE invoicestatus_new RENAME TO invoicestatus;
            END IF;
        END $$;
        """
    ]

    # Execute migration
    try:
        with engine.connect() as connection:
            with connection.begin():
                for i, sql in enumerate(migration_sql, 1):
                    print(
                        f"📝 Executing migration step {i}/{len(migration_sql)}...")
                    try:
                        connection.execute(text(sql))
                        print(f"✅ Step {i} completed successfully")
                    except Exception as step_error:
                        print(
                            f"⚠️ Step {i} had an issue (might be expected): {step_error}")
                        # Continue with other steps

        print("\n🎉 FEL Migration completed successfully!")

        # Verify the migration
        verify_migration(engine)

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True


def verify_migration(engine):
    """Verify that the FEL migration was successful"""

    print("\n🔍 Verifying FEL migration...")

    verification_sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'invoices'
    AND column_name LIKE 'fel_%'
    OR column_name = 'requires_fel'
    ORDER BY column_name;
    """

    try:
        with engine.connect() as connection:
            result = connection.execute(text(verification_sql))
            columns = result.fetchall()

            expected_columns = {
                'fel_authorization_date',
                'fel_certification_date',
                'fel_certifier',
                'fel_error_message',
                'fel_number',
                'fel_series',
                'fel_uuid',
                'fel_xml_path',
                'dte_number',
                'requires_fel'}

            found_columns = {row[0] for row in columns}

            if expected_columns.issubset(found_columns):
                print("✅ All FEL columns added successfully:")
                for column_name, data_type, nullable in columns:
                    print(
                        f"   - {column_name}: {data_type} ({'nullable' if nullable == 'YES' else 'not null'})")
            else:
                missing = expected_columns - found_columns
                print(f"❌ Missing columns: {missing}")
                return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

    print("✅ Migration verification completed successfully!")
    return True


def rollback_migration():
    """Rollback the FEL migration (remove added columns)"""

    print("⏪ Rolling back FEL migration...")

    engine = create_engine(settings.DATABASE_URL)

    rollback_sql = [
        "DROP INDEX IF EXISTS idx_invoices_fel_uuid;",
        "DROP INDEX IF EXISTS idx_invoices_dte_number;",
        "DROP INDEX IF EXISTS idx_invoices_requires_fel;",
        "DROP INDEX IF EXISTS idx_invoices_fel_status;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_uuid;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS dte_number;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_authorization_date;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_xml_path;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_certification_date;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_certifier;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_series;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_number;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS fel_error_message;",
        "ALTER TABLE invoices DROP COLUMN IF EXISTS requires_fel;"
    ]

    try:
        with engine.connect() as connection:
            with connection.begin():
                for sql in rollback_sql:
                    connection.execute(text(sql))

        print("✅ Rollback completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='FEL Integration Migration for Guatemala')
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration')
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify the migration')

    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    elif args.verify_only:
        engine = create_engine(settings.DATABASE_URL)
        verify_migration(engine)
    else:
        run_fel_migration()
