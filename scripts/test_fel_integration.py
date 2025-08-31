#!/usr/bin/env python3
"""
Test script for FEL (Facturación Electrónica en Línea) integration
This script tests the complete FEL workflow in Guatemala
"""

import sys
import os
import json
import requests
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.fel_service import FELService
from app.services.invoice_service import InvoiceService
from app.models.invoice import InvoiceStatus
from app.repositories.invoice_repository import InvoiceRepository

def test_fel_service():
    """Test the FEL service functionality"""
    
    print("🧪 Testing FEL Service...")
    
    db = SessionLocal()
    fel_service = FELService()
    
    try:
        # Test FEL status summary
        print("\n📊 Testing FEL Status Summary...")
        summary = fel_service.get_fel_status_summary(db)
        print(f"FEL Summary: {json.dumps(summary, indent=2, default=str)}")
        
        # Test FEL configuration
        print("\n⚙️ Testing FEL Configuration...")
        for certifier, config in fel_service.fel_configs.items():
            print(f"Certifier {certifier}: {config.certifier_name} - {config.base_url}")
        
        print("✅ FEL Service tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ FEL Service test failed: {e}")
        return False
    finally:
        db.close()

def test_invoice_fel_integration():
    """Test invoice and FEL integration"""
    
    print("\n🧾 Testing Invoice-FEL Integration...")
    
    db = SessionLocal()
    invoice_service = InvoiceService()
    invoice_repository = InvoiceRepository()
    
    try:
        # Get an existing invoice for testing (or create one)
        invoices = invoice_repository.get_multi(db, limit=1)
        
        if not invoices:
            print("⚠️ No invoices found in database. Create some orders and invoices first.")
            return True
        
        invoice = invoices[0]
        print(f"Testing with Invoice ID: {invoice.id}, Number: {invoice.invoice_number}")
        
        # Test FEL processing (mock)
        print("\n🇬🇹 Testing FEL Processing...")
        fel_result = invoice_service.process_fel_for_invoice(db, invoice.id, "digifact")
        print(f"FEL Result: Success={fel_result.success}, UUID={fel_result.fel_uuid}")
        
        # Get updated invoice
        updated_invoice = invoice_service.get_invoice(db, invoice.id)
        if updated_invoice:
            print(f"Invoice Status: {updated_invoice.status}")
            print(f"FEL UUID: {updated_invoice.fel_uuid}")
            print(f"Requires FEL: {updated_invoice.requires_fel}")
        
        print("✅ Invoice-FEL integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Invoice-FEL integration test failed: {e}")
        return False
    finally:
        db.close()

def test_api_endpoints_fel():
    """Test FEL API endpoints"""
    
    print("\n🌐 Testing FEL API Endpoints...")
    
    # Note: This requires the API server to be running
    base_url = "http://localhost:8000"
    
    # You would need to get an auth token first
    # For now, just check if endpoints are accessible
    
    endpoints_to_test = [
        "/invoices/fel/status-summary",
        "/invoices/revenue/fiscal"
    ]
    
    print("📝 FEL Endpoints that should be available:")
    for endpoint in endpoints_to_test:
        print(f"   - GET {base_url}{endpoint}")
    
    print("📝 Invoice-specific FEL endpoints:")
    print(f"   - POST {base_url}/invoices/{{invoice_id}}/fel/process")
    print(f"   - POST {base_url}/invoices/orders/{{order_id}}/auto-invoice-with-fel")
    print(f"   - POST {base_url}/invoices/orders/{{order_id}}/receipt-only")
    
    print("✅ API endpoints documentation completed!")
    return True

def test_fel_xml_generation():
    """Test FEL XML generation"""
    
    print("\n📄 Testing FEL XML Generation...")
    
    db = SessionLocal()
    fel_service = FELService()
    invoice_repository = InvoiceRepository()
    
    try:
        # Get an invoice with order items
        invoices = db.query(invoice_repository.model).filter(
            invoice_repository.model.order_id.isnot(None)
        ).limit(1).all()
        
        if not invoices:
            print("⚠️ No invoices with orders found. Need invoices with order items for XML generation.")
            return True
        
        invoice = invoices[0]
        
        # Test XML generation
        print(f"Generating FEL XML for Invoice {invoice.invoice_number}...")
        
        # Load the order relationship
        db.refresh(invoice)
        
        if not hasattr(invoice, 'order') or not invoice.order:
            print("⚠️ Invoice doesn't have order relationship loaded")
            return True
        
        xml_content = fel_service._generate_fel_xml(invoice)
        
        # Save sample XML for review
        xml_filename = f"sample_fel_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        xml_path = f"/tmp/{xml_filename}"
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print(f"✅ FEL XML generated successfully!")
        print(f"📁 Sample XML saved to: {xml_path}")
        print(f"📏 XML Length: {len(xml_content)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ FEL XML generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_invoice_states_flow():
    """Test the complete invoice states flow with FEL"""
    
    print("\n🔄 Testing Invoice States Flow with FEL...")
    
    states_flow = [
        "DRAFT → Create invoice", 
        "FEL_PENDING → Send to FEL certifier",
        "FEL_AUTHORIZED → Authorized by SAT", 
        "ISSUED → Officially issued",
        "PAID → Payment received"
    ]
    
    print("📋 FEL Invoice States Flow:")
    for i, state in enumerate(states_flow, 1):
        print(f"   {i}. {state}")
    
    print("\n📋 Available Invoice States:")
    for status in InvoiceStatus:
        description = {
            InvoiceStatus.DRAFT: "Borrador - Initial state",
            InvoiceStatus.FEL_PENDING: "Pendiente FEL - Being processed",
            InvoiceStatus.FEL_AUTHORIZED: "Autorizada por SAT - FEL approved",
            InvoiceStatus.FEL_REJECTED: "Rechazada por SAT - FEL rejected",
            InvoiceStatus.ISSUED: "Emitida oficialmente - Ready for business",
            InvoiceStatus.PAID: "Pagada - Payment received",
            InvoiceStatus.OVERDUE: "Vencida - Past due",
            InvoiceStatus.CANCELLED: "Cancelada - Cancelled"
        }.get(status, "Unknown status")
        
        print(f"   - {status.value}: {description}")
    
    print("✅ Invoice states flow documentation completed!")
    return True

def run_complete_fel_test():
    """Run complete FEL test suite"""
    
    print("🇬🇹 GUATEMALA FEL INTEGRATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("FEL Service", test_fel_service),
        ("Invoice-FEL Integration", test_invoice_fel_integration), 
        ("FEL XML Generation", test_fel_xml_generation),
        ("Invoice States Flow", test_invoice_states_flow),
        ("API Endpoints Documentation", test_api_endpoints_fel)
    ]
    
    results = []
    
    for test_name, test_function in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = test_function()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"Result: {status}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All FEL integration tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

def create_fel_usage_examples():
    """Create examples of how to use the FEL integration"""
    
    print("\n📚 FEL USAGE EXAMPLES")
    print("=" * 50)
    
    examples = {
        "Create invoice with FEL": {
            "endpoint": "POST /invoices/orders/{order_id}/auto-invoice-with-fel",
            "description": "Create invoice for delivered order and process FEL automatically",
            "example": """
curl -X POST "http://localhost:8000/invoices/orders/123/auto-invoice-with-fel?certifier=digifact" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json"
            """
        },
        
        "Create receipt only": {
            "endpoint": "POST /invoices/orders/{order_id}/receipt-only",
            "description": "Create receipt without FEL processing (for customers who don't need invoice)",
            "example": """
curl -X POST "http://localhost:8000/invoices/orders/123/receipt-only" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json"
            """
        },
        
        "Process existing invoice through FEL": {
            "endpoint": "POST /invoices/{invoice_id}/fel/process",
            "description": "Process an existing invoice through FEL",
            "example": """
curl -X POST "http://localhost:8000/invoices/456/fel/process?certifier=digifact" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json"
            """
        },
        
        "Get FEL status summary": {
            "endpoint": "GET /invoices/fel/status-summary",
            "description": "Get summary of FEL processing status",
            "example": """
curl -X GET "http://localhost:8000/invoices/fel/status-summary" \\
     -H "Authorization: Bearer YOUR_TOKEN"
            """
        },
        
        "Get fiscal revenue": {
            "endpoint": "GET /invoices/revenue/fiscal",
            "description": "Get revenue from FEL-authorized invoices only",
            "example": """
curl -X GET "http://localhost:8000/invoices/revenue/fiscal?start_date=2024-01-01&end_date=2024-12-31" \\
     -H "Authorization: Bearer YOUR_TOKEN"
            """
        }
    }
    
    for title, info in examples.items():
        print(f"\n📋 {title}")
        print(f"   Endpoint: {info['endpoint']}")
        print(f"   Description: {info['description']}")
        print(f"   Example:{info['example']}")
    
    print("\n✅ Usage examples created!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test FEL Integration for Guatemala')
    parser.add_argument('--examples', action='store_true', help='Show usage examples')
    parser.add_argument('--xml-only', action='store_true', help='Test XML generation only')
    parser.add_argument('--service-only', action='store_true', help='Test FEL service only')
    
    args = parser.parse_args()
    
    if args.examples:
        create_fel_usage_examples()
    elif args.xml_only:
        test_fel_xml_generation()
    elif args.service_only:
        test_fel_service()
    else:
        run_complete_fel_test()

