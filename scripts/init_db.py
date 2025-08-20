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
from app.services.user_service import UserService
from app.services.client_service import ClientService
from app.services.product_service import ProductService
from app.schemas.user import UserCreate
from app.schemas.client import ClientCreate
from app.schemas.product import ProductCreate


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
        
        for client_data in clients_data:
            try:
                client = ClientCreate(**client_data)
                client_service.create_client(db, client)
                print(f"✅ Cliente {client_data['name']} creado")
            except ValueError as e:
                print(f"⚠️  Cliente {client_data['name']} ya existe: {e}")
        
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
        
        for product_data in products_data:
            try:
                product = ProductCreate(**product_data)
                product_service.create_product(db, product)
                print(f"✅ Producto {product_data['name']} creado")
            except ValueError as e:
                print(f"⚠️  Producto {product_data['name']} ya existe: {e}")
        
        print("\n🎉 ¡Base de datos inicializada correctamente!")
        print("\n📋 Datos de acceso:")
        print("   Admin: admin@example.com / admin123")
        print("   Usuario: user1@example.com / user123")
        print("\n🌐 La API estará disponible en: http://localhost:8000")
        print("📚 Documentación: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db() 