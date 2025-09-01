# Creación de Tenants con Superusuario Automático

Este documento describe el proceso de creación de tenants en el sistema multi-tenant, incluyendo la creación automática de un superusuario.

## 🏢 Proceso de Creación de Tenant

### Endpoint de Creación

**POST** `/api/v1/tenants/`

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "nombre": "Mi Empresa",
    "subdominio": "miempresa"
}
```

**Response (201):**
```json
{
    "id": 1,
    "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Mi Empresa",
    "subdominio": "miempresa", 
    "schema_name": "miempresa_a1b2c3d4e5f67890abcdef1234567890",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

## 🔄 Proceso Automatizado

Cuando se crea un tenant, el sistema ejecuta automáticamente estos pasos:

### 1. Creación del Registro
- Se crea el registro del tenant en el esquema `public`
- Se genera automáticamente un token UUID único
- Se genera el nombre del schema: `{nombre_limpio}_{token}`

### 2. Creación del Schema de Base de Datos
- Se crea un nuevo schema PostgreSQL con el nombre generado
- El schema queda aislado del resto de tenants

### 3. Ejecución de Migraciones
- Se ejecutan todas las migraciones de Alembic en el nuevo schema
- Se crean todas las tablas necesarias para el tenant

### 4. Creación de Superusuario Automático ✨

**El sistema crea automáticamente un superusuario con:**

- **Email:** `admin@{subdominio}.com`
- **Password:** `admin{subdominio}123`
- **Username:** `admin_{subdominio}`
- **Full Name:** `Administrador {Subdominio}`
- **Role:** `ADMIN`
- **is_superuser:** `True`

#### Ejemplo con subdominio "bethel":
- **Email:** `admin@bethel.com`
- **Password:** `adminbethel123`
- **Username:** `admin_bethel`
- **Full Name:** `Administrador Bethel`

## 📝 Ejemplo Completo de Uso

### 1. Crear el Tenant

```bash
curl -X POST "http://localhost:8000/api/v1/tenants/" \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "nombre": "Bethel Company",
       "subdominio": "bethel"
     }'
```

### 2. Login con el Superusuario Creado

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@bethel.com",
       "password": "adminbethel123",
       "subdominio": "bethel"
     }'
```

**JWT Response Structure:**
```json
{
  "sub": "admin@bethel.com",
  "tenant": {
    "tenant_id": 9,
    "tenant_schema": "lacteosbethel_3cf22284-02d4-4aff-97d1-9d27b28cc9b4",
    "tenant_name": "Lacteos Bethel",
    "tenant_subdomain": "bethel"
  },
  "exp": 1756705136
}
```

## 🔒 Consideraciones de Seguridad

### Fortalezas
- **Credenciales Predecibles pero Únicas:** Cada tenant tiene sus propias credenciales
- **Aislamiento Completo:** Cada superusuario solo tiene acceso a su propio schema
- **Rol Administrativo:** El usuario creado tiene permisos completos dentro de su tenant

### Recomendaciones
1. **Cambiar Password Inmediatamente:** El superusuario debe cambiar su password tras el primer login
2. **Comunicación Segura:** Entregar las credenciales de forma segura al cliente
3. **Auditoría:** Registrar y monitorear el uso de estas cuentas

## 🛠️ Testing

Se proporciona un script de testing completo:

```bash
python test_tenant_creation_with_admin.py
```

Este script:
1. Crea un tenant de prueba
2. Verifica que el superusuario se haya creado
3. Prueba el login con las credenciales generadas
4. Analiza los claims del JWT resultante

## 🚨 Manejo de Errores

### Errores Posibles en la Creación

**400 - Bad Request:**
- Subdominio ya existe
- Datos inválidos

**403 - Forbidden:**
- Usuario sin permisos de administrador

**500 - Internal Server Error:**
- Error creando el schema
- Error ejecutando migraciones
- Error creando el superusuario (no impide la creación del tenant)

### Logs Importantes

El sistema registra:
- Creación exitosa del tenant
- Creación exitosa del superusuario
- Advertencias si no se puede crear el superusuario
- Errores en cualquier paso del proceso

## 📊 Ejemplo de Response Completa

```json
{
    "id": 5,
    "token": "12345678-90ab-cdef-1234-567890abcdef",
    "nombre": "Bethel Company",
    "subdominio": "bethel",
    "schema_name": "bethelcompany_1234567890abcdef1234567890abcdef",
    "created_at": "2024-01-15T14:30:00.123456Z",
    "updated_at": "2024-01-15T14:30:00.123456Z"
}
```

**Superusuario creado automáticamente:**
- Email: `admin@bethel.com`
- Password: `adminbethel123`
- Listo para usar inmediatamente

## 🔄 Flujo de Trabajo Recomendado

1. **Administrador del Sistema:** Crea el tenant via API
2. **Sistema:** Ejecuta todo el proceso automatizado
3. **Administrador del Sistema:** Entrega credenciales al cliente
4. **Cliente:** Hace login con `admin@{subdominio}.com`
5. **Cliente:** Cambia password y comienza a usar el sistema
6. **Cliente:** Crea usuarios adicionales según necesite

Este proceso garantiza que cada tenant tenga acceso inmediato a su sistema con un usuario administrativo completamente funcional.
