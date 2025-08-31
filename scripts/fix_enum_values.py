#!/usr/bin/env python3
"""
Fix enum values to ensure they work correctly
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import settings

def fix_enum_values():
    """Fix enum values by recreating them properly"""
    
    print("🔧 Fixing FEL enum values...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            with connection.begin():
                # First, check current enum values
                print("📋 Checking current enum values...")
                result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
                current_values = [row[0] for row in result.fetchall()]
                print(f"Current values: {current_values}")
                
                # Add the missing values if they don't exist
                new_values = ['fel_pending', 'fel_authorized', 'fel_rejected']
                
                for value in new_values:
                    if value not in current_values:
                        print(f"Adding enum value: {value}")
                        connection.execute(text(f"ALTER TYPE invoicestatus ADD VALUE '{value}'"))
                    else:
                        print(f"✅ Enum value '{value}' already exists")
                
                # Verify final state
                print("\n📋 Final enum values:")
                result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
                final_values = [row[0] for row in result.fetchall()]
                for value in final_values:
                    print(f"   - {value}")
        
        print("✅ Enum values fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing enum values: {e}")
        return False

def test_enum_update():
    """Test updating an invoice status to ensure enum works"""
    
    print("\n🧪 Testing enum update...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            with connection.begin():
                # Get first invoice
                result = connection.execute(text("SELECT id FROM invoices LIMIT 1"))
                row = result.fetchone()
                
                if not row:
                    print("⚠️ No invoices found to test with")
                    return True
                
                invoice_id = row[0]
                print(f"Testing with invoice ID: {invoice_id}")
                
                # Try updating to fel_pending
                print("Trying to update status to 'fel_pending'...")
                connection.execute(text("UPDATE invoices SET status = 'fel_pending' WHERE id = :id"), 
                                 {"id": invoice_id})
                
                # Verify update
                result = connection.execute(text("SELECT status FROM invoices WHERE id = :id"), 
                                          {"id": invoice_id})
                new_status = result.fetchone()[0]
                print(f"✅ Status updated to: {new_status}")
                
                # Reset to draft
                connection.execute(text("UPDATE invoices SET status = 'draft' WHERE id = :id"), 
                                 {"id": invoice_id})
                print("✅ Status reset to draft")
        
        print("✅ Enum update test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Enum update test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix FEL enum values')
    parser.add_argument('--test-only', action='store_true', help='Only run test')
    
    args = parser.parse_args()
    
    if args.test_only:
        test_enum_update()
    else:
        success = fix_enum_values()
        if success:
            test_enum_update()

