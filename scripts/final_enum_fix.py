#!/usr/bin/env python3
"""
Final fix for enum values - remove lowercase FEL values and add uppercase ones
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import settings

def final_enum_fix():
    """Final fix for enum values"""
    
    print("🔧 Final FEL Enum Fix...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # First, let's see what we have
        with engine.connect() as connection:
            print("📋 Current enum values:")
            result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
            current_values = [row[0] for row in result.fetchall()]
            for value in current_values:
                print(f"   - {value}")
        
        print("\n🔄 Step 1: Update all existing records to use uppercase...")
        with engine.connect() as connection:
            with connection.begin():
                # Update any records using lowercase FEL values to uppercase
                updates = [
                    ("fel_pending", "FEL_PENDING"),
                    ("fel_authorized", "FEL_AUTHORIZED"), 
                    ("fel_rejected", "FEL_REJECTED")
                ]
                
                for old_val, new_val in updates:
                    # First check if the new value exists in enum
                    try:
                        connection.execute(text(f"ALTER TYPE invoicestatus ADD VALUE '{new_val}'"))
                        print(f"✅ Added enum value: {new_val}")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"✅ Enum value {new_val} already exists")
                        else:
                            print(f"⚠️ Could not add {new_val}: {e}")
                
                # Now update any records
                for old_val, new_val in updates:
                    result = connection.execute(text(f"UPDATE invoices SET status = '{new_val}' WHERE status = '{old_val}'"))
                    if result.rowcount > 0:
                        print(f"Updated {result.rowcount} records from {old_val} to {new_val}")
        
        print("\n📋 Final enum values:")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
            final_values = [row[0] for row in result.fetchall()]
            for value in final_values:
                print(f"   - {value}")
        
        print("✅ Final enum fix completed!")
        return True
        
    except Exception as e:
        print(f"❌ Final enum fix failed: {e}")
        return False

def update_python_model():
    """Show the final Python model that should be used"""
    
    print("\n📝 FINAL PYTHON MODEL:")
    print("Update app/models/invoice.py:")
    print("""
class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"                          # Borrador
    FEL_PENDING = "FEL_PENDING"              # Enviando a FEL  
    FEL_AUTHORIZED = "FEL_AUTHORIZED"        # Autorizada por SAT
    FEL_REJECTED = "FEL_REJECTED"            # Rechazada por SAT
    ISSUED = "ISSUED"                        # Emitida oficialmente (con FEL)
    PAID = "PAID"                            # Pagada
    OVERDUE = "OVERDUE"                      # Vencida
    CANCELLED = "CANCELLED"                  # Anulada
    """)

def test_final_enum():
    """Test the final enum values"""
    
    print("\n🧪 Testing final enum values...")
    
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
                
                # Test all status transitions
                test_statuses = ["DRAFT", "FEL_PENDING", "FEL_AUTHORIZED", "ISSUED", "DRAFT"]
                
                for status in test_statuses:
                    print(f"Setting status to {status}...")
                    connection.execute(text("UPDATE invoices SET status = :status WHERE id = :id"), 
                                     {"status": status, "id": invoice_id})
                    
                    # Verify
                    result = connection.execute(text("SELECT status FROM invoices WHERE id = :id"), 
                                              {"id": invoice_id})
                    current_status = result.fetchone()[0]
                    print(f"✅ Status is: {current_status}")
        
        print("✅ Final enum test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Final enum test failed: {e}")
        return False

if __name__ == "__main__":
    success = final_enum_fix()
    if success:
        update_python_model()
        test_final_enum()

