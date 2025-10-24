#!/usr/bin/env python3
"""
Script simple para ejecutar tests con PostgreSQL.

Este script ejecuta los tests usando la configuración simple.
"""

import os
import sys
import subprocess


def main():
    """Función principal."""
    print("🧪 Ejecutando tests con PostgreSQL...")
    print("=" * 50)
    
    # Verificar variable de entorno
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ Variable de entorno DATABASE_URL no configurada")
        print("💡 Configurar con:")
        print("   export DATABASE_URL='postgresql://test_user:test_password@localhost:5432/test_db'")
        return 1
    
    print(f"📊 Base de datos: {database_url}")
    
    # Ejecutar tests
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            "tests/api/", 
            "-v",
            "--tb=short"
        ], check=True)
        
        print("\n✅ Todos los tests pasaron exitosamente")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Algunos tests fallaron (código: {e.returncode})")
        return e.returncode
    except Exception as e:
        print(f"\n💥 Error ejecutando tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())