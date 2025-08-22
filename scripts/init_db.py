#!/usr/bin/env python3
"""
Script para inicializar la base de datos con datos de ejemplo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, User, Client, Product, Order, OrderItem
from app.models.order import OrderStatus
from app.services.user_service import UserService
from app.services.client_service import ClientService
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from app.schemas.user import UserCreate
from app.schemas.client import ClientCreate
from app.schemas.product import ProductCreate
from app.schemas.order import OrderCreate, OrderItemCreate


def init_db():
    """Inicializar la base de datos con datos de ejemplo"""
    
    print("🚀 Iniciando configuración de la base de datos...")
    
    # Crear tablas
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas correctamente")
    
    db = SessionLocal()
    
    try:
        # Inicializar servicios
        user_service = UserService()
        client_service = ClientService()
        product_service = ProductService()
        order_service = OrderService()
        
        # Crear usuarios de ejemplo
        print("\n👥 Creando usuarios de ejemplo...")
        
        admin_user = UserCreate(
            email="admin@example.com",
            username="admin",
            full_name="Administrador",
            password="admin123",
            is_superuser=True
        )
        
        user1 = UserCreate(
            email="user1@example.com",
            username="user1",
            full_name="Usuario Ejemplo 1",
            password="user123"
        )
        
        try:
            user_service.create_user(db, admin_user)
            print("✅ Usuario admin creado")
        except ValueError as e:
            print(f"⚠️  Usuario admin ya existe: {e}")
            
        try:
            user_service.create_user(db, user1)
            print("✅ Usuario user1 creado")
        except ValueError as e:
            print(f"⚠️  Usuario user1 ya existe: {e}")
        
        # Crear clientes de ejemplo
        print("\n👤 Creando clientes de ejemplo...")
        
        clients_data = [
            {
                "name": "Juan Pérez",
                "email": "juan.perez@email.com",
                "phone": "+1234567890",
                "address": "Calle Principal 123, Ciudad"
            },
            {
                "name": "María García",
                "email": "maria.garcia@email.com",
                "phone": "+0987654321",
                "address": "Avenida Central 456, Ciudad"
            },
            {
                "name": "Carlos López",
                "email": "carlos.lopez@email.com",
                "phone": "+1122334455",
                "address": "Plaza Mayor 789, Ciudad"
            }
        ]
        
        created_clients = []
        for client_data in clients_data:
            try:
                client = ClientCreate(**client_data)
                created_client = client_service.create_client(db, client)
                created_clients.append(created_client)
                print(f"✅ Cliente {client_data['name']} creado")
            except ValueError as e:
                print(f"⚠️  Cliente {client_data['name']} ya existe: {e}")
                # Obtener el cliente existente
                existing_client = client_service.get_client_by_email(db, client_data['email'])
                if existing_client:
                    created_clients.append(existing_client)
        
        # Crear productos de ejemplo
        print("\n📦 Creando productos de ejemplo...")
        
        products_data = [
            {
                "name": "Laptop Dell XPS 13",
                "description": "Laptop ultrabook de 13 pulgadas con procesador Intel i7",
                "price": 1299.99,
                "stock": 15,
                "sku": "DELL-XPS13-001"
            },
            {
                "name": "Mouse Logitech MX Master 3",
                "description": "Mouse inalámbrico ergonómico para productividad",
                "price": 99.99,
                "stock": 50,
                "sku": "LOG-MX3-001"
            },
            {
                "name": "Monitor Samsung 27\" 4K",
                "description": "Monitor de 27 pulgadas con resolución 4K UHD",
                "price": 399.99,
                "stock": 8,
                "sku": "SAM-27-4K-001"
            },
            {
                "name": "Teclado Mecánico Corsair K70",
                "description": "Teclado mecánico RGB con switches Cherry MX",
                "price": 149.99,
                "stock": 25,
                "sku": "COR-K70-001"
            },
            {
                "name": "Auriculares Sony WH-1000XM4",
                "description": "Auriculares inalámbricos con cancelación de ruido",
                "price": 349.99,
                "stock": 12,
                "sku": "SON-WH4-001"
            }
        ]
        
        created_products = []
        for product_data in products_data:
            try:
                product = ProductCreate(**product_data)
                created_product = product_service.create_product(db, product)
                created_products.append(created_product)
                print(f"✅ Producto {product_data['name']} creado")
            except ValueError as e:
                print(f"⚠️  Producto {product_data['name']} ya existe: {e}")
                # Obtener el producto existente
                existing_product = product_service.get_product_by_sku(db, product_data['sku'])
                if existing_product:
                    created_products.append(existing_product)
        
        # Crear órdenes de ejemplo
        print("\n📋 Creando órdenes de ejemplo...")
        
        # Obtener todos los clientes y productos activos
        all_clients = client_service.get_active_clients(db)
        all_products = product_service.get_active_products(db)
        
        if not all_clients:
            print("❌ No hay clientes activos para crear órdenes")
            return
        
        if not all_products:
            print("❌ No hay productos activos para crear órdenes")
            return
        
        # Crear órdenes usando los IDs reales de clientes y productos
        orders_data = [
            {
                "client_id": all_clients[0].id,  # Juan Pérez
                "status": OrderStatus.CONFIRMED,
                "notes": "Entrega urgente para oficina",
                "items": [
                    {
                        "product_id": all_products[0].id,  # Laptop Dell XPS 13
                        "quantity": 2,
                        "unit_price": all_products[0].price
                    },
                    {
                        "product_id": all_products[1].id,  # Mouse Logitech MX Master 3
                        "quantity": 2,
                        "unit_price": all_products[1].price
                    }
                ]
            },
            {
                "client_id": all_clients[1].id,  # María García
                "status": OrderStatus.IN_PROGRESS,
                "notes": "Configuración especial requerida",
                "items": [
                    {
                        "product_id": all_products[2].id,  # Monitor Samsung 27" 4K
                        "quantity": 1,
                        "unit_price": all_products[2].price
                    },
                    {
                        "product_id": all_products[3].id,  # Teclado Mecánico Corsair K70
                        "quantity": 1,
                        "unit_price": all_products[3].price
                    },
                    {
                        "product_id": all_products[4].id,  # Auriculares Sony WH-1000XM4
                        "quantity": 1,
                        "unit_price": all_products[4].price
                    }
                ]
            },
            {
                "client_id": all_clients[2].id,  # Carlos López
                "status": OrderStatus.PENDING,
                "notes": "Pedido para regalo de cumpleaños",
                "items": [
                    {
                        "product_id": all_products[1].id,  # Mouse Logitech MX Master 3
                        "quantity": 1,
                        "unit_price": all_products[1].price
                    },
                    {
                        "product_id": all_products[4].id,  # Auriculares Sony WH-1000XM4
                        "quantity": 1,
                        "unit_price": all_products[4].price
                    }
                ]
            },
            {
                "client_id": all_clients[0].id,  # Juan Pérez (segunda orden)
                "status": OrderStatus.DELIVERED,
                "notes": "Pedido completado satisfactoriamente",
                "items": [
                    {
                        "product_id": all_products[3].id,  # Teclado Mecánico Corsair K70
                        "quantity": 1,
                        "unit_price": all_products[3].price
                    }
                ]
            }
        ]
        
        for i, order_data in enumerate(orders_data, 1):
            try:
                # Convertir los items a OrderItemCreate
                order_items = [OrderItemCreate(**item) for item in order_data["items"]]
                
                order_create = OrderCreate(
                    client_id=order_data["client_id"],
                    status=order_data["status"],
                    notes=order_data["notes"],
                    items=order_items
                )
                
                created_order = order_service.create_order(db, order_create)
                print(f"✅ Orden {i} creada - Cliente ID: {order_data['client_id']}, Estado: {order_data['status']}")
                print(f"   📦 Items: {len(order_items)} productos, Total: ${created_order.total_amount:.2f}")
                
            except ValueError as e:
                print(f"⚠️  Error al crear orden {i}: {e}")
            except Exception as e:
                print(f"❌ Error inesperado al crear orden {i}: {e}")
        
        print("\n🎉 ¡Base de datos inicializada correctamente!")
        print("\n📋 Datos de acceso:")
        print("   Admin: admin@example.com / admin123")
        print("   Usuario: user1@example.com / user123")
        print("\n📊 Resumen de datos creados:")
        print(f"   👥 Usuarios: 2")
        print(f"   👤 Clientes: {len(created_clients)}")
        print(f"   📦 Productos: {len(created_products)}")
        print(f"   📋 Órdenes: {len(orders_data)}")
        print("\n🌐 La API estará disponible en: http://localhost:8000")
        print("📚 Documentación: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db() 