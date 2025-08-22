#!/usr/bin/env python3
"""
Script para verificar que las órdenes se crearon correctamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.order_service import OrderService
from app.services.client_service import ClientService
from app.services.product_service import ProductService


def verify_orders():
    """Verificar que las órdenes se crearon correctamente"""
    
    print("🔍 Verificando órdenes creadas...")
    
    db = SessionLocal()
    order_service = OrderService()
    client_service = ClientService()
    product_service = ProductService()
    
    try:
        # Obtener todas las órdenes
        orders = order_service.get_orders(db)
        
        print(f"\n📋 Total de órdenes encontradas: {len(orders)}")
        
        if not orders:
            print("❌ No se encontraron órdenes")
            return
        
        # Mostrar detalles de cada orden
        for i, order in enumerate(orders, 1):
            print(f"\n📦 Orden #{i}")
            print(f"   🆔 ID: {order.id}")
            print(f"   📝 Número: {order.order_number}")
            print(f"   👤 Cliente ID: {order.client_id}")
            print(f"   📊 Estado: {order.status}")
            print(f"   💰 Total: ${order.total_amount:.2f}")
            print(f"   📅 Creada: {order.created_at}")
            if order.notes:
                print(f"   📝 Notas: {order.notes}")
            
            # Mostrar items de la orden
            if order.items:
                print(f"   📦 Items ({len(order.items)}):")
                for j, item in enumerate(order.items, 1):
                    print(f"      {j}. Producto ID: {item.product_id}, Cantidad: {item.quantity}, Precio: ${item.unit_price:.2f}, Total: ${item.total_price:.2f}")
            else:
                print("   ❌ No hay items en esta orden")
        
        # Mostrar estadísticas
        print(f"\n📊 Estadísticas:")
        
        # Órdenes por estado
        status_counts = {}
        total_amount = 0
        total_items = 0
        
        for order in orders:
            status = order.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_amount += order.total_amount
            total_items += len(order.items)
        
        print(f"   💰 Valor total de todas las órdenes: ${total_amount:.2f}")
        print(f"   📦 Total de items en todas las órdenes: {total_items}")
        print(f"   📊 Órdenes por estado:")
        for status, count in status_counts.items():
            print(f"      - {status}: {count}")
        
        # Verificar clientes
        print(f"\n👤 Verificando clientes...")
        clients = client_service.get_active_clients(db)
        print(f"   Total de clientes activos: {len(clients)}")
        
        # Verificar productos
        print(f"\n📦 Verificando productos...")
        products = product_service.get_active_products(db)
        print(f"   Total de productos activos: {len(products)}")
        
        # Mostrar productos con stock actualizado
        print(f"\n📦 Stock actual de productos:")
        for product in products:
            print(f"   - {product.name}: {product.stock} unidades")
        
        print(f"\n✅ Verificación completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    verify_orders() 