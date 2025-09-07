#!/usr/bin/env python3
"""
Script de prueba para el endpoint de reporte PDF de órdenes
Utiliza pipenv para ejecutarse en el entorno virtual del proyecto
"""

import requests
import json
from datetime import datetime, timedelta
import os
import sys

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "default"  # or your tenant ID

# Test credentials - adjust based on your test data
TEST_USERNAME = "admin"  # or your test user
TEST_PASSWORD = "admin123"  # or your test password

def authenticate():
    """Authenticate and get access token"""
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    print("🔐 Authenticating...")
    response = requests.post(f"{API_BASE_URL}/auth/login", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    token_data = response.json()
    print(f"✅ Authentication successful")
    return token_data.get("access_token")

def test_orders_pdf_report(token, filters=None):
    """Test the orders PDF report endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID
    }
    
    # Build query parameters
    params = {}
    if filters:
        params.update(filters)
    
    filter_desc = ", ".join([f"{k}={v}" for k, v in params.items()]) if params else "sin filtros"
    print(f"📊 Testing PDF report endpoint with filters: {filter_desc}")
    
    response = requests.get(
        f"{API_BASE_URL}/orders/report/pdf",
        headers=headers,
        params=params
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        # Save PDF to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filter_suffix = "_".join([f"{k}-{v}" for k, v in params.items()]) if params else "all"
        filename = f"test_orders_report_{filter_suffix}_{timestamp}.pdf"
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"✅ PDF generated successfully!")
        print(f"📄 File saved as: {filename}")
        print(f"📏 File size: {file_size:,} bytes")
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if content_type == 'application/pdf':
            print("✅ Correct content type: application/pdf")
        else:
            print(f"⚠️  Unexpected content type: {content_type}")
            
        return True
        
    elif response.status_code == 404:
        print("ℹ️  No orders found with specified filters")
        return False
        
    else:
        print(f"❌ Error: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error details: {error_data.get('detail', 'Unknown error')}")
        except:
            print(f"Raw response: {response.text}")
        return False

def test_various_filters(token):
    """Test the endpoint with various filter combinations"""
    test_cases = [
        # Test case 1: No filters (all orders)
        {"description": "All orders", "filters": {}},
        
        # Test case 2: Filter by status
        {"description": "Pending orders", "filters": {"status_filter": "pending"}},
        {"description": "Delivered orders", "filters": {"status_filter": "delivered"}},
        
        # Test case 3: Filter by date range (last 30 days)
        {
            "description": "Last 30 days", 
            "filters": {
                "date_from": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            }
        },
        
        # Test case 4: Filter by date range (specific range)
        {
            "description": "Last week", 
            "filters": {
                "date_from": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                "date_to": datetime.now().strftime('%Y-%m-%d')
            }
        },
        
        # Test case 5: Combined filters
        {
            "description": "Confirmed orders from last 15 days", 
            "filters": {
                "status_filter": "confirmed",
                "date_from": (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
            }
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 Test Case {i}: {test_case['description']}")
        print('='*60)
        
        success = test_orders_pdf_report(token, test_case['filters'])
        if success:
            success_count += 1
        
        print()  # Empty line for readability
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {success_count}/{len(test_cases)} tests generated PDFs successfully")
    print('='*60)

def check_orders_exist(token):
    """Check if there are orders in the system"""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID
    }
    
    print("🔍 Checking if orders exist in the system...")
    response = requests.get(f"{API_BASE_URL}/orders/", headers=headers, params={"limit": 5})
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and 'items' in data:
            orders = data['items']
        else:
            orders = data
            
        print(f"✅ Found {len(orders)} orders (showing first 5)")
        for order in orders[:3]:  # Show first 3
            print(f"  - Order {order['order_number']}: {order['status']} (Client: {order.get('client', {}).get('name', 'N/A')})")
        
        return len(orders) > 0
    else:
        print(f"❌ Error checking orders: {response.status_code}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Orders PDF Report Test")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Username: {TEST_USERNAME}")
    print()
    
    # Authenticate
    token = authenticate()
    if not token:
        print("❌ Cannot proceed without authentication")
        return False
    
    print()
    
    # Check if orders exist
    if not check_orders_exist(token):
        print("⚠️  No orders found. Please create some test orders first.")
        return False
    
    print()
    
    # Test various filters
    test_various_filters(token)
    
    print("\n🎉 Test completed!")
    print("📝 Check the generated PDF files to verify the layout and content.")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
