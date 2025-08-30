# 👥 Sistema de Roles de Usuario

## 🎯 Roles Implementados

### 1. **👷 EMPLOYEE (Empleado)**
- **Inventario**: Crear entradas (DRAFT), ver propias entradas
- **Productos**: Ver catálogo y stock básico
- **Sin acceso a**: Pedidos, ventas, aprobaciones, costos

### 2. **💼 SALES (Vendedor)**
- **Pedidos**: Crear, gestionar y ver todos los pedidos
- **Clientes**: Gestionar información completa de clientes
- **Productos**: Ver catálogo con precios de venta
- **Rutas**: Ver rutas disponibles para asignar
- **Sin acceso a**: Inventario, costos de compra, configuraciones

### 3. **🚚 DRIVER (Repartidor)**
- **Pedidos**: Ver pedidos asignados, marcar como entregados
- **Clientes**: Ver información básica para entregas
- **Rutas**: Ver solo sus rutas asignadas
- **Productos**: Ver información básica de productos
- **Sin acceso a**: Crear pedidos, inventario, costos

### 4. **👨‍💼 SUPERVISOR (Supervisor)**
- **Todo lo de SALES +**
- **Inventario**: Aprobar y completar entradas
- **Productos**: Gestionar catálogo completo
- **Rutas**: Crear y gestionar rutas
- **Pedidos**: Resolver problemas y cancelar
- **Sin acceso a**: Configuración usuarios, reportes financieros

### 5. **👔 MANAGER (Gerente/Dueño)**
- **Todo lo de SUPERVISOR +**
- **Finanzas**: Ver costos y márgenes
- **Reportes**: Acceso a reportes de ganancias
- **Configuración**: Precios y políticas
- **Sin acceso a**: Administración técnica del sistema

### 6. **⚙️ ADMIN (Administrador)**
- **Acceso completo al sistema**
- **Usuarios**: Crear, editar, desactivar usuarios
- **Configuración**: Todas las configuraciones técnicas
- **Soporte**: Acceso para mantenimiento y debugging

## 🔐 Permisos Detallados

| Función | Employee | Sales | Driver | Supervisor | Manager | Admin |
|---------|----------|-------|--------|------------|---------|-------|
| **Inventario** |
| Crear entradas | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Aprobar entradas | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Completar entradas | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Ver costos inventario | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Productos** |
| Ver catálogo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver precios venta | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Crear/editar productos | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Ver costos de compra | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Pedidos** |
| Crear pedidos | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Ver pedidos | ❌ | ✅ | ✅* | ✅ | ✅ | ✅ |
| Marcar entregado | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cancelar pedidos | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Clientes** |
| Ver clientes | ❌ | ✅ | ✅* | ✅ | ✅ | ✅ |
| Gestionar clientes | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Rutas** |
| Ver rutas | ❌ | ✅ | ✅* | ✅ | ✅ | ✅ |
| Gestionar rutas | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Reportes** |
| Reportes básicos | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Reportes financieros | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Usuarios** |
| Gestionar usuarios | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Nota**: Los permisos marcados con * para DRIVER son limitados a sus rutas asignadas.

## 🚀 Uso en el Frontend

### 1. **Obtener permisos del usuario actual:**
```javascript
// GET /api/v1/auth/permissions
const response = await fetch('/api/v1/auth/permissions', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const permissions = await response.json();

console.log(permissions);
/*
{
  "role": "supervisor",
  "is_superuser": false,
  "permissions": {
    "inventory": {
      "can_manage": true,
      "can_approve": true,
      "can_complete": true
    },
    "orders": {
      "can_manage": true
    },
    "products": {
      "can_manage": true,
      "can_view_costs": false
    },
    // ...
  }
}
*/
```

### 2. **Mostrar/ocultar elementos según permisos:**
```javascript
// Mostrar botón de aprobar solo si tiene permisos
if (permissions.inventory.can_approve) {
  showApproveButton();
}

// Ocultar costos si no puede verlos
if (!permissions.products.can_view_costs) {
  hideCostColumns();
}
```

### 3. **Validar antes de llamar API:**
```javascript
const approveEntry = async (entryId) => {
  if (!permissions.inventory.can_approve) {
    alert('No tienes permisos para aprobar entradas');
    return;
  }
  
  // Llamar API...
};
```

## 🔧 Configuración Inicial

### 1. **Ejecutar migración (agregar roles a usuarios existentes):**
```bash
cd /home/carlos/Documents/apis/smart-orders-api
python scripts/add_user_roles.py
```

### 2. **Crear usuarios de ejemplo:**
Los siguientes usuarios te serían útiles para una empresa pequeña:

```
admin@empresa.com      → ADMIN      (configuración sistema)
gerente@empresa.com    → MANAGER    (supervisión general)
supervisor@empresa.com → SUPERVISOR (aprobaciones diarias)
vendedor1@empresa.com  → SALES      (ventas y pedidos)
vendedor2@empresa.com  → SALES      (ventas y pedidos)
repartidor1@empresa.com → DRIVER     (entregas)
repartidor2@empresa.com → DRIVER     (entregas)
empleado1@empresa.com  → EMPLOYEE   (almacén/producción)
empleado2@empresa.com  → EMPLOYEE   (almacén/producción)
```

### 3. **Gestión de Usuarios y Roles:**

#### **Crear nuevo usuario con rol:**
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@empresa.com",
    "username": "nuevo_usuario", 
    "full_name": "Nuevo Usuario",
    "password": "password123",
    "role": "sales",
    "is_active": true
  }'
```

#### **Asignar rol a usuario existente:**
```bash
curl -X POST http://localhost:8000/api/v1/users/5/assign-role \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '"manager"'
```

#### **Ver roles disponibles:**
```bash
curl http://localhost:8000/api/v1/users/roles/available \
  -H "Authorization: Bearer {admin_token}"
```

#### **Actualizar perfil propio (cualquier usuario):**
```bash
curl -X PUT http://localhost:8000/api/v1/users/5 \
  -H "Authorization: Bearer {user_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Nombre Actualizado",
    "email": "nuevo_email@empresa.com"
  }'
```

#### **Actualizar usuario con rol (solo ADMIN):**
```bash
curl -X PUT http://localhost:8000/api/v1/users/5 \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Usuario Actualizado",
    "role": "supervisor",
    "is_active": false
  }'
```

## 🚨 Validaciones Implementadas

### Endpoints con validación de roles:

**Inventario:**
```
POST /api/v1/inventory/entries/{id}/approve   → Requiere SUPERVISOR+
POST /api/v1/inventory/entries/{id}/complete  → Requiere SUPERVISOR+
```

**Pedidos:**
```
POST /api/v1/orders/                          → Requiere SALES+
GET  /api/v1/orders/                          → Requiere SALES, DRIVER o superior
POST /api/v1/orders/{id}/status/delivered     → Requiere DRIVER+ (solo para entregado)
POST /api/v1/orders/{id}/status/{other}       → Requiere SALES+ (otros estados)
```

**Usuarios:**
```
POST /api/v1/users/                           → Requiere ADMIN
GET  /api/v1/users/                           → Requiere ADMIN
GET  /api/v1/users/{id}                       → ADMIN o propio perfil
PUT  /api/v1/users/{id}                       → ADMIN o propio perfil*
DELETE /api/v1/users/{id}                     → Requiere ADMIN
POST /api/v1/users/{id}/assign-role           → Requiere ADMIN
GET  /api/v1/users/roles/available            → Requiere ADMIN
```

**Nota**: * Los usuarios pueden editar su perfil básico, pero solo ADMIN puede cambiar roles/permisos.

### Respuestas de error:
```json
{
  "detail": "No tienes permisos para aprobar entradas de inventario. Se requiere rol de Supervisor o superior."
}
```

## 📈 Escalabilidad Futura

Este sistema básico se puede expandir fácilmente:

### Roles adicionales:
- `SALES` - Vendedor especializado
- `DRIVER` - Repartidor
- `ACCOUNTANT` - Contador
- `INVENTORY_MANAGER` - Jefe de almacén

### Permisos granulares:
- Permisos por departamento
- Permisos temporales
- Restricciones por horario
- Aprobaciones por monto

### Configuración dinámica:
- Roles configurables desde admin panel
- Permisos personalizables por empresa
- Workflows de aprobación complejos

## 🎯 Próximos Pasos

1. **Probar el sistema** con usuarios de diferentes roles
2. **Implementar validaciones** en más endpoints según necesites
3. **Configurar el frontend** para mostrar/ocultar elementos
4. **Crear usuarios reales** para tu empresa
5. **Documentar flujos** específicos de tu negocio
