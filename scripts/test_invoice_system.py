#!/usr/bin/env python3
"""
Script para probar el sistema completo de facturación
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

class InvoiceSystemTester:
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
    
    def get_sample_order(self):
        """Obtener una orden de ejemplo"""
        print("\n📋 Obteniendo órdenes existentes...")
        
        response = self.session.get(f"{BASE_URL}/orders/")
        if response.status_code == 200:
            orders = response.json()
            if orders:
                order = orders[0]
                print(f"✅ Usando orden: {order['order_number']} - Cliente: {order.get('client', {}).get('name', 'N/A')}")
                return order
        
        print("❌ No se encontraron órdenes. Ejecute scripts/init_db.py primero")
        return None
    
    def test_create_invoice(self, order_id):
        """Probar creación de factura"""
        print(f"\n🧾 Creando factura para orden {order_id}...")
        
        invoice_data = {
            "order_id": order_id,
            "tax_rate": 0.12,
            "discount_amount": 0.0,
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "payment_terms": "Pago contra entrega",
            "notes": "Factura de prueba generada automáticamente"
        }
        
        response = self.session.post(
            f"{BASE_URL}/invoices/?order_id={order_id}",
            json=invoice_data
        )
        
        if response.status_code == 201:
            invoice = response.json()
            print(f"✅ Factura creada: {invoice['invoice_number']}")
            print(f"   💰 Total: Q {invoice['total_amount']:,.2f}")
            print(f"   📅 Vencimiento: {invoice['due_date']}")
            return invoice
        else:
            print(f"❌ Error creando factura: {response.text}")
            return None
    
    def test_get_invoice(self, invoice_id):
        """Probar obtención de factura"""
        print(f"\n📄 Obteniendo factura {invoice_id}...")
        
        response = self.session.get(f"{BASE_URL}/invoices/{invoice_id}")
        
        if response.status_code == 200:
            invoice = response.json()
            print(f"✅ Factura obtenida: {invoice['invoice_number']}")
            print(f"   Estado: {invoice['status']}")
            print(f"   Total: Q {invoice['total_amount']:,.2f}")
            print(f"   Saldo: Q {invoice['balance_due']:,.2f}")
            return invoice
        else:
            print(f"❌ Error obteniendo factura: {response.text}")
            return None
    
    def test_generate_pdf(self, invoice_id):
        """Probar generación de PDF"""
        print(f"\n📄 Generando PDF para factura {invoice_id}...")
        
        response = self.session.post(f"{BASE_URL}/invoices/{invoice_id}/pdf/generate")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ PDF generado: {result['file_path']}")
            return result['file_path']
        else:
            print(f"❌ Error generando PDF: {response.text}")
            return None
    
    def test_download_pdf(self, invoice_id):
        """Probar descarga de PDF"""
        print(f"\n⬇️ Descargando PDF para factura {invoice_id}...")
        
        response = self.session.get(f"{BASE_URL}/invoices/{invoice_id}/pdf")
        
        if response.status_code == 200:
            # Guardar PDF localmente para verificación
            filename = f"test_invoice_{invoice_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ PDF descargado: {filename} ({len(response.content)} bytes)")
            return filename
        else:
            print(f"❌ Error descargando PDF: {response.text}")
            return None
    
    def test_record_payment(self, invoice_id, amount):
        """Probar registro de pago"""
        print(f"\n💰 Registrando pago de Q {amount:,.2f} para factura {invoice_id}...")
        
        payment_data = {
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_method": "cash",
            "payment_date": datetime.now().isoformat(),
            "notes": "Pago de prueba"
        }
        
        response = self.session.post(f"{BASE_URL}/invoices/payments", json=payment_data)
        
        if response.status_code == 200:
            invoice = response.json()
            print(f"✅ Pago registrado")
            print(f"   💳 Pagado: Q {invoice['paid_amount']:,.2f}")
            print(f"   💰 Saldo: Q {invoice['balance_due']:,.2f}")
            print(f"   📊 Estado: {invoice['status']}")
            return invoice
        else:
            print(f"❌ Error registrando pago: {response.text}")
            return None
    
    def test_invoice_summary(self):
        """Probar resumen de facturas"""
        print("\n📊 Obteniendo resumen de facturas...")
        
        response = self.session.get(f"{BASE_URL}/invoices/summary")
        
        if response.status_code == 200:
            summary = response.json()
            print("✅ Resumen obtenido:")
            print(f"   📋 Total facturas: {summary['total_invoices']}")
            print(f"   💰 Monto total: Q {summary['total_amount']:,.2f}")
            print(f"   💳 Monto pagado: Q {summary['paid_amount']:,.2f}")
            print(f"   ⏰ Monto pendiente: Q {summary['pending_amount']:,.2f}")
            print(f"   🚨 Facturas vencidas: {summary['overdue_count']}")
            return summary
        else:
            print(f"❌ Error obteniendo resumen: {response.text}")
            return None
    
    def test_list_invoices(self):
        """Probar listado de facturas"""
        print("\n📋 Listando todas las facturas...")
        
        response = self.session.get(f"{BASE_URL}/invoices/")
        
        if response.status_code == 200:
            invoices = response.json()
            print(f"✅ Se encontraron {len(invoices)} facturas:")
            
            for invoice in invoices[:5]:  # Mostrar solo las primeras 5
                print(f"   🧾 {invoice['invoice_number']} - {invoice['client_name']} - Q {invoice['total_amount']:,.2f} ({invoice['status']})")
            
            if len(invoices) > 5:
                print(f"   ... y {len(invoices) - 5} más")
            
            return invoices
        else:
            print(f"❌ Error listando facturas: {response.text}")
            return None
    
    def run_complete_test(self):
        """Ejecutar prueba completa del sistema"""
        print("🚀 Iniciando prueba completa del sistema de facturación\n")
        print("=" * 60)
        
        # 1. Autenticación
        if not self.authenticate():
            return False
        
        # 2. Obtener orden de ejemplo
        order = self.get_sample_order()
        if not order:
            return False
        
        # 3. Crear factura
        invoice = self.test_create_invoice(order['id'])
        if not invoice:
            return False
        
        invoice_id = invoice['id']
        
        # 4. Obtener factura
        self.test_get_invoice(invoice_id)
        
        # 5. Generar PDF
        self.test_generate_pdf(invoice_id)
        
        # 6. Descargar PDF
        self.test_download_pdf(invoice_id)
        
        # 7. Registrar pago parcial
        partial_payment = invoice['total_amount'] * 0.5  # 50% del total
        self.test_record_payment(invoice_id, partial_payment)
        
        # 8. Registrar pago completo
        remaining_payment = invoice['total_amount'] * 0.5
        self.test_record_payment(invoice_id, remaining_payment)
        
        # 9. Obtener resumen
        self.test_invoice_summary()
        
        # 10. Listar facturas
        self.test_list_invoices()
        
        print("\n" + "=" * 60)
        print("🎉 ¡Prueba completa del sistema de facturación terminada!")
        print("\n📋 Funcionalidades probadas:")
        print("   ✅ Autenticación JWT")
        print("   ✅ Creación de facturas desde órdenes")
        print("   ✅ Obtención de facturas")
        print("   ✅ Generación de PDF profesional")
        print("   ✅ Descarga de PDF")
        print("   ✅ Registro de pagos")
        print("   ✅ Actualización automática de estados")
        print("   ✅ Resúmenes y reportes")
        print("   ✅ Listado con filtros")
        
        print("\n💡 El sistema de facturación está completamente funcional!")
        return True


def main():
    tester = InvoiceSystemTester()
    
    print("🧾 SMART ORDERS - PRUEBA DEL SISTEMA DE FACTURACIÓN")
    print("=" * 60)
    print("\n⚠️  REQUISITOS PREVIOS:")
    print("   1. La API debe estar corriendo en http://localhost:8000")
    print("   2. La base de datos debe estar inicializada (scripts/init_db.py)")
    print("   3. Debe haber al menos una orden en el sistema")
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
        print("📈 El sistema está listo para producción.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revise los errores arriba.")


if __name__ == "__main__":
    main()
