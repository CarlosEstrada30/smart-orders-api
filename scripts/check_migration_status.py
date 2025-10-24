#!/usr/bin/env python3
"""
Script para revisar el estado de migraciones en todos los schemas (dry-run)

Este script muestra información sobre:
- Qué schemas existen
- Estado actual de migraciones en cada schema
- Tenants activos e inactivos
- No ejecuta migraciones, solo reporta el estado
"""

import logging
from sqlalchemy import text
from app.utils.tenant_db import get_engine_for_schema, list_schemas
from app.services.tenant_service import TenantService
from app.database import SessionLocal, engine
import sys
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()


# Configurar logging
logging.basicConfig(level=logging.WARNING)  # Solo warnings y errores


class MigrationStatusChecker:
    """Verificador del estado de migraciones multitenant"""

    def __init__(self):
        self.tenant_service = TenantService()

    def get_migration_version(self, schema_name: str) -> Optional[str]:
        """
        Obtiene la versión actual de migraciones para un schema

        Args:
            schema_name: Nombre del schema

        Returns:
            str: Versión actual, None si no hay tabla alembic_version, o 'ERROR' si hay error
        """
        try:
            if schema_name == "public":
                connection_engine = engine
            else:
                connection_engine = get_engine_for_schema(schema_name)

            with connection_engine.connect() as connection:
                if schema_name != "public":
                    connection.execute(
                        text(f'SET search_path TO "{schema_name}", public'))

                # Verificar si existe la tabla alembic_version
                result = connection.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'alembic_version'
                        AND table_schema = :schema_name
                    )
                """), {"schema_name": schema_name})

                if not result.scalar():
                    return None  # No hay tabla de versiones

                # Obtener la versión actual
                result = connection.execute(text("""
                    SELECT version_num FROM alembic_version
                    ORDER BY version_num DESC LIMIT 1
                """))

                row = result.fetchone()
                return row[0] if row else "EMPTY"

        except Exception as e:
            return f"ERROR: {str(e)}"

    def get_tenant_info(self) -> List[Dict[str, str]]:
        """
        Obtiene información de todos los tenants (activos e inactivos) desde la tabla tenants
        Mantenemos esta función para información adicional, pero no la usamos para migraciones

        Returns:
            Lista de diccionarios con información de tenants
        """
        db = SessionLocal()
        tenants_info = []

        try:
            # Obtener todos los tenants (incluyendo inactivos)
            tenants = self.tenant_service.get_tenants(
                db, limit=1000, include_inactive=True)

            for tenant in tenants:
                tenants_info.append({
                    'id': str(tenant.id),
                    'nombre': tenant.nombre,
                    'subdominio': tenant.subdominio,
                    'schema_name': tenant.schema_name,
                    'active': 'Sí' if tenant.active else 'No',
                    'is_trial': 'Sí' if tenant.is_trial else 'No',
                    'created_at': tenant.created_at.strftime('%Y-%m-%d %H:%M:%S') if tenant.created_at else 'N/A'
                })

        except Exception as e:
            print(f"❌ Error obteniendo información de tenants: {str(e)}")
        finally:
            db.close()

        return tenants_info

    def get_all_tenant_schemas(self) -> List[str]:
        """
        Obtiene todos los schemas de tenants consultando directamente la base de datos

        Returns:
            Lista de nombres de schemas
        """
        tenant_schemas = []

        try:
            # Consultar directamente los schemas de la base de datos
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

                for row in result.fetchall():
                    tenant_schemas.append(row[0])

        except Exception as e:
            print(f"❌ Error obteniendo schemas de la base de datos: {str(e)}")

        return tenant_schemas

    def check_schema_exists(self, schema_name: str) -> bool:
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
        except Exception:
            return False

    def get_all_schemas(self) -> List[str]:
        """
        Obtiene todos los schemas de la base de datos

        Returns:
            Lista de nombres de schemas
        """
        return list_schemas()

    def generate_status_report(self) -> None:
        """
        Genera un reporte completo del estado de migraciones
        """
        print("📊 REPORTE DE ESTADO DE MIGRACIONES MULTITENANT")
        print("=" * 65)

        # 1. Información general de schemas
        all_schemas = self.get_all_schemas()
        print(f"\n🏗️  SCHEMAS EN LA BASE DE DATOS")
        print(f"Total schemas: {len(all_schemas)}")

        schema_categories = {
            'public': [],
            'tenant': [],
            'system': []
        }

        for schema in all_schemas:
            if schema == 'public':
                schema_categories['public'].append(schema)
            elif any(schema.startswith(prefix) for prefix in ['pg_', 'information_schema']):
                schema_categories['system'].append(schema)
            else:
                schema_categories['tenant'].append(schema)

        print(f"   - Schema público: {len(schema_categories['public'])}")
        print(f"   - Schemas de tenants: {len(schema_categories['tenant'])}")
        print(f"   - Schemas del sistema: {len(schema_categories['system'])}")

        # 2. Estado de migraciones en schema público
        print(f"\n🏢 ESTADO DEL SCHEMA PÚBLICO")
        public_version = self.get_migration_version("public")

        if public_version is None:
            print("   ❌ No hay tabla alembic_version (sin migraciones)")
        elif public_version == "EMPTY":
            print("   ⚠️  Tabla alembic_version existe pero está vacía")
        elif public_version.startswith("ERROR"):
            print(f"   ❌ Error: {public_version}")
        else:
            print(f"   ✅ Versión actual: {public_version}")

        # 3. Información de tenants
        tenants_info = self.get_tenant_info()
        active_tenants = [t for t in tenants_info if t['active'] == 'Sí']
        inactive_tenants = [t for t in tenants_info if t['active'] == 'No']

        print(f"\n👥 INFORMACIÓN DE TENANTS")
        print(f"Total tenants registrados: {len(tenants_info)}")
        print(f"   - Activos: {len(active_tenants)}")
        print(f"   - Inactivos: {len(inactive_tenants)}")
        print(
            f"   - En trial: {sum(1 for t in tenants_info if t['is_trial'] == 'Sí')}")

        # 4. Estado detallado de schemas de tenants
        all_tenant_schemas = self.get_all_tenant_schemas()

        if all_tenant_schemas:
            print(f"\n🏬 ESTADO DE MIGRACIONES - TODOS LOS SCHEMAS DE TENANTS")
            print("-" * 85)
            print(
                f"{'#':<3} {'Schema':<35} {'Estado Migración':<25} {'Existe en tabla tenants':<20}")
            print("-" * 85)

            tenant_schemas_registered = {
                t['schema_name'] for t in tenants_info}

            for i, schema_name in enumerate(all_tenant_schemas, 1):
                # Verificar si el schema existe
                if not self.check_schema_exists(schema_name):
                    migration_status = "❌ Schema no existe"
                else:
                    version = self.get_migration_version(schema_name)
                    if version is None:
                        migration_status = "❌ Sin alembic_version"
                    elif version == "EMPTY":
                        migration_status = "⚠️  Tabla vacía"
                    elif version.startswith("ERROR"):
                        migration_status = "❌ Error"
                    else:
                        migration_status = f"✅ {version[:16]}"

                # Verificar si está registrado en la tabla tenants
                is_registered = "✅ Sí" if schema_name in tenant_schemas_registered else "⚠️  No"

                print(
                    f"{i:<3} {schema_name[:34]:<35} {migration_status:<25} {is_registered:<20}")
        else:
            print(f"\n🏬 No se encontraron schemas de tenants en la base de datos")

        # 5. Tenants inactivos (si los hay)
        if inactive_tenants:
            print(f"\n⚠️  TENANTS INACTIVOS ({len(inactive_tenants)})")
            for tenant in inactive_tenants[:5]:  # Mostrar solo los primeros 5
                print(
                    f"   - {tenant['nombre']} ({tenant['schema_name']}) - Creado: {tenant['created_at']}")
            if len(inactive_tenants) > 5:
                print(f"   ... y {len(inactive_tenants) - 5} más")

        # 6. Schemas huérfanos (schemas que existen pero no tienen tenant)
        all_tenant_schemas = self.get_all_tenant_schemas()
        tenant_schemas_registered = {t['schema_name'] for t in tenants_info}
        orphan_schemas = [
            s for s in all_tenant_schemas if s not in tenant_schemas_registered]

        if orphan_schemas:
            print(f"\n⚠️  SCHEMAS HUÉRFANOS (sin registro en tabla tenants)")
            print(f"Total: {len(orphan_schemas)} schemas")
            for schema in orphan_schemas[:10]:  # Mostrar solo los primeros 10
                version = self.get_migration_version(schema)
                status = "Sin versión" if version is None else f"Versión: {version}"
                print(f"   - {schema} ({status})")
            if len(orphan_schemas) > 10:
                print(f"   ... y {len(orphan_schemas) - 10} más")

        # 7. Resumen y recomendaciones
        print(f"\n📋 RESUMEN Y RECOMENDACIONES")
        print("-" * 40)

        needs_migration = []
        has_errors = []

        # Revisar público
        if public_version is None or public_version.startswith("ERROR"):
            needs_migration.append("public")
        if public_version and public_version.startswith("ERROR"):
            has_errors.append("public")

        # Revisar todos los schemas de tenants
        all_tenant_schemas = self.get_all_tenant_schemas()
        for schema_name in all_tenant_schemas:
            if self.check_schema_exists(schema_name):
                version = self.get_migration_version(schema_name)
                if version is None or version == "EMPTY":
                    needs_migration.append(schema_name)
                if version and version.startswith("ERROR"):
                    has_errors.append(schema_name)

        if needs_migration:
            print("🔧 Necesitan migraciones:")
            for item in needs_migration[:5]:
                print(f"   - {item}")
            if len(needs_migration) > 5:
                print(f"   ... y {len(needs_migration) - 5} más")

        if has_errors:
            print("❌ Schemas con errores:")
            for item in has_errors:
                print(f"   - {item}")

        if not needs_migration and not has_errors:
            print("✅ Todos los schemas están actualizados")

        print(f"\n💡 Para ejecutar migraciones automáticamente:")
        print("   python scripts/migrate_all_schemas.py")
        print("   # o")
        print("   ./scripts/migrate_all_schemas_simple.sh")


def main():
    """Función principal"""
    try:
        print("🔍 Verificando estado de migraciones multitenant...")
        print()

        checker = MigrationStatusChecker()
        checker.generate_status_report()

    except KeyboardInterrupt:
        print("\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
