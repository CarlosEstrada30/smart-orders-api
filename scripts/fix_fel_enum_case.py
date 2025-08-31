#!/usr/bin/env python3
"""
Fix FEL enum case to be consistent (uppercase like existing values)
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import settings

def fix_fel_enum_case():
    """Fix FEL enum values to be uppercase like existing ones"""
    
    print("🔧 Fixing FEL enum case to uppercase...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            with connection.begin():
                # Check current enum values
                print("📋 Current enum values:")
                result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
                current_values = [row[0] for row in result.fetchall()]
                for value in current_values:
                    print(f"   - {value}")
                
                # Add uppercase versions of FEL values
                fel_values_upper = ['FEL_PENDING', 'FEL_AUTHORIZED', 'FEL_REJECTED']
                
                for value in fel_values_upper:
                    if value not in current_values:
                        print(f"Adding uppercase enum value: {value}")
                        connection.execute(text(f"ALTER TYPE invoicestatus ADD VALUE '{value}'"))
                    else:
                        print(f"✅ Enum value '{value}' already exists")
                
                # Show final state
                print("\n📋 Final enum values:")
                result = connection.execute(text("SELECT unnest(enum_range(NULL::invoicestatus)) AS enum_value;"))
                final_values = [row[0] for row in result.fetchall()]
                for value in final_values:
                    print(f"   - {value}")
        
        print("✅ FEL enum case fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing FEL enum case: {e}")
        return False

def update_model_to_uppercase():
    """Show what needs to be updated in the model"""
    
    print("\n📝 MODEL UPDATE REQUIRED:")
    print("Update app/models/invoice.py to use uppercase values:")
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

def test_uppercase_enum():
    """Test updating with uppercase values"""
    
    print("\n🧪 Testing uppercase enum values...")
    
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
                
                # Test sequence: DRAFT → FEL_PENDING → DRAFT
                test_sequence = [
                    ("DRAFT", "Setting to DRAFT"),
                    ("FEL_PENDING", "Setting to FEL_PENDING"), 
                    ("FEL_AUTHORIZED", "Setting to FEL_AUTHORIZED"),
                    ("DRAFT", "Resetting to DRAFT")
                ]
                
                for status, description in test_sequence:
                    print(f"{description}...")
                    connection.execute(text("UPDATE invoices SET status = :status WHERE id = :id"), 
                                     {"status": status, "id": invoice_id})
                    
                    # Verify
                    result = connection.execute(text("SELECT status FROM invoices WHERE id = :id"), 
                                              {"id": invoice_id})
                    current_status = result.fetchone()[0]
                    print(f"✅ Status is now: {current_status}")
        
        print("✅ Uppercase enum test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Uppercase enum test failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_fel_enum_case()
    if success:
        update_model_to_uppercase()
        test_uppercase_enum()

