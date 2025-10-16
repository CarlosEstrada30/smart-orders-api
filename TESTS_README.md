# Tests con PostgreSQL - Configuración Simple

Esta es una configuración simple y limpia para ejecutar tests con PostgreSQL.

## 🎯 Características

- ✅ **Un solo conftest.py** - Configuración centralizada
- ✅ **PostgreSQL** - Conexión desde variable de entorno
- ✅ **JWT fijo** - No necesitas hacer login en cada test
- ✅ **JWT personalizable** - Crear JWTs con diferentes usuarios/permisos
- ✅ **Limpieza automática** - Se borra todo después de cada test
- ✅ **Configuración simple** - Mínima configuración necesaria

## 🚀 Configuración Rápida

### 1. Configurar PostgreSQL

```bash
# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER test_user WITH PASSWORD 'test_password';
ALTER USER test_user CREATEDB;
CREATE DATABASE test_db OWNER test_user;
GRANT ALL PRIVILEGES ON DATABASE test_db TO test_user;
EOF
```

### 2. Configurar variable de entorno

```bash
export DATABASE_URL="postgresql://test_user:test_password@localhost:5432/test_db"
```

### 3. Ejecutar tests

```bash
# Opción 1: Con script
python run_tests.py

# Opción 2: Con pytest directamente
python -m pytest tests/api/ -v

# Opción 3: Solo tests de clientes
python -m pytest tests/api/clients/ -v
```

## 📁 Archivos Creados

- `tests/conftest.py` - Configuración principal
- `tests/api/clients/test_client_endpoints.py` - Tests de clientes
- `pytest.ini` - Configuración de pytest
- `run_tests.py` - Script para ejecutar tests

## 🔧 Configuración Detallada

### conftest.py

```python
# Conexión desde variable de entorno
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://test_user:test_password@localhost:5432/test_db')

# Fixtures principales:
# - db_session: Sesión de PostgreSQL
# - client: Cliente FastAPI básico
# - authenticated_client: Cliente con JWT fijo
```

### Flujo de cada test:

1. ✅ **Crear tablas** (`Base.metadata.create_all()`)
2. ✅ **Ejecutar test** (operaciones en BD)
3. ✅ **Limpiar tablas** (`Base.metadata.drop_all()`)

## 🧪 Ejemplos de Uso

### Test con servicio (sin autenticación)
```python
def test_create_client_success(self, db_session, sample_client_data):
    client_service = ClientService()
    client_data = ClientCreate(**sample_client_data)
    result = client_service.create_client(db_session, client_data)
    assert result.name == sample_client_data["name"]
```

### Test con endpoint (con autenticación)
```python
def test_create_client_endpoint(self, authenticated_client, sample_client_data):
    response = authenticated_client.post("/api/v1/clients/", json=sample_client_data)
    assert response.status_code == 201
```

### Test sin autenticación
```python
def test_create_client_without_auth(self, client, sample_client_data):
    response = client.post("/api/v1/clients/", json=sample_client_data)
    assert response.status_code == 401
```


## 🔑 JWT Fijo

El JWT fijo está configurado en `authenticated_client` y contiene:

```json
{
  "sub": "admin@example.com",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "username": "admin",
    "full_name": "Administrador",
    "token": "b0d238cb-7f18-48c1-8c19-0908e7332df2",
    "role": "EMPLOYEE",
    "is_active": true,
    "is_superuser": true
  },
  "tenant": {
    "tenant_schema": "public"
  },
  "exp": 1759875106
}
```

## 🛠️ Fixtures Disponibles

### `db_session`
Sesión de PostgreSQL para tests. Se crean/eliminan tablas automáticamente.

### `client`
Cliente FastAPI básico (sin autenticación).

### `authenticated_client`
Cliente con JWT fijo preconfigurado para autenticación.

### `sample_client_data`
Datos de cliente de muestra para tests.

## 🚨 Troubleshooting

### Error de conexión
```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Verificar usuario
sudo -u postgres psql -c "\du"

# Verificar base de datos
sudo -u postgres psql -c "\l"
```

### Error de permisos
```bash
# Dar permisos
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE test_db TO test_user;"
```

### Error de variable de entorno
```bash
# Verificar variable
echo $DATABASE_URL

# Configurar si no existe
export DATABASE_URL="postgresql://test_user:test_password@localhost:5432/test_db"
```

## 📊 Ventajas de esta Configuración

- ✅ **Simple**: Solo un conftest.py
- ✅ **Rápido**: Configuración mínima
- ✅ **Limpio**: Se borra todo después de cada test
- ✅ **Realista**: Usa PostgreSQL real
- ✅ **Fácil**: JWT fijo, no necesitas login

## 🎯 Comandos Útiles

```bash
# Ejecutar todos los tests
python run_tests.py

# Ejecutar test específico
python -m pytest tests/test_client_simple.py::TestClientSimple::test_create_client_success -v

# Ejecutar con logs SQL
# (cambiar echo=True en conftest.py)

# Verificar conexión
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
print('✅ Conexión exitosa')
conn.close()
"
```

¿Necesitas ayuda con alguna configuración específica?
