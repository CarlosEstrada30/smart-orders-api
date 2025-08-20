# Sistema de Autenticación JWT

Este documento describe el sistema de autenticación JWT implementado en la Smart Orders API.

## 🔐 Flujo de Autenticación

### 1. Login del Usuario
El usuario proporciona sus credenciales (email y contraseña) al endpoint de login.

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
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

### 2. Uso del Token
El cliente debe incluir el token en el header `Authorization` de todas las peticiones a endpoints protegidos.

**Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Validación del Token
El sistema valida automáticamente el token JWT en cada petición a endpoints protegidos.

## 📋 Endpoints de Autenticación

### POST /api/v1/auth/login
Autentica al usuario y retorna un token JWT.

**Parámetros:**
- `email` (string): Email del usuario
- `password` (string): Contraseña del usuario

**Respuesta exitosa (200):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

**Respuesta de error (401):**
```json
{
    "detail": "Incorrect email or password"
}
```

### GET /api/v1/auth/me
Obtiene información del usuario autenticado actual.

**Headers requeridos:**
- `Authorization: Bearer <token>`

**Respuesta exitosa (200):**
```json
{
    "id": 1,
    "email": "admin@example.com",
    "username": "admin",
    "full_name": "Administrador",
    "is_active": true,
    "is_superuser": true
}
```

## 🛡️ Endpoints Protegidos

Los siguientes endpoints requieren autenticación JWT:

### Usuarios
- `GET /api/v1/users` - Listar usuarios
- `GET /api/v1/users/{user_id}` - Obtener usuario específico
- `PUT /api/v1/users/{user_id}` - Actualizar usuario
- `DELETE /api/v1/users/{user_id}` - Eliminar usuario

### Clientes
- `POST /api/v1/clients` - Crear cliente
- `GET /api/v1/clients` - Listar clientes
- `GET /api/v1/clients/search` - Buscar clientes
- `GET /api/v1/clients/{client_id}` - Obtener cliente específico
- `PUT /api/v1/clients/{client_id}` - Actualizar cliente
- `DELETE /api/v1/clients/{client_id}` - Eliminar cliente
- `POST /api/v1/clients/{client_id}/reactivate` - Reactivar cliente

### Productos
- `POST /api/v1/products` - Crear producto
- `GET /api/v1/products` - Listar productos
- `GET /api/v1/products/search` - Buscar productos
- `GET /api/v1/products/{product_id}` - Obtener producto específico
- `PUT /api/v1/products/{product_id}` - Actualizar producto
- `DELETE /api/v1/products/{product_id}` - Eliminar producto
- `POST /api/v1/products/{product_id}/reactivate` - Reactivar producto
- `PUT /api/v1/products/{product_id}/stock` - Actualizar stock

### Órdenes
- `POST /api/v1/orders` - Crear orden
- `GET /api/v1/orders` - Listar órdenes
- `GET /api/v1/orders/{order_id}` - Obtener orden específica
- `PUT /api/v1/orders/{order_id}` - Actualizar orden
- `DELETE /api/v1/orders/{order_id}` - Eliminar orden
- `POST /api/v1/orders/{order_id}/items` - Agregar item a orden
- `DELETE /api/v1/orders/{order_id}/items/{item_id}` - Remover item de orden
- `POST /api/v1/orders/{order_id}/status/{new_status}` - Actualizar estado de orden
- `GET /api/v1/orders/client/{client_id}` - Obtener órdenes por cliente

## 🔧 Configuración

### Variables de Entorno
El sistema utiliza las siguientes variables de entorno:

```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Configuración de Seguridad
- **Algoritmo:** HS256 (HMAC con SHA-256)
- **Expiración por defecto:** 30 minutos
- **Tipo de token:** Bearer

## 🧪 Pruebas

### Script de Prueba Local
```bash
pipenv run python scripts/test_auth.py
```

### Script de Prueba de API
```bash
pipenv run python scripts/test_api_auth.py
```

### Ejemplo con curl
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "password": "admin123"}'

# Usar token
curl -X GET "http://localhost:8000/api/v1/users" \
     -H "Authorization: Bearer <token>"
```

## 🚨 Manejo de Errores

### 401 Unauthorized
- Token faltante o inválido
- Token expirado
- Credenciales incorrectas

### 400 Bad Request
- Usuario inactivo
- Datos de entrada inválidos

## 🔒 Consideraciones de Seguridad

1. **Tokens JWT:** Los tokens contienen información del usuario pero no son almacenados en el servidor
2. **Expiración:** Los tokens expiran automáticamente después del tiempo configurado
3. **HTTPS:** En producción, siempre usar HTTPS para transmitir tokens
4. **Secret Key:** Mantener la SECRET_KEY segura y única por entorno
5. **Logout:** Los tokens JWT no pueden ser invalidados del lado del servidor, se recomienda implementar una lista negra de tokens si es necesario

## 📝 Notas de Implementación

- El sistema utiliza `python-jose` para la generación y validación de tokens JWT
- La autenticación se basa en email y contraseña hasheada con bcrypt
- Todos los endpoints protegidos verifican automáticamente el token JWT
- El middleware de autenticación se aplica a nivel de endpoint usando FastAPI Dependencies 