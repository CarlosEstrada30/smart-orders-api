#!/bin/bash

# Script simple para ejecutar migraciones en todos los schemas (multitenant)
# Versión bash más básica y rápida

set -e

echo "🚀 Iniciando migraciones multitenant (versión simple)..."
echo "========================================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "alembic.ini" ]; then
    echo "❌ Error: No se encontró alembic.ini"
    echo "   Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# Cargar variables de entorno
if [ -f ".env" ]; then
    echo "📂 Cargando variables de entorno..."
    export $(grep -v '^#' .env | xargs)
fi

# 1. Migrar schema public primero
echo ""
echo "🏢 Migrando schema 'public'..."
pipenv run alembic upgrade head
echo "✅ Schema 'public' migrado"

# 2. Obtener todos los schemas de tenants consultando directamente la base de datos
echo ""
echo "🏬 Obteniendo schemas de tenants desde la base de datos..."

TENANT_SCHEMAS=$(pipenv run python -c "
import sys, os
sys.path.append('.')
from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as connection:
        result = connection.execute(text('''
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
        '''))
        
        for row in result.fetchall():
            schema_name = row[0]
            print(f'{schema_name}:{schema_name}')
            
except Exception as e:
    print(f'ERROR:{e}', file=sys.stderr)
")

# Verificar si hay errores
if echo "$TENANT_SCHEMAS" | grep -q "ERROR:"; then
    echo "❌ Error obteniendo schemas:"
    echo "$TENANT_SCHEMAS" | grep "ERROR:" | cut -d: -f2-
    exit 1
fi

# Contar schemas
if [ -z "$TENANT_SCHEMAS" ] || [ "$TENANT_SCHEMAS" = "" ]; then
    echo "ℹ️  No se encontraron schemas de tenants"
    echo ""
    echo "🎉 ¡Migraciones completadas!"
    exit 0
fi

TENANT_COUNT=$(echo "$TENANT_SCHEMAS" | grep -c ':')

echo "📊 Se encontraron $TENANT_COUNT schemas de tenants"

# 3. Migrar cada schema de tenant
counter=1
successful=0
failed=0

while IFS=: read -r schema_display_name schema_name; do
    if [ -n "$schema_display_name" ] && [ -n "$schema_name" ]; then
        echo ""
        echo "🏢 [$counter/$TENANT_COUNT] Migrando schema: $schema_display_name"
        echo "   📂 Schema: $schema_name"
        
        # Configurar DATABASE_URL con search_path para el schema específico
        # Agregar comillas dobles si el schema tiene guiones u otros caracteres especiales
        # y encodificar correctamente para URL (%22 en lugar de ")
        if [[ "$schema_name" == *"-"* ]] || [[ "$schema_name" == *" "* ]] || [[ "$schema_name" == *"."* ]] || [[ "$schema_name" == *"+"* ]]; then
            QUOTED_SCHEMA="%22${schema_name}%22"
        else
            QUOTED_SCHEMA="${schema_name}"
        fi
        
        if [[ "$DATABASE_URL" == *"?"* ]]; then
            TENANT_DB_URL="${DATABASE_URL}&options=-csearch_path%3D${QUOTED_SCHEMA}"
        else
            TENANT_DB_URL="${DATABASE_URL}?options=-csearch_path%3D${QUOTED_SCHEMA}"
        fi
        
        # Ejecutar migración para este schema
        if DATABASE_URL="$TENANT_DB_URL" pipenv run alembic upgrade head 2>/dev/null; then
            echo "   ✅ Migración exitosa"
            ((successful++))
        else
            echo "   ❌ Error en migración"
            ((failed++))
        fi
        
        ((counter++))
    fi
done <<< "$TENANT_SCHEMAS"

# 4. Resumen
echo ""
echo ""
echo "========================================================="
echo "📊 RESUMEN DE MIGRACIONES"
echo "========================================================="
total_processed=$((counter > 1 ? counter-1 : 0))
echo "Total schemas procesados: $total_processed"
echo "✅ Exitosos: $successful"
echo "❌ Fallidos: $failed"

if [ $failed -eq 0 ]; then
    echo ""
    echo "🎉 ¡Todas las migraciones completadas exitosamente!"
else
    echo ""
    echo "⚠️  Algunas migraciones fallaron. Revisa los logs anteriores."
fi

# Always exit 0 unless there were critical failures
exit 0
