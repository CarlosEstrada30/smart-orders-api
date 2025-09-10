# 🚀 Guía de Despliegue en Render

Esta guía te ayuda a desplegar Smart Orders API en Render con configuración multitenant completa.

## 📋 Prerrequisitos

1. **Cuenta en Render**: [render.com](https://render.com)
2. **Repositorio GitHub**: Tu código debe estar en GitHub  
3. **Base de datos PostgreSQL** (puedes usar Render PostgreSQL)
4. **Pipenv configurado**: Este proyecto usa `Pipfile` en lugar de `requirements.txt`

### 🔧 ¿Por qué pipenv?

**Ventajas sobre requirements.txt:**
- ✅ **Lockfile determinístico**: `Pipfile.lock` garantiza builds reproducibles
- ✅ **Separación dev/prod**: Dependencias de desarrollo separadas
- ✅ **Resolución de dependencias**: Maneja conflictos automáticamente  
- ✅ **Virtual environments**: Manejo automático de entornos virtuales
- ✅ **Seguridad**: Verificación de hashes de paquetes

## ⚙️ Configuración Paso a Paso

### 1. 📦 Preparar el Repositorio

Asegúrate de que tu repositorio contenga estos archivos:

```
├── entrypoint.sh          # ✅ Script de entrada principal
├── render.yaml            # ✅ Configuración de Render  
├── scripts/
│   ├── migrate_all_schemas.py    # ✅ Migraciones multitenant
│   ├── check_migration_status.py # ✅ Verificador de estado
│   └── health_check.py           # ✅ Health checks detallados
├── Pipfile                # ✅ Dependencias de Python (pipenv)
├── Pipfile.lock           # ✅ Versiones exactas (pipenv)
└── app/                   # ✅ Código de la aplicación
```

### 2. 🗄️ Crear Base de Datos en Render

1. Ve a tu Dashboard de Render
2. Click en **"New PostgreSQL"**
3. Configuración recomendada:
   ```
   Name: smart-orders-db
   Database: smart_orders_db
   User: postgres
   Plan: Starter (para desarrollo) / Standard+ (para producción)
   Region: Oregon (o tu región preferida)
   ```

### 3. 🌐 Crear Web Service

#### Opción A: Usando render.yaml (Recomendado)

1. Asegúrate que `render.yaml` esté en la raíz de tu repositorio
2. En Render, click **"New"** → **"Blueprint"**
3. Conecta tu repositorio de GitHub
4. Render detectará automáticamente el `render.yaml`
5. Review la configuración y click **"Apply"**

#### Opción B: Configuración Manual

1. Click **"New Web Service"**
2. Conecta tu repositorio de GitHub
3. Configuración:
   ```
   Name: smart-orders-api
   Environment: Python 3
   Build Command: 
     apt-get update && apt-get install -y postgresql-client && 
     pip install --upgrade pip pipenv
   
   Start Command: ./entrypoint.sh
   Plan: Starter (para desarrollo)
   ```

### 4. 🔧 Variables de Entorno

Configura estas variables en tu Web Service:

#### Variables Requeridas:
```bash
# Base de datos (auto-generada si usas Render PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# Autenticación
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Entorno
ENVIRONMENT=production
PYTHON_VERSION=3.8
PIPENV_VENV_IN_PROJECT=1
```

#### Variables Opcionales:
```bash
# FEL Integration (si aplica)
FEL_BASE_URL=https://your-fel-service.com
FEL_API_KEY=your-fel-api-key

# Configuración de logging
LOG_LEVEL=INFO
```

### 5. 🔗 Conectar Base de Datos

Si creaste la BD en Render:

1. Ve a tu PostgreSQL service
2. Copia la **Connection String**
3. En tu Web Service, configura:
   ```
   DATABASE_URL = [pegar connection string aquí]
   ```

O usa la configuración automática del `render.yaml`.

## 🔄 Proceso de Despliegue

El `entrypoint.sh` ejecuta automáticamente:

1. ✅ **Validación de variables de entorno**
2. ✅ **Instalación de dependencias con pipenv**
3. ✅ **Espera de disponibilidad de la BD**
4. ✅ **Migraciones del schema público**
5. ✅ **Migraciones de todos los schemas de tenants**
6. ✅ **Verificación de estado**
7. ✅ **Inicio del servidor FastAPI**

### Logs de Ejemplo:
```
🔍 Validando variables de entorno...
✅ Variables de entorno validadas

📦 Instalando dependencias con pipenv...
✅ Dependencias instaladas

⏳ Esperando disponibilidad de la base de datos...
✅ Base de datos disponible

🏢 Ejecutando migraciones del schema público...
✅ Migraciones del schema público completadas

🏬 Ejecutando migraciones multitenant...
✅ Migraciones multitenant completadas

🚀 Iniciando servidor FastAPI...
✅ 🎉 Iniciando aplicación en puerto 10000
```

## 🔍 Verificación del Despliegue

### Health Checks Disponibles:

1. **Basic Health Check**: `https://your-app.onrender.com/health`
   ```json
   {
     "status": "healthy",
     "service": "smart-orders-api",
     "environment": "production",
     "database": "connected"
   }
   ```

2. **Detailed Health Check**: `https://your-app.onrender.com/health/detailed`
   ```json
   {
     "status": "healthy",
     "checks": {
       "database": {"status": "healthy", "message": "Database connection OK"},
       "migrations": {"status": "healthy", "message": "Migrations OK"},
       "environment": {"status": "healthy", "message": "Environment variables OK"}
     }
   }
   ```

3. **API Documentation**: `https://your-app.onrender.com/docs`

## 🛠️ Debugging y Troubleshooting

### Ver Logs en Tiempo Real:
```bash
# En el dashboard de Render, ve a tu servicio y click en "Logs"
```

### Problemas Comunes:

#### 1. Error de Variables de Entorno
```
❌ Variables de entorno faltantes: SECRET_KEY
```
**Solución**: Configura la variable faltante en Environment Variables

#### 2. Error de Conexión a BD
```
❌ No se pudo conectar a la base de datos
```
**Solución**: 
- Verifica que `DATABASE_URL` esté correcto
- Asegúrate que la BD esté en la misma región
- Revisa que el usuario/password sean correctos

#### 3. Error de Migraciones
```
❌ Falló la migración del schema público
```
**Solución**:
- Verifica que Alembic esté configurado correctamente
- Revisa los archivos de migración en `alembic/versions/`

#### 4. Timeout en el Start Command
**Solución**:
- Incrementa el timeout en Render (si disponible)
- Optimiza el tiempo de inicio reduciendo operaciones en `entrypoint.sh`

### Comandos de Debug:

```bash
# Probar entrypoint localmente
./entrypoint.sh

# Verificar health checks
pipenv run python scripts/health_check.py

# Verificar migraciones
pipenv run python scripts/check_migration_status.py
```

## 🔄 CI/CD y Auto-Deploy

### Auto-Deploy desde GitHub:
- Render automáticamente redespliega cuando haces push a tu branch principal
- Configurable en Settings → Build & Deploy

### Workflow Recomendado:
1. 🔧 Desarrollo local con `pipenv shell`
2. ✅ Testing con `pipenv run pytest`
3. 📤 Push a GitHub
4. 🚀 Auto-deploy en Render
5. 🔍 Verificación con health checks

## 💰 Costos Estimados

### Plan Starter (Desarrollo):
- **Web Service**: $0/mes (suspende después de 15min de inactividad)
- **PostgreSQL**: $7/mes (1GB storage, 1GB RAM)
- **Total**: ~$7/mes

### Plan Standard (Producción):
- **Web Service**: $25/mes (siempre activo, 2GB RAM)
- **PostgreSQL**: $25/mes (10GB storage, 4GB RAM)
- **Total**: ~$50/mes

## 🔧 Configuración Avanzada

### Escalabilidad:
- Para más tráfico, cambia a plan **Pro** ($85/mes)
- Considera **multiple workers** en uvicorn para plan Standard+

### Monitoring:
- Render incluye métricas básicas gratis
- Para monitoring avanzado, integra con Sentry o similar

### Backup:
- Render PostgreSQL incluye backups diarios automáticos
- Para backups manuales, usa `pg_dump`

## 🎯 Checklist Final

Antes de ir a producción:

- [ ] ✅ Variables de entorno configuradas
- [ ] ✅ SSL habilitado (automático en Render)  
- [ ] ✅ CORS configurado correctamente
- [ ] ✅ Health checks funcionando
- [ ] ✅ Migraciones funcionando
- [ ] ✅ Documentación API accesible
- [ ] ✅ Logs monitoreando correctamente
- [ ] ✅ Plan de backup configurado

## 📞 Soporte

- **Documentación Render**: [docs.render.com](https://docs.render.com)
- **Community**: [community.render.com](https://community.render.com)
- **Status**: [status.render.com](https://status.render.com)

---

🎉 **¡Listo! Tu API multitenant está desplegada en Render**
