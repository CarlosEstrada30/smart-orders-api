#!/usr/bin/env python3
"""
Script simplificado para ejecutar migraciones de Alembic en todos los schemas (multitenant)

Este script utiliza la función run_migrations proporcionada para ejecutar migraciones
de manera más simple y confiable, permitiendo tanto upgrade como downgrade.
"""

import logging
import os
import sys
import pathlib
from typing import List, Dict, Optional

# Agregar el directorio raíz al path ANTES de importar módulos de app
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from app.utils.tenant_db import get_engine_for_schema
from app.database import engine
from alembic import config
from alembic.command import downgrade, upgrade

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations(schema_name: str, revision: Optional[str] = None):
    """
    Ejecuta migraciones de Alembic para un schema específico
    
    Args:
        schema_name: Nombre del schema donde ejecutar la migración
        revision: Versión específica a la cual hacer downgrade (None para upgrade a head)
    """
    root_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
    cfg = config.Config(f"{str(root_dir)}/alembic.ini")
    
    # Para el schema public, usar el engine por defecto
    print(f"------------ Schema name: {schema_name}")
    if schema_name == "public":
        connection_engine = engine
    else:
        connection_engine = get_engine_for_schema(schema_name)
    
    with connection_engine.begin() as connection:
        # Configurar search_path explícitamente para tenants
        
        cfg.attributes["connection"] = connection
        
        # Verificar versión actual antes de la migración
        try:
            result = connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"))
            current_version = result.fetchone()
            current_version_str = current_version[0] if current_version else "Sin versión"
            logger.info(f"Schema {schema_name} - Versión actual: {current_version_str}")
        except Exception as e:
            logger.warning(f"No se pudo obtener versión actual para {schema_name}: {e}")
            current_version_str = "Error"
        
        if not revision:
            logger.info(f"Migrating {schema_name} from {current_version_str} to head")
            upgrade(cfg, "head")
        else:
            logger.info(f"Downgrading {schema_name} from {current_version_str} to {revision}")
            downgrade(cfg, revision=revision)
        
        # Verificar versión después de la migración
        try:
            result = connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"))
            new_version = result.fetchone()
            new_version_str = new_version[0] if new_version else "Sin versión"
            logger.info(f"Schema {schema_name} - Nueva versión: {new_version_str}")
        except Exception as e:
            logger.warning(f"No se pudo obtener nueva versión para {schema_name}: {e}")


def get_all_tenant_schemas() -> List[str]:
    """
    Obtiene todos los schemas de tenants consultando directamente la base de datos
    
    Returns:
        Lista de nombres de schemas de tenants
    """
    tenant_schemas = []
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN (
                    'information_schema',
                    'pg_catalog',
                    'pg_toast',
                    'pg_toast_temp_1',
                    'pg_temp_1',
                    'public'
                )
                AND schema_name NOT LIKE 'pg_%'
                ORDER BY schema_name
            """))
            
            tenant_schemas = [row[0] for row in result.fetchall()]
            
    except Exception as e:
        logger.error(f"Error obteniendo schemas de la base de datos: {str(e)}")
    
    return tenant_schemas


def verify_schema_exists(schema_name: str) -> bool:
    """
    Verifica si un schema existe en la base de datos
    
    Args:
        schema_name: Nombre del schema a verificar
        
    Returns:
        bool: True si el schema existe
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = :schema_name
                )
            """), {"schema_name": schema_name})
            
            return result.scalar()
    except Exception as e:
        logger.error(f"Error verificando schema {schema_name}: {str(e)}")
        return False


def migrate_all_schemas(revision: Optional[str] = None) -> None:
    """
    Ejecuta migraciones en todos los schemas
    
    Args:
        revision: Versión específica para downgrade (None para upgrade a head)
    """
    operation = "downgrade" if revision else "upgrade"
    print(f"🚀 Iniciando {operation} multitenant...")
    print("=" * 60)
    
    results: List[Dict[str, str]] = []
    
    # 1. Migrar schema public primero
    print(f"\n🏢 {operation.capitalize()} schema 'public'...")
    
    if not verify_schema_exists("public"):
        print("❌ Schema 'public' no existe!")
        return
    
    try:
        run_migrations("public", revision)
        results.append({
            "schema": "public",
            "tenant": "Sistema Base",
            "status": "✅",
            "message": f"{operation.capitalize()} exitoso"
        })
        print(f"   ✅ {operation.capitalize()} exitoso para schema 'public'")
    except Exception as e:
        error_msg = str(e)
        results.append({
            "schema": "public",
            "tenant": "Sistema Base",
            "status": "❌",
            "message": f"Error: {error_msg}"
        })
        print(f"   ❌ Error en schema 'public': {error_msg}")
        print("   ⚠️  Continuando con schemas de tenants...")
    
    # 2. Obtener todos los schemas de tenants
    print(f"\n🏬 Obteniendo schemas de tenants desde la base de datos...")
    tenant_schemas = get_all_tenant_schemas()
    
    if not tenant_schemas:
        print("   ℹ️  No se encontraron schemas de tenants")
    else:
        print(f"   📊 Se encontraron {len(tenant_schemas)} schemas de tenants")
    
    # 3. Migrar cada schema de tenant
    for i, schema_name in enumerate(tenant_schemas, 1):
        print(f"\n🏢 [{i}/{len(tenant_schemas)}] {operation.capitalize()} schema: {schema_name}")
        
        # Verificar que el schema existe
        if not verify_schema_exists(schema_name):
            print(f"   ⚠️  Schema '{schema_name}' no existe, saltando...")
            results.append({
                "schema": schema_name,
                "tenant": schema_name,
                "status": "⚠️",
                "message": "Schema no existe"
            })
            continue
        
        try:
            print(f"   🔄 Ejecutando {operation} para schema '{schema_name}'...")
            run_migrations(schema_name, revision)
            results.append({
                "schema": schema_name,
                "tenant": schema_name,
                "status": "✅",
                "message": f"{operation.capitalize()} exitoso"
            })
            print(f"   ✅ {operation.capitalize()} exitoso para schema '{schema_name}'")
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Error en schema '{schema_name}': {error_msg}")
            print(f"   📋 Detalle del error: {type(e).__name__}")
            results.append({
                "schema": schema_name,
                "tenant": schema_name,
                "status": "❌",
                "message": f"Error: {error_msg}"
            })
    
    # 4. Mostrar resumen
    print_summary(results)


def print_summary(results: List[Dict[str, str]]) -> None:
    """
    Imprime un resumen de todas las migraciones ejecutadas
    """
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE MIGRACIONES")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["status"] == "✅")
    failed = sum(1 for r in results if r["status"] == "❌")
    warnings = sum(1 for r in results if r["status"] == "⚠️")
    
    print(f"Total schemas procesados: {len(results)}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    print(f"⚠️  Advertencias: {warnings}")
    
    if failed > 0 or warnings > 0:
        print("\n📋 Detalle de problemas:")
        for result in results:
            if result["status"] != "✅":
                print(f"   {result['status']} {result['tenant']} ({result['schema']}): {result['message']}")
    
    print(f"\n🎉 Proceso de migraciones completado!")


def main():
    """Función principal"""
    try:
        # Verificar que estamos en el directorio correcto
        if not os.path.exists("alembic.ini"):
            print("❌ Error: No se encontró alembic.ini")
            print("   Ejecuta este script desde la raíz del proyecto")
            sys.exit(1)
        
        # Verificar argumentos de línea de comandos
        if len(sys.argv) > 1:
            revision = sys.argv[1]
            # Verificar si es una opción de ayuda
            if revision in ['--help', '-h', 'help']:
                print("Uso: python migrate_all_schemas.py [revision]")
                print("")
                print("Sin argumentos: Ejecuta upgrade a head en todos los schemas")
                print("Con revision: Ejecuta downgrade a la versión especificada")
                print("")
                print("Ejemplos:")
                print("  python migrate_all_schemas.py                    # Upgrade a head")
                print("  python migrate_all_schemas.py base               # Downgrade a 'base'")
                print("  python migrate_all_schemas.py f4d1333f244b       # Downgrade a versión específica")
                sys.exit(0)
            
            print(f"🔄 Ejecutando downgrade a versión: {revision}")
            migrate_all_schemas(revision=revision)
        else:
            print("⬆️  Ejecutando upgrade a head")
            migrate_all_schemas()
    
    except KeyboardInterrupt:
        print("\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        logger.exception("Error durante la ejecución del script")
        sys.exit(1)


if __name__ == "__main__":
    main()