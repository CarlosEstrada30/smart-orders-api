# Scripts de Migraciones Multitenant

Este directorio contiene scripts para manejar migraciones de base de datos en una arquitectura multitenant donde cada tenant tiene su propio schema.

## 📋 Scripts Disponibles

### 1. `check_migration_status.py` - Verificación de Estado (Dry-run)
**Propósito**: Reporta el estado actual de migraciones sin ejecutar cambios.

```bash
# Ejecutar verificación
pipenv run python scripts/check_migration_status.py
./scripts/check_migration_status.py
```

**Qué hace:**
- ✅ Consulta **directamente** los schemas de la BD (no depende de tabla tenants)
- ✅ Reporta el estado de migraciones en cada schema
- ✅ Identifica schemas "huérfanos" (sin registro en tabla tenants)
- ✅ Lista información adicional de tenants registrados
- ✅ Proporciona recomendaciones de acción

### 2. `migrate_all_schemas.py` - Migración Completa (Python)
**Propósito**: Ejecuta migraciones de Alembic en todos los schemas con reporte detallado.

```bash
# Ejecutar migraciones completas
pipenv run python scripts/migrate_all_schemas.py
./scripts/migrate_all_schemas.py
```

**Características:**
- 🔄 Migra schema `public` primero
- 🔄 Consulta **directamente** la BD para obtener todos los schemas
- 🔄 Migra **TODOS** los schemas (no solo tenants activos)
- 📊 Reporte detallado de éxito/errores
- ⏱️ Timeout de 5 minutos por migración
- 🛡️ Manejo robusto de errores
- 📋 Resumen final con estadísticas

### 3. `migrate_all_schemas_simple.sh` - Migración Rápida (Bash)
**Propósito**: Versión más rápida y simple para uso cotidiano.

```bash
# Ejecutar migraciones rápidas
./scripts/migrate_all_schemas_simple.sh
```

**Características:**
- ⚡ Más rápido que la versión Python
- 🔄 Consulta **directamente** la BD para schemas
- 🔄 Migra `public` y **todos** los schemas
- 📊 Contador de éxito/errores
- 🎯 Perfecto para CI/CD y uso diario

## 🏗️ Arquitectura Multitenant

### Estructura de Schemas
```
postgresql_database
├── public/                    # Schema principal (usuarios, tenants, etc.)
├── lacteosbethel_<uuid>/     # Schema del tenant 1 (registrado)
├── nuevotenant_<uuid>/       # Schema del tenant 2 (huérfano)
├── miempresa_<uuid>/         # Schema del tenant 3 (registrado)
└── otroschema/               # Cualquier otro schema existente
```

### ⚠️ **CAMBIO IMPORTANTE**: Consulta Directa de Schemas

Los scripts **YA NO** dependen de la tabla `tenants` del schema `public`. Ahora:

1. **Consultan directamente** `information_schema.schemata`
2. **Migran TODOS los schemas** que encuentren (excepto system schemas)
3. **Incluyen schemas "huérfanos"** que no están registrados en tabla tenants
4. **Más robusto** - no falla si la tabla tenants tiene problemas

### Flujo de Migración
1. **Schema Public**: Se migra primero (contiene tabla `tenants`)
2. **Schemas de Tenants**: Se migran **todos** los schemas encontrados usando `search_path`
3. **Verificación**: Cada schema mantiene su propia tabla `alembic_version`
4. **Sin exclusiones**: Migra schemas activos, inactivos, huérfanos, etc.

## 🚀 Casos de Uso Comunes

### Configuración Inicial (Primera vez)
```bash
# 1. Crear migración inicial
pipenv run alembic revision --autogenerate -m "Initial migration"

# 2. Aplicar a todos los schemas existentes
./scripts/migrate_all_schemas_simple.sh
```

### Después de Agregar Nuevas Migraciones
```bash
# 1. Crear nueva migración
pipenv run alembic revision --autogenerate -m "Add new feature"

# 2. Aplicar a todos los schemas
./scripts/migrate_all_schemas_simple.sh
```

### Verificar Estado Actual
```bash
# Ver qué schemas necesitan migraciones
pipenv run python scripts/check_migration_status.py
```

### Schemas Huérfanos o Problemas
```bash
# 1. Verificar estado (identifica schemas huérfanos)
pipenv run python scripts/check_migration_status.py

# 2. Migrar TODOS los schemas (incluye huérfanos)
pipenv run python scripts/migrate_all_schemas.py
```

## ⚠️ Consideraciones Importantes

### Prerrequisitos
- ✅ **pipenv** instalado y configurado
- ✅ **alembic.ini** configurado correctamente  
- ✅ Variables de entorno (**.env**) configuradas
- ✅ Conexión a la base de datos funcionando

### Comportamiento Nuevo
1. **TODOS los schemas** se migran (no solo tenants activos)
2. **Schemas huérfanos** incluidos automáticamente
3. **No requiere** tabla tenants funcionando
4. **Más inclusivo** - migra cualquier schema encontrado

### Orden de Ejecución
1. El schema `public` **SIEMPRE** se migra primero
2. Los schemas de tenants se migran usando `search_path`
3. **TODOS** los schemas se procesan (sin filtros de activo/inactivo)

### Manejo de Errores
- Si falla `public`, se reporta pero continúa con tenants
- Si falla un schema, se reporta pero continúa con los demás
- Logs detallados disponibles en todas las versiones

### Performance
- **Script Simple**: ~2-5 segundos por schema
- **Script Python**: ~5-10 segundos por schema (más logging)
- **Timeout**: 5 minutos máximo por migración individual

## 🔧 Troubleshooting

### Error: "pipenv not found"
```bash
# Instalar pipenv
pip install pipenv

# O usar python directamente (modificar scripts)
python scripts/migrate_all_schemas.py
```

### Error: "alembic.ini not found"
```bash
# Ejecutar desde la raíz del proyecto
cd /path/to/smart-orders-api
./scripts/migrate_all_schemas_simple.sh
```

### Error: "Database connection failed"
```bash
# Verificar .env
cat .env | grep DATABASE_URL

# Probar conexión
pipenv run python -c "from app.database import engine; print(engine.connect())"
```

### Schema de Tenant No Registrado
Los scripts **ahora migran automáticamente** schemas huérfanos:
```bash
# Ver schemas huérfanos
pipenv run python scripts/check_migration_status.py

# Migrar todos (incluye huérfanos)
pipenv run python scripts/migrate_all_schemas.py
```

## 📊 Ejemplo de Output

### check_migration_status.py
```
📊 REPORTE DE ESTADO DE MIGRACIONES MULTITENANT
=================================================================

🏗️  SCHEMAS EN LA BASE DE DATOS
Total schemas: 5
   - Schema público: 1
   - Schemas de tenants: 3
   - Schemas del sistema: 1

🏢 ESTADO DEL SCHEMA PÚBLICO
   ✅ Versión actual: 0a10ddc75bd6

👥 INFORMACIÓN DE TENANTS
Total tenants registrados: 2
   - Activos: 2
   - Inactivos: 0

🏬 ESTADO DE MIGRACIONES - TODOS LOS SCHEMAS DE TENANTS
-------------------------------------------------------------------------------------
#   Schema                              Estado Migración          Existe en tabla tenants
-------------------------------------------------------------------------------------
1   lacteosbethel_325c8cbe-eb8b-4fcb-a  ✅ 0a10ddc75bd6            ✅ Sí                
2   miempresa_789abc12-3456-7890       ✅ 0a10ddc75bd6            ✅ Sí                
3   nuevotenant-325654645               ❌ Sin alembic_version     ⚠️  No              

⚠️  SCHEMAS HUÉRFANOS (sin registro en tabla tenants)
Total: 1 schemas
   - nuevotenant-325654645 (Sin versión)
```

### migrate_all_schemas.py
```
🚀 Iniciando migraciones multitenant...
============================================================

🏢 Migrando schema 'public'...
   ✅ Migración exitosa - Nueva versión: 0a10ddc75bd6

🏬 Obteniendo schemas de tenants desde la base de datos...
   📊 Se encontraron 3 schemas de tenants

🏢 [1/3] Migrando schema: lacteosbethel_325c8cbe-eb8b-4fcb-ad49-c4f62b5e6730
   ✅ Migración exitosa - Nueva versión: 0a10ddc75bd6

🏢 [2/3] Migrando schema: miempresa_789abc12-3456-7890-abcd-ef1234567890  
   ✅ Migración exitosa - Nueva versión: 0a10ddc75bd6

🏢 [3/3] Migrando schema: nuevotenant-325654645 (HUÉRFANO)
   ✅ Migración exitosa - Nueva versión: 0a10ddc75bd6

============================================================
📊 RESUMEN DE MIGRACIONES
============================================================
Total schemas procesados: 3
✅ Exitosos: 3
❌ Fallidos: 0

🎉 ¡Todas las migraciones completadas exitosamente!
```

## 🔄 Integración con CI/CD

### GitHub Actions Example
```yaml
- name: Run Database Migrations (All Schemas)
  run: |
    pipenv install
    ./scripts/migrate_all_schemas_simple.sh
```

### Docker Compose
```yaml
services:
  migrate:
    build: .
    command: "./scripts/migrate_all_schemas_simple.sh"
    depends_on:
      - db
```

## 💡 Ventajas del Nuevo Enfoque

### ✅ **Antes** (basado en tabla tenants)
- Solo migraba tenants activos
- Fallaba si tabla tenants tenía problemas
- Ignoraba schemas huérfanos
- Dependía de registros correctos

### ✅ **Ahora** (consulta directa de schemas)
- Migra **TODOS** los schemas encontrados
- Funciona aunque tabla tenants esté corrupta
- Incluye schemas huérfanos automáticamente
- Más robusto y completo

---

## 📞 Soporte

Si encuentras problemas:
1. Ejecuta `pipenv run python scripts/check_migration_status.py` primero
2. Revisa los logs de error específicos
3. Verifica conexión a base de datos y configuración de schemas
4. Para problemas complejos, usa la versión Python detallada
5. Los scripts ahora son más tolerantes a schemas huérfanos y problemas