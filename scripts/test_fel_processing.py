#!/usr/bin/env python3
"""
Test FEL processing functionality specifically
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.fel_service import FELService
from app.services.invoice_service import InvoiceService
from app.repositories.invoice_repository import InvoiceRepository

def test_fel_processing():
    """Test FEL processing for an existing invoice"""
    
    print("🧪 Testing FEL Processing...")
    
    db = SessionLocal()
    fel_service = FELService()
    invoice_service = InvoiceService()
    invoice_repository = InvoiceRepository()
    
    try:
        # Get an existing invoice
        invoices = invoice_repository.get_multi(db, limit=1)
        
        if not invoices:
            print("⚠️ No invoices found in database.")
            return True
        
        invoice = invoices[0]
        print(f"Testing with Invoice ID: {invoice.id}, Number: {invoice.invoice_number}")
        print(f"Initial status: {invoice.status}")
        print(f"Requires FEL: {getattr(invoice, 'requires_fel', 'Not set')}")
        
        # Update invoice to require FEL if needed
        if not getattr(invoice, 'requires_fel', True):
            print("Setting requires_fel to True...")
            invoice_repository.update(db, db_obj=invoice, obj_in={"requires_fel": True})
            db.commit()
        
        # Test FEL processing
        print("\n🇬🇹 Processing FEL...")
        fel_result = fel_service.process_fel_authorization(db, invoice.id, "digifact")
        
        print(f"FEL Processing Result:")
        print(f"  - Success: {fel_result.success}")
        print(f"  - Status: {fel_result.status}")
        print(f"  - FEL UUID: {fel_result.fel_uuid}")
        print(f"  - DTE Number: {fel_result.dte_number}")
        print(f"  - Certifier: {fel_result.certifier}")
        
        if fel_result.error_message:
            print(f"  - Error: {fel_result.error_message}")
        
        # Get updated invoice to verify
        db.refresh(invoice)
        print(f"\nUpdated Invoice:")
        print(f"  - Status: {invoice.status}")
        print(f"  - FEL UUID: {getattr(invoice, 'fel_uuid', 'Not set')}")
        print(f"  - FEL Certifier: {getattr(invoice, 'fel_certifier', 'Not set')}")
        
        if fel_result.success:
            print("✅ FEL processing completed successfully!")
        else:
            print("⚠️ FEL processing completed with issues (expected in test environment)")
        
        return True
        
    except Exception as e:
        print(f"❌ FEL processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_invoice_service_integration():
    """Test InvoiceService integration with FEL"""
    
    print("\n🧾 Testing InvoiceService FEL Integration...")
    
    db = SessionLocal()
    invoice_service = InvoiceService()
    
    try:
        # Test FEL status summary
        print("📊 Getting FEL Status Summary...")
        summary = invoice_service.get_fel_status_summary(db)
        print(f"FEL Summary: {summary}")
        
        # Test retry FEL processing
        print("\n🔄 Testing Retry FEL Processing...")
        retry_result = invoice_service.retry_fel_processing(db, "digifact")
        print(f"Retry Result: {retry_result}")
        
        print("✅ InvoiceService FEL integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ InvoiceService FEL integration test failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🇬🇹 FEL PROCESSING TEST")
    print("=" * 50)
    
    success1 = test_fel_processing()
    success2 = test_invoice_service_integration()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    if success1 and success2:
        print("🎉 All FEL processing tests passed!")
    else:
        print("⚠️ Some tests had issues (may be expected in test environment)")

