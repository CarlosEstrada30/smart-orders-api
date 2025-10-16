#!/usr/bin/env python3
"""
Script para facilitar el uso de migraciones de Alembic
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Ejecutar un comando y mostrar el resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True)
        print(f"✅ {description} completado")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}:")
        print(e.stderr)
        return False


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("🔧 Script de Migraciones de Alembic")
        print("====================================")
        print("Uso:")
        print("  python scripts/migrate.py init          # Inicializar Alembic")
        print("  python scripts/migrate.py create        # Crear nueva migración")
        print("  python scripts/migrate.py upgrade       # Aplicar migraciones")
        print("  python scripts/migrate.py downgrade     # Revertir migración")
        print("  python scripts/migrate.py current       # Ver migración actual")
        print("  python scripts/migrate.py history       # Ver historial")
        print("  python scripts/migrate.py stamp         # Marcar como aplicada")
        return

    command = sys.argv[1]

    if command == "init":
        # Inicializar Alembic
        if not Path("alembic.ini").exists():
            run_command("alembic init alembic", "Inicializando Alembic")
        else:
            print("⚠️  Alembic ya está inicializado")

    elif command == "create":
        # Crear nueva migración
        message = sys.argv[2] if len(
            sys.argv) > 2 else "Auto-generated migration"
        run_command(
            f'alembic revision --autogenerate -m "{message}"',
            "Creando migración")

    elif command == "upgrade":
        # Aplicar migraciones
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_command(
            f"alembic upgrade {revision}",
            f"Aplicando migraciones hasta {revision}")

    elif command == "downgrade":
        # Revertir migración
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        run_command(
            f"alembic downgrade {revision}",
            f"Revirtiendo migración a {revision}")

    elif command == "current":
        # Ver migración actual
        run_command("alembic current", "Mostrando migración actual")

    elif command == "history":
        # Ver historial
        run_command("alembic history", "Mostrando historial de migraciones")

    elif command == "stamp":
        # Marcar como aplicada
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_command(
            f"alembic stamp {revision}",
            f"Marcando {revision} como aplicada")

    else:
        print(f"❌ Comando '{command}' no reconocido")
        print("Comandos disponibles: init, create, upgrade, downgrade, current, history, stamp")


if __name__ == "__main__":
    main()
