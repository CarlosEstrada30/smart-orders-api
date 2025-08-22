#!/usr/bin/env python3
"""
Script para probar la estructura de respuesta de órdenes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.order_service import OrderService


def test_order_response():
    """Probar la estructura de respuesta de órdenes"""
    
    print("🔍 Probando estructura de respuesta de órdenes...")
    
    db = SessionLocal()
    order_service = OrderService()
    
    try:
        # Obtener todas las órdenes
        orders = order_service.get_orders(db, limit=2)
        
        print(f"\n📋 Órdenes obtenidas: {len(orders)}")
        
        if not orders:
            print("❌ No se encontraron órdenes")
            return
        
        # Verificar la primera orden
        order = orders[0]
        print(f"\n📦 Verificando orden ID: {order.id}")
        
        # Verificar cliente
        if order.client:
            print(f"✅ Cliente encontrado:")
            print(f"   👤 Nombre: {order.client.name}")
            print(f"   📧 Email: {order.client.email}")
            print(f"   📞 Teléfono: {order.client.phone}")
            print(f"   📍 Dirección: {order.client.address}")
        else:
            print("❌ Cliente no encontrado")
        
        # Verificar items
        print(f"\n📦 Items ({len(order.items)}):")
        for i, item in enumerate(order.items, 1):
            print(f"   {i}. Producto: {item.product_name or 'Sin nombre'}")
            print(f"      SKU: {item.product_sku or 'Sin SKU'}")
            print(f"      Descripción: {item.product_description or 'Sin descripción'}")
            print(f"      Cantidad: {item.quantity}")
            print(f"      Precio: ${item.unit_price:.2f}")
            print(f"      Total: ${item.total_price:.2f}")
            
            if not item.product_name:
                print(f"      ⚠️  Producto sin nombre (ID: {item.product_id})")
        
        # Verificar estructura completa
        print(f"\n📊 Estructura completa de la orden:")
        print(f"   🆔 ID: {order.id}")
        print(f"   📝 Número: {order.order_number}")
        print(f"   👤 Cliente ID: {order.client_id}")
        print(f"   📊 Estado: {order.status}")
        print(f"   💰 Total: ${order.total_amount:.2f}")
        print(f"   📅 Creada: {order.created_at}")
        if order.notes:
            print(f"   📝 Notas: {order.notes}")
        
        print(f"\n✅ Verificación completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_order_response() 