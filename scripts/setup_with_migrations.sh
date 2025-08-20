#!/bin/bash

# Smart Orders API - Setup Script with Migrations
# Este script configura el entorno de desarrollo e inicializa las migraciones

set -e

echo "🚀 Smart Orders API - Setup Script with Migrations"
echo "=================================================="

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instala Python 3.8+"
    exit 1
fi

# Verificar versión de Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION detectado"

# Intentar usar Pipenv primero
if command -v pipenv &> /dev/null; then
    echo "📦 Pipenv detectado, intentando usar Pipenv..."
    
    # Verificar versión de Pipenv
    PIPENV_VERSION=$(pipenv --version | cut -d' ' -f3)
    echo "📋 Versión de Pipenv: $PIPENV_VERSION"
    
    # Intentar instalar con Pipenv
    if pipenv install --skip-lock; then
        echo "✅ Instalación con Pipenv exitosa"
        
        # Crear archivo .env si no existe
        if [ ! -f .env ]; then
            echo "📝 Creando archivo .env..."
            cp .env.example .env
            echo "⚠️  Por favor configura las variables de entorno en el archivo .env"
        else
            echo "✅ Archivo .env ya existe"
        fi
        
        # Configurar migraciones
        echo "🗄️  Configurando migraciones de Alembic..."
        
        # Verificar si ya existe una migración inicial
        if [ ! -f "alembic/versions/9e16c8e2eae6_initial_migration.py" ]; then
            echo "📋 Creando migración inicial..."
            pipenv run alembic revision --autogenerate -m "Initial migration"
        else
            echo "✅ Migración inicial ya existe"
        fi
        
        # Aplicar migraciones
        echo "🔄 Aplicando migraciones..."
        pipenv run alembic upgrade head
        
        # Inicializar base de datos con datos de ejemplo
        echo "📊 Inicializando base de datos con datos de ejemplo..."
        pipenv run python scripts/init_db.py
        
        echo ""
        echo "🎉 ¡Setup completado con Pipenv y migraciones!"
        echo ""
        echo "📋 Para ejecutar la aplicación:"
        echo "   pipenv shell"
        echo "   uvicorn app.main:app --reload"
        echo ""
        echo "🌐 La API estará disponible en: http://localhost:8000"
        echo "📚 Documentación: http://localhost:8000/docs"
        echo ""
        echo "📋 Comandos útiles de migración:"
        echo "   pipenv run alembic current    # Ver migración actual"
        echo "   pipenv run alembic history    # Ver historial"
        echo "   pipenv run alembic revision --autogenerate -m 'Descripción'  # Nueva migración"
        
    else
        echo "❌ Error con Pipenv, usando pip..."
        ./scripts/setup_pip.sh
    fi
else
    echo "📦 Pipenv no detectado, usando pip..."
    ./scripts/setup_pip.sh
fi 