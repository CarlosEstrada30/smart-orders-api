#!/bin/bash

# =============================================================================
# ENTRYPOINT PARA DESPLIEGUE EN RENDER
# =============================================================================
# Este script maneja todo el proceso de despliegue:
# 1. Instalación de dependencias
# 2. Validación de variables de entorno
# 3. Espera de la base de datos
# 4. Migraciones del schema público
# 5. Migraciones de todos los schemas de tenants
# 6. Inicio del servidor FastAPI
# =============================================================================

set -e  # Salir si cualquier comando falla

# Colores para logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# =============================================================================
# 1. VALIDACIÓN DE VARIABLES DE ENTORNO
# =============================================================================
log "🔍 Validando variables de entorno..."

required_vars=(
    "DATABASE_URL"
    "SECRET_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    error "Variables de entorno faltantes: ${missing_vars[*]}"
    exit 1
fi

success "Variables de entorno validadas"

# =============================================================================
# 2. INSTALACIÓN DE DEPENDENCIAS
# =============================================================================
log "📦 Instalando dependencias con pipenv..."

# Instalar pipenv si no está disponible
if ! command -v pipenv &> /dev/null; then
    log "Instalando pipenv..."
    pip install pipenv
fi

# Instalar dependencias
pipenv install --deploy --ignore-pipfile

success "Dependencias instaladas"

# =============================================================================
# 3. ESPERA DE LA BASE DE DATOS
# =============================================================================
log "⏳ Esperando disponibilidad de la base de datos..."

wait_for_db() {
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Intento $attempt/$max_attempts: Conectando a la base de datos..."
        
        if pipenv run python -c "
import sys, os
sys.path.append('.')
try:
    from app.database import engine
    with engine.connect() as connection:
        connection.execute('SELECT 1')
    print('✅ Base de datos disponible')
    sys.exit(0)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
" 2>/dev/null; then
            success "Base de datos disponible"
            return 0
        fi
        
        warn "Base de datos no disponible, esperando 5 segundos..."
        sleep 5
        ((attempt++))
    done
    
    error "No se pudo conectar a la base de datos después de $max_attempts intentos"
    return 1
}

if ! wait_for_db; then
    exit 1
fi

# =============================================================================
# 4. MIGRACIONES DEL SCHEMA PÚBLICO
# =============================================================================
log "🏢 Ejecutando migraciones del schema público..."

if pipenv run alembic upgrade head; then
    success "Migraciones del schema público completadas"
else
    error "Falló la migración del schema público"
    exit 1
fi

# =============================================================================
# 5. MIGRACIONES DE TODOS LOS SCHEMAS DE TENANTS
# =============================================================================
log "🏬 Ejecutando migraciones multitenant..."

# Ejecutar script de migraciones multitenant con manejo de errores
if pipenv run python scripts/migrate_all_schemas.py; then
    success "Migraciones multitenant completadas"
else
    # En producción, las migraciones de tenants pueden fallar si no hay tenants
    # Esto no debería bloquear el despliegue
    warn "Algunas migraciones de tenants fallaron - continuando con el despliegue"
fi

# =============================================================================
# 6. VERIFICACIÓN DE ESTADO
# =============================================================================
log "🔍 Verificando estado de las migraciones..."

pipenv run python scripts/check_migration_status.py || warn "Verificación de estado completada con advertencias"

# =============================================================================
# 7. INICIO DEL SERVIDOR
# =============================================================================
log "🚀 Iniciando servidor FastAPI..."

# Configurar variables para producción
export PYTHONPATH="${PYTHONPATH}:."

# Obtener puerto desde variable de entorno de Render o usar 8000 por defecto
PORT=${PORT:-8000}

success "🎉 Iniciando aplicación en puerto $PORT"

# Iniciar con Uvicorn
exec pipenv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --log-level info \
    --access-log

