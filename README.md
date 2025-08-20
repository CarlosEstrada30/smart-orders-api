# Smart Orders API

Una API REST completa para gestión de pedidos construida con FastAPI y arquitectura limpia.

## Características

- **Arquitectura Limpia**: Separación clara de responsabilidades con capas de servicios y repositorios
- **Autenticación JWT**: Sistema de autenticación seguro con tokens JWT
- **CRUD Completo**: Operaciones CRUD para Usuarios, Clientes, Productos y Pedidos
- **Validación de Datos**: Uso de Pydantic para validación y serialización
- **Base de Datos**: SQLAlchemy con PostgreSQL
- **Documentación Automática**: Swagger UI y ReDoc integrados
- **Gestión de Stock**: Control automático de inventario
- **Estados de Pedidos**: Flujo de trabajo configurable para pedidos
- **Endpoints Protegidos**: Todos los endpoints críticos requieren autenticación

## Módulos

### 1. Usuarios
- Registro y autenticación de usuarios
- Gestión de perfiles y permisos
- Encriptación de contraseñas con bcrypt
- Sistema de autenticación JWT

### 2. Clientes
- Gestión de información de clientes
- Búsqueda por nombre
- Soft delete (desactivación en lugar de eliminación)

### 3. Productos
- Catálogo de productos con SKU único
- Control de inventario
- Alertas de stock bajo
- Búsqueda por nombre

### 4. Pedidos
- Creación de pedidos con múltiples productos
- Estados de pedido: Pending, Confirmed, In Progress, Shipped, Delivered, Cancelled
- Validación automática de stock
- Números de pedido únicos
- Resúmenes detallados

## Autenticación

La API utiliza autenticación JWT (JSON Web Tokens) para proteger los endpoints. Para más detalles, consulta [AUTHENTICATION.md](AUTHENTICATION.md).

### Flujo Básico:
1. **Login**: `POST /api/v1/auth/login` con email y contraseña
2. **Obtener Token**: El sistema retorna un token JWT
3. **Usar Token**: Incluir el token en el header `Authorization: Bearer <token>`

### Credenciales de Prueba:
- **Admin**: admin@example.com / admin123
- **Usuario**: user1@example.com / user123

## Instalación

### Prerrequisitos

- Python 3.8+
- PostgreSQL
- pip o pipenv

### Opción 1: Usando Pipenv (Recomendado)

#### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd smart-orders-api
```

#### 2. Instalar Pipenv (si no lo tienes)

```bash
pip install pipenv
```

#### 3. Instalar dependencias

```bash
pipenv install
```

#### 4. Activar el entorno virtual

```bash
pipenv shell
```

#### 5. Configurar base de datos

1. Crear una base de datos PostgreSQL
2. Copiar `.env.example` a `.env`
3. Configurar las variables de entorno:

```env
DATABASE_URL=postgresql://user:password@localhost/smart_orders_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### 6. Ejecutar la aplicación

```bash
pipenv run uvicorn app.main:app --reload
```

### Opción 2: Usando pip tradicional

#### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd smart-orders-api
```

#### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

#### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

#### 4. Configurar base de datos

1. Crear una base de datos PostgreSQL
2. Copiar `.env.example` a `.env`
3. Configurar las variables de entorno:

```env
DATABASE_URL=postgresql://user:password@localhost/smart_orders_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### 5. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload
```

### Opción 3: Setup Automático

#### Setup Inteligente (Recomendado):

```bash
./scripts/quick_setup.sh
```

Este script detecta automáticamente si Pipenv está disponible y funciona correctamente, y usa pip como respaldo si hay problemas.

#### Usando Pipenv (si funciona correctamente):

```bash
./scripts/setup.sh
```

#### Usando pip (alternativa si Pipenv falla):

```bash
./scripts/setup_pip.sh
```

## Solución de Problemas

### Error con Pipenv

Si encuentras errores como `SyntaxError: invalid syntax` al usar Pipenv, es probable que tengas una versión antigua. Soluciones:

1. **Actualizar Pipenv:**
```bash
pip install --upgrade pipenv
```

2. **Usar pip en su lugar:**
```bash
./scripts/setup_pip.sh
```

3. **Instalación manual con pip:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Error de Base de Datos

Si tienes problemas con PostgreSQL:

1. **Verificar que PostgreSQL esté corriendo:**
```bash
sudo systemctl status postgresql
```

2. **Crear la base de datos:**
```bash
sudo -u postgres psql
CREATE DATABASE smart_orders_db;
CREATE USER myuser WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE smart_orders_db TO myuser;
\q
```

3. **Usar SQLite para desarrollo (temporal):**
Cambiar en `.env`:
```env
DATABASE_URL=sqlite:///./smart_orders.db
```

### Error de Dependencias

Si hay conflictos de dependencias:

1. **Limpiar entorno virtual:**
```bash
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Usar Docker:**
```bash
docker-compose up --build
```

## Uso

### Documentación

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints Principales

#### Usuarios
- `POST /api/v1/users/` - Crear usuario
- `GET /api/v1/users/` - Listar usuarios
- `GET /api/v1/users/{id}` - Obtener usuario
- `PUT /api/v1/users/{id}` - Actualizar usuario
- `DELETE /api/v1/users/{id}` - Eliminar usuario

#### Clientes
- `POST /api/v1/clients/` - Crear cliente
- `GET /api/v1/clients/` - Listar clientes
- `GET /api/v1/clients/search?name=...` - Buscar clientes
- `GET /api/v1/clients/{id}` - Obtener cliente
- `PUT /api/v1/clients/{id}` - Actualizar cliente
- `DELETE /api/v1/clients/{id}` - Desactivar cliente
- `POST /api/v1/clients/{id}/reactivate` - Reactivar cliente

#### Productos
- `POST /api/v1/products/` - Crear producto
- `GET /api/v1/products/` - Listar productos
- `GET /api/v1/products/search?name=...` - Buscar productos
- `GET /api/v1/products/low-stock` - Productos con stock bajo
- `GET /api/v1/products/{id}` - Obtener producto
- `GET /api/v1/products/sku/{sku}` - Obtener producto por SKU
- `PUT /api/v1/products/{id}` - Actualizar producto
- `DELETE /api/v1/products/{id}` - Desactivar producto
- `POST /api/v1/products/{id}/reactivate` - Reactivar producto
- `POST /api/v1/products/{id}/stock` - Actualizar stock

#### Pedidos
- `POST /api/v1/orders/` - Crear pedido
- `GET /api/v1/orders/` - Listar pedidos
- `GET /api/v1/orders/client/{client_id}` - Pedidos por cliente
- `GET /api/v1/orders/{id}` - Obtener pedido
- `GET /api/v1/orders/number/{order_number}` - Obtener pedido por número
- `PUT /api/v1/orders/{id}` - Actualizar pedido
- `POST /api/v1/orders/{id}/status` - Actualizar estado
- `POST /api/v1/orders/{id}/cancel` - Cancelar pedido
- `GET /api/v1/orders/{id}/summary` - Resumen del pedido

## Ejemplos de Uso

### Crear un Cliente

```bash
curl -X POST "http://localhost:8000/api/v1/clients/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "phone": "+1234567890",
    "address": "Calle Principal 123"
  }'
```

### Crear un Producto

```bash
curl -X POST "http://localhost:8000/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop Dell XPS 13",
    "description": "Laptop ultrabook de 13 pulgadas",
    "price": 1299.99,
    "stock": 10,
    "sku": "DELL-XPS13-001"
  }'
```

### Crear un Pedido

```bash
curl -X POST "http://localhost:8000/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "status": "pending",
    "notes": "Entrega urgente",
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "unit_price": 1299.99
      }
    ]
  }'
```

## Comandos Útiles con Pipenv

### Gestión de dependencias

```bash
# Instalar dependencias
pipenv install

# Instalar dependencia de desarrollo
pipenv install --dev pytest

# Instalar dependencia específica
pipenv install requests

# Desinstalar dependencia
pipenv uninstall requests

# Ver dependencias instaladas
pipenv graph

# Verificar seguridad
pipenv check
```

### Ejecución de comandos

```bash
# Activar entorno virtual
pipenv shell

# Ejecutar comando en el entorno virtual
pipenv run python script.py

# Ejecutar la aplicación
pipenv run uvicorn app.main:app --reload

# Ejecutar tests
pipenv run pytest

# Formatear código
pipenv run black .

# Verificar tipos
pipenv run mypy app/
```

## Arquitectura

```
app/
├── models/          # Modelos SQLAlchemy
├── schemas/         # Esquemas Pydantic
├── repositories/    # Capa de acceso a datos
├── services/        # Lógica de negocio
├── api/            # Endpoints REST
│   └── v1/         # Versión 1 de la API
└── database.py     # Configuración de BD
```

### Patrones Utilizados

- **Repository Pattern**: Abstracción del acceso a datos
- **Service Layer**: Lógica de negocio centralizada
- **Dependency Injection**: Inyección de dependencias con FastAPI
- **Data Transfer Objects**: Esquemas Pydantic para validación

## Desarrollo

### Estructura del Proyecto

```
smart-orders-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   └── api/
├── Pipfile
├── Pipfile.lock
├── requirements.txt
├── README.md
└── .env.example
```

### Agregar Nuevas Funcionalidades

1. **Modelo**: Crear en `app/models/`
2. **Esquema**: Crear en `app/schemas/`
3. **Repositorio**: Crear en `app/repositories/`
4. **Servicio**: Crear en `app/services/`
5. **API**: Crear en `app/api/v1/`

### Comandos de Desarrollo

```bash
# Inicializar base de datos con datos de ejemplo
pipenv run python scripts/init_db.py
# o
python scripts/init_db.py

# Ejecutar tests
pipenv run pytest
# o
pytest

# Formatear código
pipenv run black .
# o
black .

# Verificar tipos
pipenv run mypy app/
# o
mypy app/

# Verificar estilo de código
pipenv run flake8 app/
# o
flake8 app/
```

### Migraciones con Alembic

El proyecto usa Alembic para el control de versiones de la base de datos.

#### Comandos Básicos:

```bash
# Crear nueva migración (automática basada en cambios en modelos)
pipenv run alembic revision --autogenerate -m "Descripción de la migración"

# Aplicar todas las migraciones pendientes
pipenv run alembic upgrade head

# Aplicar hasta una migración específica
pipenv run alembic upgrade <revision_id>

# Revertir la última migración
pipenv run alembic downgrade -1

# Revertir a una migración específica
pipenv run alembic downgrade <revision_id>

# Ver migración actual
pipenv run alembic current

# Ver historial de migraciones
pipenv run alembic history

# Marcar migración como aplicada (sin ejecutarla)
pipenv run alembic stamp <revision_id>
```

#### Usando el Script de Migraciones:

```bash
# Crear nueva migración
python scripts/migrate.py create "Descripción de la migración"

# Aplicar migraciones
python scripts/migrate.py upgrade

# Revertir migración
python scripts/migrate.py downgrade

# Ver estado actual
python scripts/migrate.py current

# Ver historial
python scripts/migrate.py history
```

#### Flujo de Trabajo Típico:

1. **Hacer cambios en los modelos** (`app/models/`)
2. **Crear migración:**
   ```bash
   pipenv run alembic revision --autogenerate -m "Agregar campo nuevo"
   ```
3. **Revisar la migración generada** en `alembic/versions/`
4. **Aplicar la migración:**
   ```bash
   pipenv run alembic upgrade head
   ```

#### Migración Inicial:

Si es la primera vez que usas el proyecto:

```bash
# Crear migración inicial
pipenv run alembic revision --autogenerate -m "Initial migration"

# Aplicar migración inicial
pipenv run alembic upgrade head
```

## Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.