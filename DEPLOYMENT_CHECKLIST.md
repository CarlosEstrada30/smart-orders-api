# ✅ Checklist de Despliegue - Smart Orders API

## 🎯 Pre-Despliegue

### 📂 Archivos Necesarios
- [ ] `entrypoint.sh` - Script principal de arranque
- [ ] `render.yaml` - Configuración de Render
- [ ] `Pipfile` y `Pipfile.lock` - Dependencias con pipenv
- [ ] `.renderignore` - Archivos a ignorar en Render
- [ ] Scripts de migración actualizados

### 🔧 Configuración Local
- [ ] Variables de entorno configuradas en `.env`
- [ ] Base de datos PostgreSQL funcionando
- [ ] Migraciones del schema público funcionando
- [ ] Migraciones multitenant funcionando
- [ ] Health checks pasando

### 🧪 Testing Pre-Despliegue
```bash
# Ejecutar test completo de despliegue
pipenv run python scripts/test_deployment.py
```

## 🚀 Despliegue en Render

### 🗄️ Base de Datos
- [ ] PostgreSQL service creado en Render
- [ ] Plan apropiado seleccionado (Starter/Standard)
- [ ] Region seleccionada
- [ ] Connection string copiado

### 🌐 Web Service  
- [ ] Repositorio GitHub conectado
- [ ] `render.yaml` detectado automáticamente
- [ ] Variables de entorno configuradas:
  - [ ] `DATABASE_URL` 
  - [ ] `SECRET_KEY`
  - [ ] `ENVIRONMENT=production`
  - [ ] `PIPENV_VENV_IN_PROJECT=1`

### 🔍 Verificación Post-Despliegue
- [ ] Servicio desplegado sin errores
- [ ] Health check básico: `/health` 
- [ ] Health check detallado: `/health/detailed`
- [ ] Documentación accesible: `/docs`
- [ ] API funcionando correctamente

## 📋 Variables de Entorno por Entorno

### 🏠 Desarrollo Local
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_orders_db
SECRET_KEY=your-dev-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
```

### 🚀 Producción (Render)
```bash
DATABASE_URL=[Auto-generado desde PostgreSQL service]
SECRET_KEY=[Auto-generado por Render]
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
PIPENV_VENV_IN_PROJECT=1
```

## 🆘 Troubleshooting Común

### ❌ Error: "pipenv not found"
**Solución**: Render debe instalar pipenv en `buildCommand`
```yaml
buildCommand: pip install --upgrade pip pipenv
```

### ❌ Error: "Database connection failed" 
**Solución**: Verificar `DATABASE_URL` y que la BD esté en la misma región

### ❌ Error: "SECRET_KEY missing"
**Solución**: Configurar en Environment Variables de Render

### ❌ Error: "Module not found"
**Solución**: Verificar que todas las dependencias estén en `Pipfile`

### ❌ Error: "Migration failed"
**Solución**: Revisar logs de migraciones en el deploy log

## 🔄 Comandos Útiles

### Local Testing:
```bash
# Test completo de despliegue
pipenv run python scripts/test_deployment.py

# Solo health checks
pipenv run python scripts/health_check.py  

# Solo migraciones
pipenv run python scripts/migrate_all_schemas.py

# Simular entrypoint
./entrypoint.sh
```

### Render Debugging:
```bash
# Ver logs en tiempo real desde dashboard de Render
# O usar Render CLI si está instalado
render logs -s [service-id]
```

## 📊 Monitoring Post-Despliegue

### Health Endpoints:
- `GET /` - Info básica de la API
- `GET /health` - Health check básico
- `GET /health/detailed` - Health check completo
- `GET /docs` - Documentación Swagger

### Métricas a Monitorear:
- Response time de endpoints
- Database connection status  
- Memory usage
- Error rate
- Tenant migration status

## 💰 Costos Estimados

### Desarrollo:
- Web Service: $0/mes (Starter + auto-suspend)
- PostgreSQL: $7/mes (Starter)
- **Total: ~$7/mes**

### Producción:
- Web Service: $25/mes (Standard)  
- PostgreSQL: $25/mes (Standard)
- **Total: ~$50/mes**

## 🎉 Listo para Producción

Una vez completado este checklist:

1. ✅ Commit todos los cambios
2. ✅ Push a GitHub  
3. ✅ Crear servicios en Render
4. ✅ Configurar variables de entorno
5. ✅ Deploy automático vía render.yaml
6. ✅ Verificar endpoints funcionando
7. ✅ Configurar monitoring (opcional)

🎯 **Tu API multitenant estará lista y desplegada!**

