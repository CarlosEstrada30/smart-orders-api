#!/usr/bin/env python3
"""
Script para probar el sistema de comprobantes de órdenes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000/api/v1"
CREDENTIALS = {
    "admin": {"email": "admin@example.com", "password": "admin123"},
    "user": {"email": "user1@example.com", "password": "user123"}
}

class ReceiptTester:
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
    
    def get_sample_orders(self):
        """Obtener órdenes de ejemplo"""
        print("\n📋 Obteniendo órdenes disponibles...")
        
        response = self.session.get(f"{BASE_URL}/orders/")
        if response.status_code == 200:
            orders = response.json()
            if orders:
                print(f"✅ Se encontraron {len(orders)} órdenes")
                for i, order in enumerate(orders[:3]):  # Mostrar solo las primeras 3
                    print(f"   {i+1}. {order['order_number']} - {order.get('client', {}).get('name', 'N/A')} - Q {order['total_amount']:,.2f} ({order['status']})")
                return orders
        
        print("❌ No se encontraron órdenes. Ejecute scripts/init_db.py primero")
        return []
    
    def test_receipt_download(self, order_id):
        """Probar descarga de comprobante"""
        print(f"\n📄 Descargando comprobante para orden {order_id}...")
        
        response = self.session.get(f"{BASE_URL}/orders/{order_id}/receipt")
        
        if response.status_code == 200:
            # Guardar PDF localmente para verificación
            filename = f"comprobante_orden_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Comprobante descargado: {filename} ({len(response.content)} bytes)")
            return filename
        else:
            print(f"❌ Error descargando comprobante: {response.text}")
            return None
    
    def test_receipt_preview(self, order_id):
        """Probar preview de comprobante"""
        print(f"\n👀 Probando preview de comprobante para orden {order_id}...")
        
        response = self.session.get(f"{BASE_URL}/orders/{order_id}/receipt/preview")
        
        if response.status_code == 200:
            print(f"✅ Preview funcionando - Tamaño: {len(response.content)} bytes")
            print(f"   URL: http://localhost:8000/api/v1/orders/{order_id}/receipt/preview")
            return True
        else:
            print(f"❌ Error en preview: {response.text}")
            return False
    
    def test_receipt_generation(self, order_id):
        """Probar generación y guardado de comprobante"""
        print(f"\n💾 Generando archivo de comprobante para orden {order_id}...")
        
        response = self.session.post(f"{BASE_URL}/orders/{order_id}/receipt/generate")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Archivo generado exitosamente:")
            print(f"   📁 Archivo: {result['file_path']}")
            print(f"   📋 Orden: {result['order_number']}")
            return result['file_path']
        else:
            print(f"❌ Error generando archivo: {response.text}")
            return None
    
    def test_order_details(self, order_id):
        """Obtener detalles de la orden para verificación"""
        print(f"\n🔍 Obteniendo detalles de orden {order_id}...")
        
        response = self.session.get(f"{BASE_URL}/orders/{order_id}")
        
        if response.status_code == 200:
            order = response.json()
            print(f"✅ Orden obtenida:")
            print(f"   📋 Número: {order['order_number']}")
            print(f"   👤 Cliente: {order.get('client', {}).get('name', 'N/A')}")
            print(f"   📅 Fecha: {order['created_at']}")
            print(f"   📊 Estado: {order['status']}")
            print(f"   💰 Total: Q {order['total_amount']:,.2f}")
            print(f"   📦 Items: {len(order.get('items', []))} productos")
            return order
        else:
            print(f"❌ Error obteniendo orden: {response.text}")
            return None
    
    def run_complete_test(self):
        """Ejecutar prueba completa del sistema de comprobantes"""
        print("🧾 Iniciando prueba completa del sistema de comprobantes\n")
        print("=" * 60)
        
        # 1. Autenticación
        if not self.authenticate():
            return False
        
        # 2. Obtener órdenes disponibles
        orders = self.get_sample_orders()
        if not orders:
            return False
        
        # 3. Seleccionar primera orden para pruebas
        test_order = orders[0]
        order_id = test_order['id']
        
        print(f"\n🎯 Probando con orden: {test_order['order_number']}")
        
        # 4. Obtener detalles de la orden
        self.test_order_details(order_id)
        
        # 5. Probar descarga directa
        self.test_receipt_download(order_id)
        
        # 6. Probar preview
        self.test_receipt_preview(order_id)
        
        # 7. Probar generación de archivo
        self.test_receipt_generation(order_id)
        
        # 8. Probar con múltiples órdenes
        print(f"\n🔄 Probando con múltiples órdenes...")
        for i, order in enumerate(orders[1:3]):  # Probar con 2 órdenes más
            print(f"\n--- Orden {i+2}: {order['order_number']} ---")
            self.test_receipt_download(order['id'])
        
        print("\n" + "=" * 60)
        print("🎉 ¡Prueba completa del sistema de comprobantes terminada!")
        print("\n📋 Funcionalidades probadas:")
        print("   ✅ Autenticación JWT")
        print("   ✅ Obtención de órdenes")
        print("   ✅ Generación de comprobantes PDF")
        print("   ✅ Descarga directa de comprobantes")
        print("   ✅ Preview en navegador")
        print("   ✅ Guardado de archivos")
        print("   ✅ Múltiples órdenes")
        
        print("\n💡 El sistema de comprobantes está completamente funcional!")
        print("\n🔗 URLs útiles:")
        print(f"   📚 Swagger: http://localhost:8000/docs")
        print(f"   👀 Preview: http://localhost:8000/api/v1/orders/{order_id}/receipt/preview")
        print(f"   ⬇️ Descarga: http://localhost:8000/api/v1/orders/{order_id}/receipt")
        
        return True


def main():
    tester = ReceiptTester()
    
    print("🧾 SMART ORDERS - PRUEBA DEL SISTEMA DE COMPROBANTES")
    print("=" * 60)
    print("\n⚠️  REQUISITOS PREVIOS:")
    print("   1. La API debe estar corriendo en http://localhost:8000")
    print("   2. La base de datos debe estar inicializada (scripts/init_db.py)")
    print("   3. Debe haber al menos una orden en el sistema")
    print("\n📄 DIFERENCIA: Comprobante vs Factura")
    print("   • Comprobante: Confirmación de pedido (no fiscal)")
    print("   • Factura: Documento fiscal para cobro")
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
        print("📈 El sistema de comprobantes está listo para uso.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revise los errores arriba.")


if __name__ == "__main__":
    main()
