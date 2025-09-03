# 🏢 Cambios en API de Tenants - Frontend Update

## 📝 Resumen
Se implementó **soft delete** y campo de **tenant de prueba** en el sistema de tenants.

## 🔧 Cambios en API Response

### Tenant Response ahora incluye:
```json
{
  "id": 1,
  "nombre": "Mi Empresa",
  "subdominio": "mi_empresa",
  "token": "abc-123",
  "schema_name": "miempresa_abc123",
  "active": true,          // ✨ NUEVO
  "is_trial": false,       // ✨ NUEVO  
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 🎯 Cambios de Comportamiento

### 1. **Listado de Tenants**
- **Por defecto**: Solo muestra tenants activos (`active: true`)
- **Para ver todos**: Agregar parámetro `include_inactive=true`

### 2. **Eliminación de Tenants** 
- **DELETE /tenants/{id}** ahora hace **soft delete** (marca `active: false`)
- **Los datos NO se pierden** (a diferencia de antes)

### 3. **Creación de Tenants**
```json
// Request body ahora acepta:
{
  "nombre": "Mi Empresa",
  "subdominio": "mi_empresa", 
  "is_trial": true  // ✨ NUEVO - opcional, default: false
}
```

## 🔄 Nuevos Endpoints Disponibles

### Restaurar Tenant
```http
POST /tenants/{id}/restore
```

### Eliminación Permanente (solo para admins)
```http
DELETE /tenants/{id}/permanent
```

## 💡 Recomendaciones Frontend

1. **UI de Listado**: Agregar filtro/toggle "Mostrar inactivos"
2. **Botón Eliminar**: Cambiar texto a "Desactivar" 
3. **Tenants Inactivos**: Mostrar con estilo diferente (gris/tachado)
4. **Botón Restaurar**: Para tenants inactivos
5. **Badge "PRUEBA"**: Para tenants con `is_trial: true`

## ⚠️ Breaking Changes
- Las respuestas de tenant ahora incluyen 2 campos nuevos
- El comportamiento de DELETE cambió (ya no es destructivo)

## 🧪 Para Testing
Todos los tenants existentes automáticamente tienen:
- `active: true` 
- `is_trial: false`
