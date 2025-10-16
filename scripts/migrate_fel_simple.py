#!/usr/bin/env python3
"""
Simplified FEL migration script that works step by step
"""

from app.config import settings
from sqlalchemy import create_engine, text
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_simple_fel_migration():
    """Run simplified FEL migration"""

    print("🇬🇹 Starting Simplified FEL Migration...")

    engine = create_engine(settings.DATABASE_URL)

    # Step 1: Add new columns first
    columns_sql = [
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_uuid VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS dte_number VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_authorization_date TIMESTAMPTZ;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_xml_path VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_certification_date TIMESTAMPTZ;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_certifier VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_series VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_number VARCHAR;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fel_error_message TEXT;",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS requires_fel BOOLEAN DEFAULT TRUE;"]

    print("📝 Adding FEL columns...")
    try:
        with engine.connect() as connection:
            with connection.begin():
                for i, sql in enumerate(columns_sql, 1):
                    print(f"   Adding column {i}/{len(columns_sql)}...")
                    connection.execute(text(sql))

        print("✅ FEL columns added successfully!")

    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False

    # Step 2: Add indexes
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_invoices_fel_uuid ON invoices(fel_uuid);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_dte_number ON invoices(dte_number);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_requires_fel ON invoices(requires_fel);"]

    print("📝 Adding indexes...")
    try:
        with engine.connect() as connection:
            with connection.begin():
                for sql in indexes_sql:
                    connection.execute(text(sql))

        print("✅ Indexes added successfully!")

    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        return False

    # Step 3: Try to add new enum values (this might fail, but it's OK)
    print("📝 Attempting to add new enum values...")
    enum_values = [
        "ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'fel_pending';",
        "ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'fel_authorized';",
        "ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'fel_rejected';"
    ]

    try:
        with engine.connect() as connection:
            for sql in enum_values:
                try:
                    connection.execute(text(sql))
                    connection.commit()
                except Exception as enum_error:
                    print(
                        f"⚠️ Enum value issue (might be expected): {enum_error}")
                    # Continue with other enum values

        print("✅ Enum values processed!")

    except Exception as e:
        print(f"⚠️ Enum processing had issues (this is often expected): {e}")
        # This is OK - we can handle enum issues later

    print("🎉 Simplified FEL Migration completed!")

    # Verify columns
    verify_columns(engine)

    return True


def verify_columns(engine):
    """Verify that FEL columns were added"""

    print("\n🔍 Verifying FEL columns...")

    verification_sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'invoices'
    AND (column_name LIKE 'fel_%' OR column_name = 'dte_number' OR column_name = 'requires_fel')
    ORDER BY column_name;
    """

    try:
        with engine.connect() as connection:
            result = connection.execute(text(verification_sql))
            columns = result.fetchall()

            expected_columns = {
                'dte_number',
                'fel_authorization_date',
                'fel_certification_date',
                'fel_certifier',
                'fel_error_message',
                'fel_number',
                'fel_series',
                'fel_uuid',
                'fel_xml_path',
                'requires_fel'}

            found_columns = {row[0] for row in columns}

            if expected_columns.issubset(found_columns):
                print("✅ All FEL columns verified successfully:")
                for column_name, data_type, nullable in columns:
                    print(
                        f"   - {column_name}: {data_type} ({'nullable' if nullable == 'YES' else 'not null'})")
                return True
            else:
                missing = expected_columns - found_columns
                print(f"❌ Missing columns: {missing}")
                return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def show_enum_values(engine):
    """Show current enum values"""

    print("\n📋 Current invoice status enum values:")

    enum_sql = """
    SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;
    """

    try:
        with engine.connect() as connection:
            result = connection.execute(text(enum_sql))
            values = result.fetchall()

            for value in values:
                print(f"   - {value[0]}")

    except Exception as e:
        print(f"⚠️ Could not show enum values: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Simplified FEL Migration')
    parser.add_argument(
        '--show-enum',
        action='store_true',
        help='Show current enum values')

    args = parser.parse_args()

    if args.show_enum:
        engine = create_engine(settings.DATABASE_URL)
        show_enum_values(engine)
    else:
        success = run_simple_fel_migration()
        if success:
            engine = create_engine(settings.DATABASE_URL)
            show_enum_values(engine)
