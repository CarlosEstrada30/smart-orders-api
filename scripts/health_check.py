#!/usr/bin/env python3
"""
Health check script para verificar el estado de la aplicación
Usado por Render y otros servicios de monitoreo
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def check_database_connection() -> Dict[str, Any]:
    """Verifica la conexión a la base de datos"""
    try:
        from app.database import engine
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            result.fetchone()
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Database error: {str(e)}"}


async def check_migrations_status() -> Dict[str, Any]:
    """Verifica el estado de las migraciones"""
    try:
        from scripts.migrate_all_schemas import MultiTenantMigrator

        migrator = MultiTenantMigrator()

        # Verificar schema público
        public_status = migrator.get_migration_status("public")
        if public_status and not public_status.startswith("ERROR"):
            return {
                "status": "healthy",
                "message": f"Migrations OK - Version: {public_status}"}
        else:
            return {
                "status": "warning",
                "message": f"Migration status: {public_status}"}

    except Exception as e:
        return {
            "status": "warning",
            "message": f"Migration check error: {str(e)}"}


async def check_environment_variables() -> Dict[str, Any]:
    """Verifica variables de entorno críticas"""
    try:
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY"
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            return {
                "status": "unhealthy",
                "message": f"Missing environment variables: {', '.join(missing_vars)}"}

        return {"status": "healthy", "message": "Environment variables OK"}

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Environment check error: {str(e)}"}


async def run_health_checks() -> Dict[str, Any]:
    """Ejecuta todas las verificaciones de salud"""

    print("🏥 Ejecutando health checks...")

    checks = {
        "database": await check_database_connection(),
        "migrations": await check_migrations_status(),
        "environment": await check_environment_variables(),
    }

    # Determinar estado general
    overall_status = "healthy"

    # Si alguno está unhealthy, el estado general es unhealthy
    if any(check["status"] == "unhealthy" for check in checks.values()):
        overall_status = "unhealthy"
    # Si alguno tiene warning pero ninguno unhealthy, el estado es warning
    elif any(check["status"] == "warning" for check in checks.values()):
        overall_status = "warning"

    result = {
        "status": overall_status,
        "timestamp": f"{asyncio.get_event_loop().time()}",
        "checks": checks
    }

    # Mostrar resultados
    status_emoji = {"healthy": "✅", "warning": "⚠️", "unhealthy": "❌"}

    print(f"\n{status_emoji.get(overall_status, '❓')} Estado general: {overall_status.upper()}")

    for check_name, check_result in checks.items():
        emoji = status_emoji.get(check_result["status"], "❓")
        print(f"  {emoji} {check_name}: {check_result['message']}")

    return result


async def main():
    """Función principal"""
    try:
        result = await run_health_checks()

        # Retornar código de salida apropiado
        if result["status"] == "unhealthy":
            sys.exit(1)
        elif result["status"] == "warning":
            sys.exit(0)  # Warnings no deben fallar el health check
        else:
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error ejecutando health checks: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
