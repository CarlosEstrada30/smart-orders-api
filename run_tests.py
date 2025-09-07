#!/usr/bin/env python3
"""
Script para ejecutar los tests del proyecto smart-orders-api.

Este script proporciona una interfaz simple para ejecutar diferentes
tipos de tests usando pytest.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Ejecutar un comando y mostrar el resultado."""
    print(f"\n🚀 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completado exitosamente")
        else:
            print(f"❌ {description} falló con código de salida: {result.returncode}")
        return result.returncode
    except Exception as e:
        print(f"❌ Error ejecutando {description}: {e}")
        return 1


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Ejecutar tests de smart-orders-api")
    
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "api", "slow"],
        default="all",
        help="Tipo de tests a ejecutar (default: all)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Ejecutar con reporte de cobertura"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Salida verbose"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Ejecutar un archivo de test específico"
    )
    
    parser.add_argument(
        "--function",
        help="Ejecutar una función específica (usar con --file)"
    )
    
    args = parser.parse_args()
    
    # Verificar que estamos en el directorio correcto
    if not Path("pytest.ini").exists():
        print("❌ Error: No se encontró pytest.ini. Ejecuta desde el directorio raíz del proyecto.")
        return 1
    
    # Construir comando base
    base_cmd = "pipenv run pytest"
    
    # Agregar opciones según argumentos
    cmd_parts = [base_cmd]
    
    if args.verbose:
        cmd_parts.append("-v")
    
    if args.coverage:
        cmd_parts.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    # Seleccionar tests según el tipo
    if args.file:
        if args.function:
            cmd_parts.append(f"tests/{args.file}::{args.function}")
        else:
            cmd_parts.append(f"tests/{args.file}")
    else:
        if args.type == "unit":
            cmd_parts.extend(["-m", "unit", "tests/unit/"])
        elif args.type == "integration":
            cmd_parts.extend(["-m", "integration", "tests/integration/"])
        elif args.type == "api":
            cmd_parts.extend(["-m", "api", "tests/integration/"])
        elif args.type == "slow":
            cmd_parts.extend(["-m", "slow"])
        else:  # all
            cmd_parts.append("tests/")
    
    command = " ".join(cmd_parts)
    
    print(f"🧪 Ejecutando tests de smart-orders-api")
    print(f"📁 Tipo: {args.type}")
    if args.file:
        print(f"📄 Archivo: {args.file}")
    if args.function:
        print(f"🎯 Función: {args.function}")
    
    # Ejecutar tests
    return run_command(command, f"Tests {args.type}")


if __name__ == "__main__":
    sys.exit(main())
