# Autenticación con Soporte Multi-Tenant

Este documento describe el sistema de autenticación actualizado con soporte para multi-tenancy mediante subdominios.

## 🏢 Flujo de Autenticación con Tenants

### 1. Nuevo Endpoint de Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body (ACTUALIZADO):**

Login con tenant específico:
```json
{
    "email": "admin@example.com",
    "password": "admin123",
    "subdominio": "empresa1"
}
```

Login en esquema público (sin tenant):
```json
{
    "email": "admin@example.com",
    "password": "admin123"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### 2. Proceso de Autenticación

El nuevo flujo de autenticación sigue estos pasos:

#### Caso 1: Sin subdominio (Esquema Public por defecto)
1. **Validación de Parámetros**: Si no se proporciona `subdominio`, se usa esquema `public`
2. **Autenticación Directa**: Se validan las credenciales en el esquema `public`
3. **Generación de JWT**: Se crea el token con claim `tenant_schema: "public"`

#### Caso 2: Con subdominio (Tenant específico)
1. **Búsqueda de Tenant**: Se busca el tenant por `subdominio` en el esquema `public`
2. **Validación de Tenant**: Si no existe el tenant, se retorna error 404
3. **Switch de Schema**: Se crea una sesión específica para el schema del tenant
4. **Autenticación de Usuario**: Se validan las credenciales en el schema del tenant
5. **Generación de JWT**: Se crea el token con claims completos del tenant

### 3. Claims del JWT

#### Login en Esquema Public (sin subdominio):
```json
{
    "sub": "admin@example.com",           // Email del usuario
    "tenant": {
        "tenant_schema": "public"         // Esquema público por defecto
    },
    "exp": 1640995200                    // Timestamp de expiración
}
```

#### Login con Tenant Específico (con subdominio):
```json
{
    "sub": "admin@example.com",           // Email del usuario
    "tenant": {
        "tenant_id": 1,                   // ID del tenant
        "tenant_schema": "empresa1_uuid123", // Schema del tenant
        "tenant_name": "Empresa 1",      // Nombre del tenant
        "tenant_subdomain": "empresa1"   // Subdominio del tenant
    },
    "exp": 1640995200                    // Timestamp de expiración
}
```

## 📝 Ejemplos de Uso

### Login en Esquema Public (Por defecto)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@example.com",
       "password": "admin123"
     }'
```

### Login con Tenant Específico

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@example.com",
       "password": "admin123",
       "subdominio": "empresa1"
     }'
```

**Respuesta exitosa (200):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBleGFtcGxlLmNvbSIsInRlbmFudCI6eyJ0ZW5hbnRfaWQiOjEsInRlbmFudF9zY2hlbWEiOiJlbXByZXNhMV91dWlkMTIzIiwidGVuYW50X25hbWUiOiJFbXByZXNhIDEiLCJ0ZW5hbnRfc3ViZG9tYWluIjoiZW1wcmVzYTEifSwiZXhwIjoxNjQwOTk1MjAwfQ...",
    "token_type": "bearer"
}
```

### Errores Posibles

**404 - Tenant no encontrado:**
```json
{
    "detail": "Tenant not found for the provided subdomain"
}
```

**401 - Credenciales incorrectas:**
```json
{
    "detail": "Incorrect email or password"
}
```

**400 - Usuario inactivo:**
```json
{
    "detail": "Inactive user"
}
```

## 🔧 Uso del Token

El token se usa de la misma manera que antes en el header Authorization:

```bash
curl -X GET "http://localhost:8000/api/v1/users" \
     -H "Authorization: Bearer <token>"
```

## 🛠️ Testing

Se proporciona un script de testing:

```bash
python test_tenant_login.py
```

Este script:
- Prueba el login con datos de tenant
- Decodifica el JWT para mostrar los claims
- Valida que todos los campos del tenant estén presentes

## 🔒 Consideraciones de Seguridad

1. **Aislamiento de Datos**: Cada tenant tiene su propio schema de base de datos
2. **Validación de Tenant**: Solo usuarios de un tenant específico pueden autenticarse en ese tenant
3. **Claims de Tenant**: El JWT contiene información del tenant agrupada bajo la propiedad "tenant"
4. **Sesiones Segregadas**: Las conexiones a base de datos se manejan por schema específico
5. **Estructura Organizada**: La información del tenant está anidada para mejor organización

## 📚 Migración desde la Versión Anterior

**¡Excelente noticia!** El endpoint es **completamente compatible con versiones anteriores**. 

Los clientes existentes NO necesitan cambios:

**Funciona igual que antes (esquema public):**
```json
{
    "email": "admin@example.com",
    "password": "admin123"
}
```

**Nuevo: Para usar tenant específico:**
```json
{
    "email": "admin@example.com", 
    "password": "admin123",
    "subdominio": "nombre_empresa"
}
```

## 🔍 Debugging

Para verificar los claims del JWT, puedes usar el script de testing o herramientas online como jwt.io (asegúrate de no compartir tokens reales).

Los logs del servidor mostrarán información sobre:
- Búsquedas de tenant
- Creación de sesiones específicas por schema
- Errores de autenticación por tenant
