#!/usr/bin/env python3
"""
Script de prueba para el generador de comprobantes mejorado
"""

# Agregar el path del proyecto al PYTHONPATH
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar variables de entorno mínimas para la prueba
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

try:
    # Imports
    from app.services.compact_receipt_generator import CompactReceiptGenerator
    from datetime import datetime
    
    # Crear datos de prueba simulados
    class MockProduct:
        def __init__(self, name, description):
            self.name = name
            self.description = description
    
    class MockOrderItem:
        def __init__(self, product, quantity, unit_price):
            self.product = product
            self.quantity = quantity
            self.unit_price = unit_price
            self.total_price = quantity * unit_price
    
    class MockClient:
        def __init__(self, name, email, phone, address):
            self.name = name
            self.email = email
            self.phone = phone
            self.address = address
    
    class MockOrder:
        def __init__(self, order_number, client, items):
            self.order_number = order_number
            self.client = client
            self.items = items
            self.total_amount = sum(item.total_price for item in items)
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
    
    class MockSettings:
        def __init__(self):
            self.company_name = "My APP"
            self.business_name = "Publica S.A"
            self.nit = "354632156312"
            self.address = "Guatemala"
            self.phone = "41668878"
            self.email = "smartorders@gmail.com"
            self.website = None
            self.logo_url = None  # Sin logo para esta prueba
    
    # Crear datos de prueba similares a la imagen
    settings = MockSettings()
    
    client = MockClient(
        name="David Morales",
        email="david@gmail.com",
        phone="656123212",
        address="Guatemala"
    )
    
    items = [
        MockOrderItem(MockProduct("Queso Crema HOY", "Descripción del queso"), 3, 5.00),
        MockOrderItem(MockProduct("Crema Pura", "Crema de alta calidad"), 3, 150.00),
        MockOrderItem(MockProduct("Crema 12 oz", "Presentación de 12 onzas"), 1, 60.00),
    ]
    
    order = MockOrder("ORD-9OF9E6B9", client, items)
    
    # Generar PDF de prueba
    generator = CompactReceiptGenerator()
    
    output_path = "test_improved_receipt.pdf"
    result = generator.generate_order_receipt(order, settings, output_path)
    
    print(f"✅ PDF mejorado generado exitosamente: {result}")
    print(f"📄 Total del pedido: Q {order.total_amount:,.2f}")
    print(f"📦 {len(items)} productos, {sum(item.quantity for item in items)} unidades totales")
    print(f"🎯 Archivo guardado como: {output_path}")
    print("\n🔍 Mejoras implementadas:")
    print("  - Layout limpio sin tabla azul de fondo")
    print("  - Información mejor alineada")
    print("  - Formato de precios consistente (Q X.XX)")
    print("  - Headers con línea verde simple")
    print("  - Espaciado uniforme")
    
except ImportError as e:
    print(f"❌ Error de import: {e}")
    print("Asegúrate de que todas las dependencias están instaladas con: pipenv install")
except Exception as e:
    print(f"❌ Error al generar el PDF: {e}")
    import traceback
    traceback.print_exc()
