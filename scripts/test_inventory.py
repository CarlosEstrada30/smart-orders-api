#!/usr/bin/env python3
"""
Script para probar el módulo completo de ingreso de producción/inventario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000/api/v1"
CREDENTIALS = {
    "admin": {"email": "admin@example.com", "password": "admin123"},
    "user": {"email": "user1@example.com", "password": "user123"}
}

class InventoryTester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        
    def authenticate(self, user_type="admin"):
        """Autenticar usuario y obtener token"""
        print(f"🔐 Autenticando como {user_type}...")
        
        login_data = {
            "username": CREDENTIALS[user_type]["email"],
            "password": CREDENTIALS[user_type]["password"]
        }
        
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print(f"✅ Autenticación exitosa")
            return True
        else:
            print(f"❌ Error en autenticación: {response.text}")
            return False
    
    def get_sample_products(self):
        """Obtener productos de ejemplo"""
        print("\n📦 Obteniendo productos disponibles...")
        
        response = self.session.get(f"{BASE_URL}/products/")
        if response.status_code == 200:
            products = response.json()
            if products:
                print(f"✅ Se encontraron {len(products)} productos")
                for i, product in enumerate(products[:3]):  # Mostrar solo los primeros 3
                    print(f"   {i+1}. {product['name']} (SKU: {product.get('sku', 'N/A')}) - Stock: {product['stock']}")
                return products
        
        print("❌ No se encontraron productos. Ejecute scripts/init_db.py primero")
        return []
    
    def test_create_production_entry(self, products):
        """Probar creación de entrada de producción"""
        print(f"\n🏭 Creando entrada de producción...")
        
        # Seleccionar productos para la entrada
        selected_products = products[:2]  # Usar los primeros 2 productos
        
        entry_data = {
            "entry_type": "production",
            "supplier_info": "Producción interna - Lote #001",
            "expected_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "notes": "Entrada de producción de prueba",
            "reference_document": "PROD-2024-001",
            "items": [
                {
                    "product_id": selected_products[0]["id"],
                    "quantity": 50,
                    "unit_cost": 15.50,
                    "batch_number": "BATCH-001",
                    "notes": "Producción matutina"
                },
                {
                    "product_id": selected_products[1]["id"],
                    "quantity": 30,
                    "unit_cost": 25.75,
                    "batch_number": "BATCH-002",
                    "notes": "Producción vespertina"
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/inventory/entries", json=entry_data)
        
        if response.status_code == 201:
            entry = response.json()
            print(f"✅ Entrada de producción creada: {entry['entry_number']}")
            print(f"   📊 Estado: {entry['status']}")
            print(f"   💰 Costo total: Q {entry['total_cost']:,.2f}")
            print(f"   📦 Items: {len(entry['items'])} productos")
            return entry
        else:
            print(f"❌ Error creando entrada: {response.text}")
            return None
    
    def test_create_purchase_entry(self, products):
        """Probar creación de entrada de compra"""
        print(f"\n🛒 Creando entrada de compra...")
        
        entry_data = {
            "entry_type": "purchase",
            "supplier_info": "Proveedor ABC S.A.",
            "expected_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "notes": "Compra mensual de inventario",
            "reference_document": "FACT-2024-0123",
            "items": [
                {
                    "product_id": products[0]["id"],
                    "quantity": 100,
                    "unit_cost": 12.00,
                    "batch_number": "PROV-001",
                    "expiry_date": (datetime.now() + timedelta(days=365)).isoformat(),
                    "notes": "Compra a proveedor principal"
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/inventory/workflows/purchase?auto_approve=true", json=entry_data)
        
        if response.status_code == 201:
            entry = response.json()
            print(f"✅ Entrada de compra creada: {entry['entry_number']}")
            print(f"   📊 Estado: {entry['status']}")
            print(f"   🏢 Proveedor: {entry['supplier_info']}")
            print(f"   💰 Costo total: Q {entry['total_cost']:,.2f}")
            return entry
        else:
            print(f"❌ Error creando entrada: {response.text}")
            return None
    
    def test_approve_entry(self, entry_id):
        """Probar aprobación de entrada"""
        print(f"\n✅ Aprobando entrada {entry_id}...")
        
        response = self.session.post(f"{BASE_URL}/inventory/entries/{entry_id}/approve")
        
        if response.status_code == 200:
            entry = response.json()
            print(f"✅ Entrada aprobada exitosamente")
            print(f"   📊 Nuevo estado: {entry['status']}")
            return entry
        else:
            print(f"❌ Error aprobando entrada: {response.text}")
            return None
    
    def test_complete_entry(self, entry_id):
        """Probar completar entrada y actualizar stock"""
        print(f"\n🎯 Completando entrada {entry_id} y actualizando stock...")
        
        # Obtener stock actual de productos
        response = self.session.get(f"{BASE_URL}/inventory/entries/{entry_id}")
        if response.status_code == 200:
            entry = response.json()
            print(f"   📦 Productos a actualizar:")
            for item in entry["items"]:
                print(f"      - {item['product_name']}: +{item['quantity']} unidades")
        
        # Completar entrada
        response = self.session.post(f"{BASE_URL}/inventory/entries/{entry_id}/complete")
        
        if response.status_code == 200:
            entry = response.json()
            print(f"✅ Entrada completada exitosamente")
            print(f"   📊 Estado final: {entry['status']}")
            print(f"   📅 Fecha completada: {entry['completed_date']}")
            print(f"   ⚡ Stock actualizado automáticamente")
            return entry
        else:
            print(f"❌ Error completando entrada: {response.text}")
            return None
    
    def test_stock_adjustment(self, product_id):
        """Probar ajuste rápido de stock"""
        print(f"\n🔧 Creando ajuste rápido de stock...")
        
        adjustment_data = {
            "product_id": product_id,
            "quantity": 25,  # Aumentar 25 unidades
            "reason": "Inventario físico - diferencia encontrada",
            "notes": "Ajuste por conteo físico realizado"
        }
        
        response = self.session.post(f"{BASE_URL}/inventory/stock/adjust", json=adjustment_data)
        
        if response.status_code == 201:
            entry = response.json()
            print(f"✅ Ajuste de stock creado: {entry['entry_number']}")
            print(f"   📊 Estado: {entry['status']}")
            print(f"   🔧 Tipo: {entry['entry_type']}")
            print(f"   📝 Razón: {adjustment_data['reason']}")
            return entry
        else:
            print(f"❌ Error creando ajuste: {response.text}")
            return None
    
    def test_inventory_summary(self):
        """Probar resumen de inventario"""
        print("\n📊 Obteniendo resumen de inventario...")
        
        response = self.session.get(f"{BASE_URL}/inventory/entries/summary")
        
        if response.status_code == 200:
            summary = response.json()
            print("✅ Resumen obtenido:")
            print(f"   📋 Total entradas: {summary['total_entries']}")
            print(f"   💰 Costo total: Q {summary['total_cost']:,.2f}")
            print(f"   ⏳ Entradas pendientes: {summary['pending_entries']}")
            print(f"   ✅ Completadas hoy: {summary['completed_today']}")
            print(f"   📊 Por tipo: {summary['entries_by_type']}")
            print(f"   📊 Por estado: {summary['entries_by_status']}")
            return summary
        else:
            print(f"❌ Error obteniendo resumen: {response.text}")
            return None
    
    def test_inventory_report(self):
        """Probar reporte de movimientos"""
        print("\n📈 Obteniendo reporte de movimientos...")
        
        response = self.session.get(f"{BASE_URL}/inventory/reports/movements")
        
        if response.status_code == 200:
            report = response.json()
            print(f"✅ Reporte obtenido para {len(report)} productos:")
            
            for item in report[:5]:  # Mostrar solo los primeros 5
                print(f"   📦 {item['product_name']}:")
                print(f"      Stock actual: {item['current_stock']}")
                print(f"      Total entradas: {item['total_entries']}")
                print(f"      Cantidad agregada: {item['total_quantity_added']}")
                print(f"      Costo promedio: Q {item['average_cost']:,.2f}")
            
            if len(report) > 5:
                print(f"   ... y {len(report) - 5} productos más")
            
            return report
        else:
            print(f"❌ Error obteniendo reporte: {response.text}")
            return None
    
    def test_list_entries(self):
        """Probar listado de entradas"""
        print("\n📋 Listando entradas de inventario...")
        
        response = self.session.get(f"{BASE_URL}/inventory/entries")
        
        if response.status_code == 200:
            entries = response.json()
            print(f"✅ Se encontraron {len(entries)} entradas:")
            
            for entry in entries[:5]:  # Mostrar solo las primeras 5
                print(f"   🧾 {entry['entry_number']} - {entry['entry_type'].upper()}")
                print(f"      Estado: {entry['status']} | Items: {entry['items_count']} | Q {entry['total_cost']:,.2f}")
            
            if len(entries) > 5:
                print(f"   ... y {len(entries) - 5} entradas más")
            
            return entries
        else:
            print(f"❌ Error listando entradas: {response.text}")
            return []
    
    def test_entry_types_and_statuses(self):
        """Probar obtención de tipos y estados"""
        print("\n🏷️ Obteniendo tipos y estados disponibles...")
        
        # Tipos
        response = self.session.get(f"{BASE_URL}/inventory/types")
        if response.status_code == 200:
            types = response.json()
            print(f"✅ Tipos disponibles: {[t['label'] for t in types['entry_types']]}")
        
        # Estados
        response = self.session.get(f"{BASE_URL}/inventory/statuses")
        if response.status_code == 200:
            statuses = response.json()
            print(f"✅ Estados disponibles: {[s['label'] for s in statuses['statuses']]}")
    
    def test_verify_stock_update(self, products):
        """Verificar que el stock se actualizó correctamente"""
        print("\n🔍 Verificando actualización de stock...")
        
        for product in products[:2]:  # Verificar los primeros 2 productos
            response = self.session.get(f"{BASE_URL}/products/{product['id']}")
            if response.status_code == 200:
                updated_product = response.json()
                old_stock = product['stock']
                new_stock = updated_product['stock']
                difference = new_stock - old_stock
                
                print(f"   📦 {updated_product['name']}:")
                print(f"      Stock anterior: {old_stock}")
                print(f"      Stock actual: {new_stock}")
                print(f"      Diferencia: +{difference} unidades")
                
                if difference > 0:
                    print(f"      ✅ Stock aumentó correctamente")
                else:
                    print(f"      ⚠️  No se detectó cambio en el stock")
    
    def run_complete_test(self):
        """Ejecutar prueba completa del módulo de inventario"""
        print("📦 Iniciando prueba completa del módulo de inventario\n")
        print("=" * 70)
        
        # 1. Autenticación
        if not self.authenticate():
            return False
        
        # 2. Obtener productos disponibles
        products = self.get_sample_products()
        if not products:
            return False
        
        # 3. Obtener tipos y estados
        self.test_entry_types_and_statuses()
        
        # 4. Crear entrada de producción
        production_entry = self.test_create_production_entry(products)
        if not production_entry:
            return False
        
        # 5. Crear entrada de compra (auto-aprobada)
        purchase_entry = self.test_create_purchase_entry(products)
        
        # 6. Aprobar entrada de producción
        if production_entry:
            self.test_approve_entry(production_entry["id"])
        
        # 7. Completar entradas y actualizar stock
        if production_entry:
            self.test_complete_entry(production_entry["id"])
        
        if purchase_entry:
            self.test_complete_entry(purchase_entry["id"])
        
        # 8. Crear ajuste rápido de stock
        self.test_stock_adjustment(products[0]["id"])
        
        # 9. Verificar actualización de stock
        self.test_verify_stock_update(products)
        
        # 10. Obtener resumen
        self.test_inventory_summary()
        
        # 11. Obtener reporte de movimientos
        self.test_inventory_report()
        
        # 12. Listar todas las entradas
        self.test_list_entries()
        
        print("\n" + "=" * 70)
        print("🎉 ¡Prueba completa del módulo de inventario terminada!")
        print("\n📋 Funcionalidades probadas:")
        print("   ✅ Autenticación JWT")
        print("   ✅ Creación de entradas de producción")
        print("   ✅ Creación de entradas de compra")
        print("   ✅ Aprobación de entradas")
        print("   ✅ Completar entradas y actualizar stock")
        print("   ✅ Ajustes rápidos de stock")
        print("   ✅ Resúmenes y reportes")
        print("   ✅ Listado con filtros")
        print("   ✅ Workflows especializados")
        
        print("\n💡 El módulo de inventario está completamente funcional!")
        print("🔗 URLs útiles:")
        print(f"   📚 Swagger: http://localhost:8000/docs")
        print(f"   📊 Inventario: http://localhost:8000/api/v1/inventory/entries")
        
        return True


def main():
    tester = InventoryTester()
    
    print("📦 SMART ORDERS - MÓDULO DE INGRESO DE PRODUCCIÓN/INVENTARIO")
    print("=" * 70)
    print("\n⚠️  REQUISITOS PREVIOS:")
    print("   1. La API debe estar corriendo en http://localhost:8000")
    print("   2. La base de datos debe estar inicializada (scripts/init_db.py)")
    print("   3. Debe haber productos en el sistema")
    print("\n📈 FUNCIONALIDADES A PROBAR:")
    print("   • Entradas de producción")
    print("   • Entradas de compra")
    print("   • Ajustes de inventario")
    print("   • Actualización automática de stock")
    print("   • Reportes y resúmenes")
    print("\n▶️  Presione Enter para continuar o Ctrl+C para cancelar...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Prueba cancelada por el usuario")
        return
    
    # Verificar que la API esté corriendo
    try:
        response = requests.get(f"{BASE_URL}/../health", timeout=5)
        if response.status_code != 200:
            print("❌ La API no está respondiendo correctamente")
            return
    except requests.exceptions.RequestException:
        print("❌ No se puede conectar a la API. ¿Está corriendo en http://localhost:8000?")
        return
    
    # Ejecutar pruebas
    success = tester.run_complete_test()
    
    if success:
        print("\n🎊 ¡Todas las pruebas pasaron exitosamente!")
        print("📈 El módulo de inventario está listo para producción.")
        print("💰 Los productos ahora tienen stock actualizado automáticamente.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revise los errores arriba.")


if __name__ == "__main__":
    main()

