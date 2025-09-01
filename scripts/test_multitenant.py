#!/usr/bin/env python3
"""
Script de prueba para la funcionalidad multitenant
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.services.tenant_service import TenantService
from app.schemas.tenant import TenantCreate
from app.utils.tenant_db import list_schemas, get_current_schema
from app.database import engine
import uuid


def test_tenant_creation():
    """Prueba la creación de un tenant"""
    print("=== Prueba de Creación de Tenant ===")
    
    # Crear una sesión de base de datos
    db = SessionLocal()
    tenant_service = TenantService()
    
    try:
        # Generar datos únicos para el tenant de prueba
        unique_id = str(uuid.uuid4())[:8]
        
        # Crear datos del tenant (el token se autogenera como UUID)
        tenant_data = TenantCreate(
            nombre=f"Empresa Test {unique_id}",
            subdominio=f"test{unique_id}"
        )
        
        print(f"Creando tenant: {tenant_data.nombre}")
        print(f"Subdominio: {tenant_data.subdominio}")
        print("Token: Se generará automáticamente como UUID")
        
        # Crear el tenant
        db_tenant = tenant_service.create_tenant(db, tenant_data)
        
        print(f"✅ Tenant creado exitosamente:")
        print(f"   ID: {db_tenant.id}")
        print(f"   Nombre: {db_tenant.nombre}")
        print(f"   Token: {db_tenant.token}")
        print(f"   Subdominio: {db_tenant.subdominio}")
        print(f"   Schema guardado: {db_tenant.schema_name}")
        print(f"   Creado: {db_tenant.created_at}")
        
        return db_tenant
        
    except Exception as e:
        print(f"❌ Error al crear tenant: {str(e)}")
        return None
    finally:
        db.close()


def test_schema_listing():
    """Lista todos los schemas disponibles"""
    print("\n=== Schemas Disponibles ===")
    
    schemas = list_schemas()
    print(f"Total de schemas encontrados: {len(schemas)}")
    
    for schema in schemas:
        print(f"  - {schema}")
    
    # Mostrar schema actual
    current_schema = get_current_schema(engine)
    print(f"\nSchema actual: {current_schema}")


def test_tenant_retrieval():
    """Prueba la recuperación de tenants"""
    print("\n=== Prueba de Recuperación de Tenants ===")
    
    db = SessionLocal()
    tenant_service = TenantService()
    
    try:
        # Obtener todos los tenants
        tenants = tenant_service.get_tenants(db)
        print(f"Total de tenants encontrados: {len(tenants)}")
        
        for tenant in tenants:
            print(f"  - {tenant.nombre} (Schema: {tenant.schema_name})")
        
    except Exception as e:
        print(f"❌ Error al recuperar tenants: {str(e)}")
    finally:
        db.close()


def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de multitenant\n")
    
    # Mostrar schemas antes de la prueba
    test_schema_listing()
    
    # Crear un tenant de prueba
    tenant = test_tenant_creation()
    
    # Mostrar schemas después de la creación
    test_schema_listing()
    
    # Probar recuperación de tenants
    test_tenant_retrieval()
    
    print("\n✅ Pruebas completadas")
    
    if tenant:
        print(f"\n📋 Resumen del tenant creado:")
        print(f"   ID: {tenant.id}")
        print(f"   Schema: {tenant.schema_name}")
        print(f"   Puedes conectarte al schema usando:")
        print(f"   SET search_path TO {tenant.schema_name};")


if __name__ == "__main__":
    main()
