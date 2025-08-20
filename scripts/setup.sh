#!/bin/bash

# Smart Orders API - Setup Script
# Este script configura el entorno de desarrollo

set -e

echo "🚀 Smart Orders API - Setup Script"
echo "=================================="

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instala Python 3.8+"
    exit 1
fi

# Verificar versión de Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION detectado"

# Verificar si pipenv está instalado
if ! command -v pipenv &> /dev/null; then
    echo "📦 Instalando Pipenv..."
    pip3 install pipenv
else
    echo "✅ Pipenv ya está instalado"
fi

# Instalar dependencias
echo "📦 Instalando dependencias..."
pipenv install

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env..."
    cp .env.example .env
    echo "⚠️  Por favor configura las variables de entorno en el archivo .env"
    echo "   Especialmente DATABASE_URL para tu base de datos PostgreSQL"
else
    echo "✅ Archivo .env ya existe"
fi

# Inicializar base de datos
echo "🗄️  Inicializando base de datos..."
pipenv run python scripts/init_db.py

echo ""
echo "🎉 ¡Setup completado!"
echo ""
echo "📋 Para ejecutar la aplicación:"
echo "   pipenv shell"
echo "   uvicorn app.main:app --reload"
echo ""
echo "🌐 La API estará disponible en: http://localhost:8000"
echo "📚 Documentación: http://localhost:8000/docs"
echo ""
echo "📋 Datos de acceso de ejemplo:"
echo "   Admin: admin@example.com / admin123"
echo "   Usuario: user1@example.com / user123" 