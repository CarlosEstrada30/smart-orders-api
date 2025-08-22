#!/usr/bin/env python3
"""
Script para probar el endpoint de órdenes de la API
"""

import requests
import json
import time

# Configuración de la API
BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
ORDERS_URL = f"{BASE_URL}/orders"

def test_orders_api():
    """Probar el endpoint de órdenes de la API"""
    
    print("🌐 Probando endpoint de órdenes de la API...")
    
    # 1. Login para obtener token
    print("\n1️⃣ Haciendo login...")
    
    login_data = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"✅ Login exitoso. Token: {access_token[:50]}...")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 2. Obtener todas las órdenes
            print("\n2️⃣ Obteniendo todas las órdenes...")
            
            orders_response = requests.get(ORDERS_URL, headers=headers)
            
            if orders_response.status_code == 200:
                orders = orders_response.json()
                print(f"✅ Órdenes obtenidas: {len(orders)} órdenes")
                
                # 3. Verificar estructura de respuesta
                print("\n3️⃣ Verificando estructura de respuesta...")
                
                for i, order in enumerate(orders, 1):
                    print(f"\n📦 Orden #{i}")
                    print(f"   🆔 ID: {order.get('id')}")
                    print(f"   📝 Número: {order.get('order_number')}")
                    print(f"   📊 Estado: {order.get('status')}")
                    print(f"   💰 Total: ${order.get('total_amount', 0):.2f}")
                    
                    # Verificar cliente
                    client = order.get('client')
                    if client:
                        print(f"   👤 Cliente: {client.get('name')} ({client.get('email')})")
                        print(f"      📞 Teléfono: {client.get('phone')}")
                        print(f"      📍 Dirección: {client.get('address')}")
                    else:
                        print("   ❌ Cliente no encontrado en la respuesta")
                    
                    # Verificar items
                    items = order.get('items', [])
                    print(f"   📦 Items ({len(items)}):")
                    
                    for j, item in enumerate(items, 1):
                        product_name = item.get('product_name')
                        product_sku = item.get('product_sku')
                        quantity = item.get('quantity')
                        unit_price = item.get('unit_price')
                        total_price = item.get('total_price')
                        
                        print(f"      {j}. {product_name or 'Sin nombre'} (SKU: {product_sku or 'Sin SKU'})")
                        print(f"         Cantidad: {quantity}, Precio: ${unit_price:.2f}, Total: ${total_price:.2f}")
                        
                        if not product_name:
                            print(f"         ⚠️  Producto sin nombre (ID: {item.get('product_id')})")
                
                # 4. Obtener una orden específica
                if orders:
                    print(f"\n4️⃣ Obteniendo orden específica (ID: {orders[0]['id']})...")
                    
                    order_id = orders[0]['id']
                    specific_order_response = requests.get(f"{ORDERS_URL}/{order_id}", headers=headers)
                    
                    if specific_order_response.status_code == 200:
                        specific_order = specific_order_response.json()
                        print(f"✅ Orden específica obtenida")
                        print(f"   📝 Número: {specific_order.get('order_number')}")
                        print(f"   👤 Cliente: {specific_order.get('client', {}).get('name', 'No encontrado')}")
                        print(f"   📦 Items: {len(specific_order.get('items', []))}")
                    else:
                        print(f"❌ Error al obtener orden específica: {specific_order_response.status_code}")
                
                # 5. Probar filtro por estado
                print(f"\n5️⃣ Probando filtro por estado...")
                
                status_filter_response = requests.get(f"{ORDERS_URL}/?status_filter=pending", headers=headers)
                
                if status_filter_response.status_code == 200:
                    pending_orders = status_filter_response.json()
                    print(f"✅ Órdenes pendientes obtenidas: {len(pending_orders)}")
                else:
                    print(f"❌ Error al filtrar por estado: {status_filter_response.status_code}")
                
            else:
                print(f"❌ Error al obtener órdenes: {orders_response.status_code}")
                print(f"Respuesta: {orders_response.text}")
                
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar a la API. Asegúrate de que esté ejecutándose en http://localhost:8000")
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
    
    print("\n🎉 ¡Pruebas de API de órdenes completadas!")


if __name__ == "__main__":
    test_orders_api() 