"""
Fixtures y datos de prueba reutilizables.

Este módulo contiene datos de prueba que pueden ser reutilizados
en diferentes tests.
"""

import pytest
from datetime import datetime
from typing import Dict, Any


class TestDataFactory:
    """Factory para generar datos de prueba."""
    
    @staticmethod
    def create_user_data(**overrides) -> Dict[str, Any]:
        """Crear datos de usuario con posibles overrides."""
        base_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "name": "Test User",
            "role": "admin"
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_tenant_data(**overrides) -> Dict[str, Any]:
        """Crear datos de tenant con posibles overrides."""
        base_data = {
            "nombre": "Test Company",
            "subdominio": "testcompany"
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_product_data(**overrides) -> Dict[str, Any]:
        """Crear datos de producto con posibles overrides."""
        base_data = {
            "name": "Test Product",
            "description": "A test product description",
            "price": 19.99,
            "sku": "TEST001",
            "stock": 100,
            "is_active": True,
            "category": "Test Category"
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_client_data(**overrides) -> Dict[str, Any]:
        """Crear datos de cliente con posibles overrides."""
        base_data = {
            "name": "Test Client",
            "email": "client@test.com",
            "phone": "123456789",
            "address": "Test Address 123",
            "nit": "12345678-9"
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_order_data(client_id: int = None, **overrides) -> Dict[str, Any]:
        """Crear datos de orden con posibles overrides."""
        base_data = {
            "client_id": client_id or 1,
            "status": "pending",
            "total_amount": 100.00,
            "notes": "Test order notes",
            "delivery_date": datetime.now().isoformat()
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_order_item_data(order_id: int = None, product_id: int = None, **overrides) -> Dict[str, Any]:
        """Crear datos de item de orden con posibles overrides."""
        base_data = {
            "order_id": order_id or 1,
            "product_id": product_id or 1,
            "quantity": 2,
            "unit_price": 25.00,
            "total_price": 50.00
        }
        base_data.update(overrides)
        return base_data


# Fixtures adicionales usando el factory
@pytest.fixture
def admin_user_data():
    """Datos de usuario administrador."""
    return TestDataFactory.create_user_data(role="admin", email="admin@test.com")


@pytest.fixture
def regular_user_data():
    """Datos de usuario regular."""
    return TestDataFactory.create_user_data(role="user", email="user@test.com")


@pytest.fixture
def premium_client_data():
    """Datos de cliente premium."""
    return TestDataFactory.create_client_data(
        name="Premium Client",
        email="premium@client.com",
        phone="987654321"
    )


@pytest.fixture
def bulk_products_data():
    """Lista de productos para pruebas masivas."""
    return [
        TestDataFactory.create_product_data(
            name=f"Product {i}",
            sku=f"PROD{i:03d}",
            price=10.0 * i
        ) for i in range(1, 6)
    ]


@pytest.fixture
def sample_order_with_items():
    """Orden completa con items de muestra."""
    return {
        "order": TestDataFactory.create_order_data(total_amount=150.00),
        "items": [
            TestDataFactory.create_order_item_data(quantity=2, unit_price=25.00),
            TestDataFactory.create_order_item_data(quantity=3, unit_price=33.33),
            TestDataFactory.create_order_item_data(quantity=1, unit_price=16.67),
        ]
    }


# Mock objects para casos específicos
class MockSettings:
    """Mock object para configuraciones de la aplicación."""
    
    def __init__(self, **kwargs):
        defaults = {
            "company_name": "Test Company",
            "business_name": "Test Business S.A",
            "nit": "123456789",
            "address": "Test Address 123",
            "phone": "123456789",
            "email": "test@company.com",
            "website": "https://test.com",
            "logo_url": None
        }
        defaults.update(kwargs)
        
        for key, value in defaults.items():
            setattr(self, key, value)


class MockProduct:
    """Mock object para productos."""
    
    def __init__(self, name: str, description: str = "", price: float = 0.0, sku: str = ""):
        self.name = name
        self.description = description
        self.price = price
        self.sku = sku


class MockOrderItem:
    """Mock object para items de orden."""
    
    def __init__(self, product: MockProduct, quantity: int, unit_price: float):
        self.product = product
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = quantity * unit_price


class MockClient:
    """Mock object para clientes."""
    
    def __init__(self, name: str, email: str = "", phone: str = "", address: str = ""):
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address


class MockOrder:
    """Mock object para órdenes."""
    
    def __init__(self, order_number: str, client: MockClient, items: list):
        self.order_number = order_number
        self.client = client
        self.items = items
        self.total_amount = sum(item.total_price for item in items)
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
