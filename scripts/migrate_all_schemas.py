#!/usr/bin/env python3
"""
Script para ejecutar migraciones de Alembic en todos los schemas (multitenant)

Este script:
1. Ejecuta migraciones en el schema 'public' primero
2. Obtiene todos los tenants activos de la base de datos
3. Ejecuta migraciones en cada schema de tenant
4. Maneja errores y reporta el estado de cada migración
"""

import sys
import os
import subprocess
from typing import List, Dict, Tuple
import psycopg2
from dotenv import load_dotenv

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

from app.database import SessionLocal, engine
from app.services.tenant_service import TenantService
from app.utils.tenant_db import get_engine_for_schema
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiTenantMigrator:
    """Manejador de migraciones para arquitectura multitenant"""
    
    def __init__(self):
        self.tenant_service = TenantService()
        self.results: List[Dict[str, str]] = []
    
    def run_alembic_for_schema(self, schema_name: str) -> Tuple[bool, str]:
        """
        Ejecuta alembic upgrade head para un schema específico
        
        Args:
            schema_name: Nombre del schema donde ejecutar la migración
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Configurar variable de entorno para el schema específico
            env = os.environ.copy()
            
            if schema_name != "public":
                # Para schemas de tenant, configurar search_path
                # Agregar comillas dobles si el schema tiene caracteres especiales
                # y encodificar correctamente para URL (%22 en lugar de ")
                if any(c in schema_name for c in ['-', ' ', '.', '+']):
                    quoted_schema = f'%22{schema_name}%22'
                else:
                    quoted_schema = schema_name
                
                db_url = env.get('DATABASE_URL', '')
                if '?' in db_url:
                    env['DATABASE_URL'] = f"{db_url}&options=-csearch_path%3D{quoted_schema}"
                else:
                    env['DATABASE_URL'] = f"{db_url}?options=-csearch_path%3D{quoted_schema}"
            
            # Ejecutar alembic upgrade head
            cmd = ["pipenv", "run", "alembic", "upgrade", "head"]
            
            logger.info(f"Ejecutando migraciones para schema: {schema_name}")
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            if result.returncode == 0:
                return True, "Migración exitosa"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"Error en migración: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout: La migración tardó más de 5 minutos"
        except Exception as e:
            return False, f"Error ejecutando migración: {str(e)}"
    
    def get_all_tenant_schemas(self) -> List[Tuple[str, str]]:
        """
        Obtiene todos los schemas de tenants consultando directamente la base de datos
        
        Returns:
            Lista de tuplas (schema_display_name, schema_name)
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
                    schema_name = row[0]
                    # Usar el schema_name como display_name también
                    tenant_schemas.append((schema_name, schema_name))
                
        except Exception as e:
            logger.error(f"Error obteniendo schemas de la base de datos: {str(e)}")
            
        return tenant_schemas
    
    def verify_schema_exists(self, schema_name: str) -> bool:
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
    
    def get_migration_status(self, schema_name: str) -> str:
        """
        Obtiene el estado actual de migraciones para un schema
        
        Args:
            schema_name: Nombre del schema
            
        Returns:
            str: Versión actual, None si no hay tabla, o 'EMPTY' si tabla vacía
        """
        try:
            if schema_name == "public":
                connection_engine = engine
            else:
                connection_engine = get_engine_for_schema(schema_name)
            
            with connection_engine.connect() as connection:
                # Primero verificar si la tabla alembic_version existe en el schema específico
                result = connection.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                        AND table_schema = :schema_name
                    )
                """), {"schema_name": schema_name})
                
                table_exists = result.scalar()
                
                if not table_exists:
                    return None  # No hay tabla alembic_version
                
                # Si existe la tabla, obtener la versión usando search_path específico
                if schema_name != "public":
                    connection.execute(text(f'SET search_path TO "{schema_name}", public'))
                
                result = connection.execute(text("""
                    SELECT version_num FROM alembic_version 
                    ORDER BY version_num DESC LIMIT 1
                """))
                
                row = result.fetchone()
                return row[0] if row else "EMPTY"
                
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def _create_base_tables_for_schema(self, schema_name: str) -> None:
        """
        Crea las tablas base usando SQLAlchemy directamente para schemas vacíos
        
        Args:
            schema_name: Nombre del schema donde crear las tablas
        """
        from sqlalchemy import create_engine
        from app.models import Base
        
        try:
            # Construir URL con encoding correcto para caracteres especiales
            if any(c in schema_name for c in ['-', ' ', '.', '+']):
                quoted_schema = f'%22{schema_name}%22'
            else:
                quoted_schema = schema_name
            
            # Obtener URL base
            import os
            base_url = os.getenv('DATABASE_URL')
            schema_url = f"{base_url}?options=-csearch_path%3D{quoted_schema}"
            
            # Crear engine específico para el schema
            schema_engine = create_engine(schema_url)
            
            # Crear todas las tablas base
            Base.metadata.create_all(bind=schema_engine)
            
            # Crear y configurar tabla alembic_version
            with schema_engine.connect() as connection:
                from sqlalchemy import text
                
                # Crear tabla alembic_version
                connection.execute(text('''
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                '''))
                
                # Obtener la versión head actual de alembic
                from alembic.config import Config
                from alembic.script import ScriptDirectory
                
                alembic_cfg = Config("alembic.ini")
                script_dir = ScriptDirectory.from_config(alembic_cfg)
                head_revision = script_dir.get_current_head()
                
                if head_revision:
                    # Insertar versión head
                    connection.execute(text('''
                        INSERT INTO alembic_version (version_num) VALUES (:version)
                        ON CONFLICT (version_num) DO NOTHING
                    '''), {"version": head_revision})
                
                connection.commit()
                
        except Exception as e:
            raise Exception(f"Error creando tablas base para schema {schema_name}: {str(e)}")
    
    def migrate_all_schemas(self) -> None:
        """
        Ejecuta migraciones en todos los schemas
        """
        print("🚀 Iniciando migraciones multitenant...")
        print("=" * 60)
        
        # 1. Migrar schema public primero
        print("\n🏢 Migrando schema 'public'...")
        
        if not self.verify_schema_exists("public"):
            print("❌ Schema 'public' no existe!")
            return
        
        current_version = self.get_migration_status("public")
        print(f"   📋 Versión actual: {current_version}")
        
        success, message = self.run_alembic_for_schema("public")
        
        self.results.append({
            "schema": "public",
            "tenant": "Sistema Base",
            "status": "✅" if success else "❌",
            "message": message
        })
        
        if success:
            new_version = self.get_migration_status("public")
            print(f"   ✅ Migración exitosa - Nueva versión: {new_version}")
        else:
            print(f"   ❌ Error: {message}")
            print("   ⚠️  Continuando con schemas de tenants...")
        
        # 2. Obtener todos los schemas de tenants
        print(f"\n🏬 Obteniendo schemas de tenants desde la base de datos...")
        tenant_schemas = self.get_all_tenant_schemas()
        
        if not tenant_schemas:
            print("   ℹ️  No se encontraron schemas de tenants")
        else:
            print(f"   📊 Se encontraron {len(tenant_schemas)} schemas de tenants")
        
        # 3. Migrar cada schema de tenant
        for i, (schema_display_name, schema_name) in enumerate(tenant_schemas, 1):
            print(f"\n🏢 [{i}/{len(tenant_schemas)}] Migrando schema: {schema_display_name}")
            print(f"   📂 Schema: {schema_name}")
            
            # Verificar que el schema existe
            if not self.verify_schema_exists(schema_name):
                print(f"   ⚠️  Schema '{schema_name}' no existe, saltando...")
                self.results.append({
                    "schema": schema_name,
                    "tenant": schema_display_name,
                    "status": "⚠️",
                    "message": "Schema no existe"
                })
                continue
            
            # Obtener versión actual
            current_version = self.get_migration_status(schema_name)
            print(f"   📋 Versión actual: {current_version}")
            
            # Si no hay alembic_version o está vacío, crear las tablas base primero
            if current_version is None or current_version == "EMPTY":
                print("   🏗️  Schema vacío - creando tablas base con SQLAlchemy...")
                try:
                    self._create_base_tables_for_schema(schema_name)
                    print("   ✅ Tablas base creadas")
                except Exception as e:
                    print(f"   ❌ Error creando tablas base: {e}")
                    success, message = False, f"Error creando tablas base: {str(e)}"
                    self.results.append({
                        "schema": schema_name,
                        "tenant": schema_display_name,
                        "status": "❌",
                        "message": message
                    })
                    continue
            
            # Ejecutar migración
            success, message = self.run_alembic_for_schema(schema_name)
            
            self.results.append({
                "schema": schema_name,
                "tenant": schema_display_name,
                "status": "✅" if success else "❌",
                "message": message
            })
            
            if success:
                new_version = self.get_migration_status(schema_name)
                print(f"   ✅ Migración exitosa - Nueva versión: {new_version}")
            else:
                print(f"   ❌ Error: {message}")
    
    def print_summary(self) -> None:
        """
        Imprime un resumen de todas las migraciones ejecutadas
        """
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE MIGRACIONES")
        print("=" * 60)
        
        successful = sum(1 for r in self.results if r["status"] == "✅")
        failed = sum(1 for r in self.results if r["status"] == "❌")
        warnings = sum(1 for r in self.results if r["status"] == "⚠️")
        
        print(f"Total schemas procesados: {len(self.results)}")
        print(f"✅ Exitosos: {successful}")
        print(f"❌ Fallidos: {failed}")
        print(f"⚠️  Advertencias: {warnings}")
        
        if failed > 0 or warnings > 0:
            print("\n📋 Detalle de problemas:")
            for result in self.results:
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
        
        # Verificar que pipenv está disponible
        try:
            subprocess.run(["pipenv", "--version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Error: pipenv no está disponible")
            print("   Instala pipenv o ajusta el script para usar 'python' directamente")
            sys.exit(1)
        
        # Ejecutar migraciones
        migrator = MultiTenantMigrator()
        migrator.migrate_all_schemas()
        migrator.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        logger.exception("Error durante la ejecución del script")
        sys.exit(1)


if __name__ == "__main__":
    main()
